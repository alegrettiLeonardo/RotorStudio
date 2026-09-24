from __future__ import annotations

import copy
import threading
import traceback
from dataclasses import dataclass

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from drm_core import AnalysisService, AnalysisCancelled


@dataclass(frozen=True)
class AnalysisJobOutcome:
    execution: object
    model_snapshot: object
    cancellation_deferred: bool = False


@dataclass(frozen=True)
class AnalysisJobFailure:
    case: object
    status: str
    message: str
    exception_type: str
    guidance: str
    traceback: str


class _WorkerSignals(QObject):
    state = Signal(str)
    progress = Signal(int, int)
    completed = Signal(object)
    cancelled = Signal(str)
    failed = Signal(object)


class _AnalysisRunnable(QRunnable):
    SAFE_COOPERATIVE_KINDS = frozenset({"modal_sweep"})

    def __init__(self, service: AnalysisService, project, case):
        super().__init__()
        self.service = service
        self.project = copy.deepcopy(project)
        self.case = case
        self.signals = _WorkerSignals()
        self.cancel_event = threading.Event()
        self.state = "QUEUED"

    @property
    def cooperative(self) -> bool:
        return self.case.kind.strip().lower() in self.SAFE_COOPERATIVE_KINDS

    def request_cancel(self):
        self.cancel_event.set()

    def _guidance(self, exc):
        if isinstance(exc, (OSError, ImportError)):
            return "Verify the packaged Fortran solver library and its runtime dependencies."
        return "Inspect the Console traceback and solver status; correct the model/case if indicated and rerun."

    @Slot()
    def run(self):
        if self.cancel_event.is_set():
            self.state = "CANCELLED"
            self.signals.cancelled.emit("cancelled before solver execution")
            return
        self.state = "RUNNING"
        self.signals.state.emit("RUNNING")
        try:
            if self.cooperative:
                execution = self.service.execute(
                    self.project,
                    self.case,
                    progress_callback=lambda current,total:self.signals.progress.emit(current,total),
                    cancel_check=self.cancel_event.is_set,
                )
            else:
                execution = self.service.execute(self.project, self.case)
        except AnalysisCancelled as exc:
            self.state = "CANCELLED"
            self.signals.cancelled.emit(str(exc))
            return
        except Exception as exc:
            self.state = "FAILED"
            failure = AnalysisJobFailure(
                case=self.case,
                status="FAILED",
                message=str(exc),
                exception_type=type(exc).__name__,
                guidance=self._guidance(exc),
                traceback=traceback.format_exc(),
            )
            self.signals.failed.emit(failure)
            return
        self.state = "COMPLETED"
        self.signals.completed.emit(
            AnalysisJobOutcome(
                execution,
                self.project.model,
                cancellation_deferred=self.cancel_event.is_set() and not self.cooperative,
            )
        )


class SolverJobManager(QObject):
    jobStateChanged = Signal(str, object)
    progress = Signal(object, int, int)
    completed = Signal(object)
    cancelled = Signal(object, str)
    failed = Signal(object)

    def __init__(self, service: AnalysisService | None = None, parent=None):
        super().__init__(parent)
        self.service = service or AnalysisService()
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self._live = []
        self._running = None

    def submit(self, project, case):
        runnable = _AnalysisRunnable(self.service, project, case)
        self._live.append(runnable)
        self.jobStateChanged.emit("QUEUED", case)

        def state_changed(state, r=runnable, c=case):
            r.state = state
            if state == "RUNNING":
                self._running = r
            self.jobStateChanged.emit(state, c)

        runnable.signals.state.connect(state_changed)
        runnable.signals.progress.connect(lambda current,total,c=case:self.progress.emit(c,current,total))

        def completed(outcome, r=runnable, c=case):
            self._discard(r)
            self.jobStateChanged.emit("COMPLETED", c)
            self.completed.emit(outcome)

        def cancelled(reason, r=runnable, c=case):
            self._discard(r)
            self.jobStateChanged.emit("CANCELLED", c)
            self.cancelled.emit(c, reason)

        def failed(failure, r=runnable, c=case):
            self._discard(r)
            self.jobStateChanged.emit("FAILED", c)
            self.failed.emit(failure)

        runnable.signals.completed.connect(completed)
        runnable.signals.cancelled.connect(cancelled)
        runnable.signals.failed.connect(failed)
        self.pool.start(runnable)
        return runnable

    def _discard(self, runnable):
        if runnable in self._live:
            self._live.remove(runnable)
        if self._running is runnable:
            self._running = None

    def cancel(self, runnable=None) -> bool:
        target = runnable or self._running or (self._live[0] if self._live else None)
        if target is None or target.state in {"COMPLETED", "FAILED", "CANCELLED"}:
            return False
        case = target.case
        if target.state == "QUEUED" and self.pool.tryTake(target):
            target.request_cancel()
            target.state = "CANCELLED"
            self._discard(target)
            self.jobStateChanged.emit("CANCELLED", case)
            self.cancelled.emit(case, "cancelled while queued; solver was not started")
            return True

        target.request_cancel()
        if target.state in {"QUEUED", "RUNNING"}:
            target.state = "CANCELLING"
            self.jobStateChanged.emit("CANCELLING", case)
        return True

    def cancel_current(self) -> bool:
        return self.cancel()

    def wait_for_done(self, msecs: int = -1) -> bool:
        return self.pool.waitForDone(msecs)
