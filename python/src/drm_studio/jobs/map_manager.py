from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import threading
import traceback as traceback_module

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from drm_core.solver.bearing_maps import (
    BearingMapCache,
    BearingMapCancelled,
)
from drm_core.solver.bearings_backend import AdvancedBearingBackend

from .states import JobState


@dataclass(frozen=True)
class OperatingMapRequest:
    request_id: int
    bearing: object
    speed_rad_s: tuple[float, ...]
    frequency_rad_s: tuple[float, ...]
    interpolation: str
    cache_root: str
    selection_key: str


@dataclass(frozen=True)
class OperatingMapProgress:
    completed_points: int
    total_points: int
    stage: str
    speed_rad_s: float | None = None
    frequency_rad_s: float | None = None

    @property
    def percent(self) -> float:
        return 100.0 * self.completed_points / max(1, self.total_points)


@dataclass(frozen=True)
class OperatingMapOutcome:
    request: OperatingMapRequest
    result: object


@dataclass(frozen=True)
class OperatingMapFailure:
    request: OperatingMapRequest
    exception_type: str
    message: str
    traceback: str


class _Signals(QObject):
    stateChanged = Signal(str, object)
    progress = Signal(object, object)
    completed = Signal(object)
    cancelled = Signal(object, str)
    failed = Signal(object)


class OperatingMapRunnable(QRunnable):
    def __init__(self, request: OperatingMapRequest):
        super().__init__()
        self.setAutoDelete(False)
        self.request = OperatingMapRequest(
            request.request_id,
            deepcopy(request.bearing),
            tuple(request.speed_rad_s),
            tuple(request.frequency_rad_s),
            request.interpolation,
            request.cache_root,
            request.selection_key,
        )
        self.signals = _Signals()
        self.state = JobState.QUEUED.value
        self._cancel = threading.Event()
        self._backend = None

    def _set_state(self, state: JobState):
        self.state = state.value
        self.signals.stateChanged.emit(self.state, self.request)

    def request_cancel(self):
        self._cancel.set()
        if self.state in (JobState.QUEUED.value, JobState.RUNNING.value):
            self._set_state(JobState.CANCEL_REQUESTED)
        if self._backend is not None:
            try:
                self._backend.request_cancel()
            except Exception:
                pass

    @Slot()
    def run(self):
        if self._cancel.is_set():
            self._set_state(JobState.CANCELLED)
            self.signals.cancelled.emit(self.request, "cancelled before map generation")
            return
        try:
            self._backend = AdvancedBearingBackend()
            cache = BearingMapCache(self.request.cache_root)

            def progress(completed, total, point):
                self.signals.progress.emit(
                    self.request,
                    OperatingMapProgress(
                        int(completed),
                        int(total),
                        str(point.get("stage", "physical_evaluation")),
                        point.get("speed_rad_s"),
                        point.get("frequency_rad_s"),
                    ),
                )

            self._set_state(JobState.RUNNING)
            result = cache.get_or_generate(
                self.request.bearing,
                self.request.speed_rad_s,
                self.request.frequency_rad_s or None,
                interpolation=self.request.interpolation,
                backend=self._backend,
                progress_callback=progress,
                cancel_check=self._cancel.is_set,
            )
            if self._cancel.is_set():
                raise BearingMapCancelled(
                    "cancel requested; complete map was intentionally not published"
                )
            if result.source in {"L1", "L2"}:
                total = len(self.request.speed_rad_s) * max(1, len(self.request.frequency_rad_s))
                self.signals.progress.emit(
                    self.request,
                    OperatingMapProgress(total, total, f"cache_{result.source.lower()}"),
                )
            self._set_state(JobState.COMPLETED)
            self.signals.completed.emit(OperatingMapOutcome(self.request, result))
        except BearingMapCancelled as exc:
            self._set_state(JobState.CANCELLED)
            self.signals.cancelled.emit(self.request, str(exc))
        except Exception as exc:
            self._set_state(JobState.FAILED)
            self.signals.failed.emit(
                OperatingMapFailure(
                    self.request,
                    type(exc).__name__,
                    str(exc),
                    traceback_module.format_exc(),
                )
            )


class OperatingMapJobManager(QObject):
    """B16 map generation on the serialized B14 job/cancellation contract."""

    stateChanged = Signal(str, object)
    progress = Signal(object, object)
    completed = Signal(object)
    cancelled = Signal(object, str)
    failed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self._counter = 0
        self._jobs = []

    def submit(
        self,
        bearing,
        speed_rad_s,
        frequency_rad_s=None,
        *,
        interpolation="pchip",
        cache_root,
        selection_key="",
    ):
        self._counter += 1
        request = OperatingMapRequest(
            self._counter,
            bearing,
            tuple(float(x) for x in speed_rad_s),
            tuple(float(x) for x in (frequency_rad_s or ())),
            str(interpolation),
            str(cache_root),
            str(selection_key),
        )
        job = OperatingMapRunnable(request)
        job.signals.stateChanged.connect(self.stateChanged)
        job.signals.progress.connect(self.progress)
        job.signals.completed.connect(self._completed)
        job.signals.cancelled.connect(self._cancelled)
        job.signals.failed.connect(self._failed)
        self._jobs.append(job)
        self.stateChanged.emit(JobState.QUEUED.value, request)
        self.pool.start(job)
        return job

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

    def _forget(self, request_id):
        self._jobs[:] = [
            job for job in self._jobs if job.request.request_id != request_id
        ]

    def _completed(self, outcome):
        self._forget(outcome.request.request_id)
        self.completed.emit(outcome)

    def _cancelled(self, request, reason):
        self._forget(request.request_id)
        self.cancelled.emit(request, reason)

    def _failed(self, failure):
        self._forget(failure.request.request_id)
        self.failed.emit(failure)

    def cancel(self, job=None):
        target = job or self.active
        if target is None:
            return False
        if target.state == JobState.QUEUED.value and self.pool.tryTake(target):
            target.request_cancel()
            target.state = JobState.CANCELLED.value
            self._forget(target.request.request_id)
            self.stateChanged.emit(JobState.CANCELLED.value, target.request)
            self.cancelled.emit(target.request, "cancelled while queued")
            return True
        target.request_cancel()
        return True

    def wait_for_done(self, timeout_ms=-1):
        return self.pool.waitForDone(int(timeout_ms))

    def shutdown(self, timeout_ms=5000):
        for job in tuple(self._jobs):
            self.cancel(job)
        return self.wait_for_done(timeout_ms)


__all__ = [
    "OperatingMapRequest",
    "OperatingMapProgress",
    "OperatingMapOutcome",
    "OperatingMapFailure",
    "OperatingMapRunnable",
    "OperatingMapJobManager",
]
