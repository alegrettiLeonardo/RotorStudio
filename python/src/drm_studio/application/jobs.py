from __future__ import annotations

import copy
import traceback
from dataclasses import dataclass

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from drm_core import AnalysisService


@dataclass(frozen=True)
class AnalysisJobOutcome:
    execution: object
    model_snapshot: object


class _WorkerSignals(QObject):
    state = Signal(str)
    completed = Signal(object)
    failed = Signal(str, str)


class _AnalysisRunnable(QRunnable):
    def __init__(self, service: AnalysisService, project, case):
        super().__init__()
        self.service = service
        self.project = copy.deepcopy(project)
        self.case = case
        self.signals = _WorkerSignals()

    @Slot()
    def run(self):
        self.signals.state.emit("RUNNING")
        try:
            execution = self.service.execute(self.project, self.case)
        except Exception as exc:
            self.signals.failed.emit(str(exc), traceback.format_exc())
            return
        self.signals.completed.emit(AnalysisJobOutcome(execution, self.project.model))


class SolverJobManager(QObject):
    jobStateChanged = Signal(str, object)
    completed = Signal(object)
    failed = Signal(str, str, object)

    def __init__(self, service: AnalysisService | None = None, parent=None):
        super().__init__(parent)
        self.service = service or AnalysisService()
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self._live = set()

    def submit(self, project, case):
        runnable = _AnalysisRunnable(self.service, project, case)
        self._live.add(runnable)
        self.jobStateChanged.emit("QUEUED", case)

        runnable.signals.state.connect(lambda state, c=case: self.jobStateChanged.emit(state, c))

        def completed(outcome, r=runnable, c=case):
            self._live.discard(r)
            self.jobStateChanged.emit("COMPLETED", c)
            self.completed.emit(outcome)

        def failed(message, trace, r=runnable, c=case):
            self._live.discard(r)
            self.jobStateChanged.emit("FAILED", c)
            self.failed.emit(message, trace, c)

        runnable.signals.completed.connect(completed)
        runnable.signals.failed.connect(failed)
        self.pool.start(runnable)
        return runnable

    def wait_for_done(self, msecs: int = -1) -> bool:
        return self.pool.waitForDone(msecs)
