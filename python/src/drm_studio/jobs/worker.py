from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import threading
import traceback as traceback_module

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from drm_core.solver.bearings_backend import BearingCancelledError
from drm_core.solver.facade import SolverFacade

from .states import JobState


@dataclass(frozen=True)
class BearingSolveRequest:
    request_id: int
    bearing: object
    speed_rad_s: float
    frequency_rad_s: float
    selection_key: str


@dataclass(frozen=True)
class BearingSolveOutcome:
    request: BearingSolveRequest
    payload: dict


@dataclass(frozen=True)
class BearingSolveFailure:
    request: BearingSolveRequest
    exception_type: str
    message: str
    traceback: str


class BearingWorkerSignals(QObject):
    stateChanged = Signal(str, object)
    completed = Signal(object)
    cancelled = Signal(object, str)
    failed = Signal(object)


class BearingSolveRunnable(QRunnable):
    """One explicit Bearing Performance solve.

    The bearing input is deep-copied at submission.  The runnable never reaches
    back into the live GUI/model while native Reynolds/THD/TEHD is executing.
    """

    def __init__(self, request: BearingSolveRequest, solver_factory=SolverFacade):
        super().__init__()
        self.setAutoDelete(False)
        self.request = BearingSolveRequest(
            request.request_id,
            deepcopy(request.bearing),
            float(request.speed_rad_s),
            float(request.frequency_rad_s),
            str(request.selection_key),
        )
        self.signals = BearingWorkerSignals()
        self.state = JobState.QUEUED.value
        self._cancel = threading.Event()
        self._solver_factory = solver_factory
        self._solver = None

    def _set_state(self, state: JobState):
        self.state = state.value
        self.signals.stateChanged.emit(self.state, self.request)

    def request_cancel(self):
        self._cancel.set()
        if self.state in (JobState.QUEUED.value, JobState.RUNNING.value):
            self._set_state(JobState.CANCEL_REQUESTED)
        solver = self._solver
        if solver is not None:
            try:
                solver.advanced_bearing_cancel()
            except Exception:
                # The worker reports the real solver error/cancellation outcome.
                pass

    def progress_snapshot(self):
        solver = self._solver
        if solver is None:
            return None
        try:
            return solver.advanced_bearing_job_progress()
        except Exception:
            return None

    @Slot()
    def run(self):
        if self._cancel.is_set():
            self._set_state(JobState.CANCELLED)
            self.signals.cancelled.emit(self.request, "cancelled before native solve")
            return
        try:
            solver = self._solver_factory()
            self._solver = solver
            solver.advanced_bearing_job_reset()
            if self._cancel.is_set():
                solver.advanced_bearing_cancel()
            self._set_state(JobState.RUNNING)
            payload = solver.advanced_bearing_fields(
                self.request.bearing,
                self.request.speed_rad_s,
                self.request.frequency_rad_s,
                reset_job_control=False,
            )
            if self._cancel.is_set():
                self._set_state(JobState.CANCELLED)
                self.signals.cancelled.emit(
                    self.request,
                    "cancel requested; completed native data were intentionally not published",
                )
                return
            self._set_state(JobState.COMPLETED)
            self.signals.completed.emit(BearingSolveOutcome(self.request, payload))
        except BearingCancelledError as exc:
            self._set_state(JobState.CANCELLED)
            self.signals.cancelled.emit(self.request, str(exc))
        except Exception as exc:
            self._set_state(JobState.FAILED)
            self.signals.failed.emit(
                BearingSolveFailure(
                    self.request,
                    type(exc).__name__,
                    str(exc),
                    traceback_module.format_exc(),
                )
            )


__all__ = [
    "BearingSolveRequest", "BearingSolveOutcome", "BearingSolveFailure",
    "BearingSolveRunnable",
]
