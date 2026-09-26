from __future__ import annotations

from PySide6.QtCore import QObject, QThreadPool, QTimer, Signal

from drm_core.solver.facade import SolverFacade

from .states import JobState
from .worker import BearingSolveRequest, BearingSolveRunnable


class BearingJobManager(QObject):
    """Serialized B14 native bearing job manager.

    One native fluid-film solve is allowed at a time until re-entrancy is
    independently qualified.  Progress is polled from the additive native ABI
    by QTimer; no arbitrary Python callback enters Fortran.
    """

    stateChanged = Signal(str, object)
    progress = Signal(object, object)
    completed = Signal(object)
    cancelled = Signal(object, str)
    failed = Signal(object)

    def __init__(self, parent=None, *, solver_factory=SolverFacade, poll_ms=100):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self._solver_factory = solver_factory
        self._counter = 0
        self._jobs = []
        self._timer = QTimer(self)
        self._timer.setInterval(max(25, int(poll_ms)))
        self._timer.timeout.connect(self._poll)

    def submit(self, bearing, speed_rad_s: float, frequency_rad_s: float, selection_key: str):
        self._counter += 1
        request = BearingSolveRequest(
            self._counter, bearing, float(speed_rad_s), float(frequency_rad_s), selection_key
        )
        runnable = BearingSolveRunnable(request, self._solver_factory)
        runnable.signals.stateChanged.connect(self.stateChanged)
        runnable.signals.completed.connect(self._completed)
        runnable.signals.cancelled.connect(self._cancelled)
        runnable.signals.failed.connect(self._failed)
        self._jobs.append(runnable)
        self.stateChanged.emit(JobState.QUEUED.value, request)
        self.pool.start(runnable)
        if not self._timer.isActive():
            self._timer.start()
        return runnable

    @property
    def active(self):
        return next(
            (
                job for job in self._jobs
                if job.state in (
                    JobState.QUEUED.value,
                    JobState.RUNNING.value,
                    JobState.CANCEL_REQUESTED.value,
                )
            ),
            None,
        )

    def cancel(self, runnable=None):
        job = runnable or self.active
        if job is None:
            return False
        if job.state == JobState.QUEUED.value and self.pool.tryTake(job):
            job.request_cancel()
            job.state = JobState.CANCELLED.value
            self.stateChanged.emit(JobState.CANCELLED.value, job.request)
            self.cancelled.emit(job.request, "cancelled while queued")
            self._forget(job)
            return True
        job.request_cancel()
        return True

    def _poll(self):
        live = False
        for job in tuple(self._jobs):
            if job.state in (JobState.RUNNING.value, JobState.CANCEL_REQUESTED.value):
                live = True
                progress = job.progress_snapshot()
                if progress is not None:
                    self.progress.emit(job.request, progress)
            elif job.state == JobState.QUEUED.value:
                live = True
        if not live:
            self._timer.stop()

    def _forget(self, job):
        try:
            self._jobs.remove(job)
        except ValueError:
            pass
        if not self._jobs:
            self._timer.stop()

    def _completed(self, outcome):
        job = next((j for j in self._jobs if j.request.request_id == outcome.request.request_id), None)
        if job is not None:
            self._forget(job)
        self.completed.emit(outcome)

    def _cancelled(self, request, reason):
        job = next((j for j in self._jobs if j.request.request_id == request.request_id), None)
        if job is not None:
            self._forget(job)
        self.cancelled.emit(request, reason)

    def _failed(self, failure):
        job = next((j for j in self._jobs if j.request.request_id == failure.request.request_id), None)
        if job is not None:
            self._forget(job)
        self.failed.emit(failure)

    def wait_for_done(self, timeout_ms=-1):
        return self.pool.waitForDone(int(timeout_ms))

    def shutdown(self, timeout_ms=5000):
        for job in tuple(self._jobs):
            self.cancel(job)
        return self.wait_for_done(timeout_ms)


__all__ = ["BearingJobManager"]
