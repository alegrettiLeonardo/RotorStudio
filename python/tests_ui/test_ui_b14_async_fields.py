from __future__ import annotations

import threading
import time

import numpy as np
from PySide6.QtCore import QTimer

from drm_core import CoefficientBearing
from drm_core.solver.bearings_backend import (
    BearingCancelledError,
    BearingEvaluation,
    BearingJobProgress,
)
from drm_studio.jobs import BearingJobManager, JobState


class _ControlledFacade:
    instances = []

    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.cancelled = threading.Event()
        self.__class__.instances.append(self)

    def advanced_bearing_job_reset(self):
        pass

    def advanced_bearing_cancel(self):
        self.cancelled.set()
        self.release.set()

    def advanced_bearing_job_progress(self):
        return BearingJobProgress(2, "thermal", 3, 10, 1, 4, self.cancelled.is_set())

    def advanced_bearing_fields(self, bearing, speed, frequency, **kwargs):
        self.entered.set()
        self.release.wait(5.0)
        if self.cancelled.is_set():
            raise BearingCancelledError("controlled cooperative cancellation")
        evaluation = BearingEvaluation(
            np.eye(2), np.eye(2), np.zeros((2, 2)), bearing.model_family, {}
        )
        return {
            "evaluation": evaluation,
            "pressure_field_pa": None,
            "temperature_field_k": None,
            "film_thickness_field_m": None,
            "deformation_field_m": None,
            "theta_rad": None,
            "axial_position_m": None,
            "pad_index": None,
            "pad_load_n": None,
            "convergence": None,
        }


class _FailingFacade(_ControlledFacade):
    def advanced_bearing_fields(self, bearing, speed, frequency, **kwargs):
        raise RuntimeError("solver sentinel failure")


def _bearing():
    return CoefficientBearing(node=1, kxx=1.1e6, kyy=1.2e6, cxx=101.0, cyy=102.0)


def test_b14_worker_does_not_block_qt_event_loop(qtbot):
    _ControlledFacade.instances.clear()
    manager = BearingJobManager(solver_factory=_ControlledFacade, poll_ms=25)
    ticks = []
    QTimer.singleShot(25, lambda: ticks.append("alive"))
    job = manager.submit(_bearing(), 100.0, 100.0, "A")
    qtbot.waitUntil(
        lambda: _ControlledFacade.instances and _ControlledFacade.instances[0].entered.is_set(),
        timeout=2000,
    )
    qtbot.waitUntil(lambda: bool(ticks), timeout=1000)
    _ControlledFacade.instances[0].release.set()
    with qtbot.waitSignal(manager.completed, timeout=3000):
        pass
    assert job.state == JobState.COMPLETED.value
    assert ticks == ["alive"]


def test_b14_progress_polling_changes_and_cancel_never_publishes(qtbot):
    _ControlledFacade.instances.clear()
    manager = BearingJobManager(solver_factory=_ControlledFacade, poll_ms=25)
    completed = []
    manager.completed.connect(completed.append)
    job = manager.submit(_bearing(), 100.0, 80.0, "A")
    qtbot.waitUntil(
        lambda: _ControlledFacade.instances and _ControlledFacade.instances[0].entered.is_set(),
        timeout=2000,
    )
    with qtbot.waitSignal(manager.progress, timeout=2000) as sig:
        pass
    progress = sig.args[1]
    assert progress.stage == "thermal"
    assert progress.percent > 0.0
    with qtbot.waitSignal(manager.cancelled, timeout=3000) as cancelled:
        assert manager.cancel(job)
    assert cancelled.args[0].selection_key == "A"
    assert job.state == JobState.CANCELLED.value
    assert completed == []


def test_b14_solver_error_reaches_gui_manager(qtbot):
    manager = BearingJobManager(solver_factory=_FailingFacade, poll_ms=25)
    with qtbot.waitSignal(manager.failed, timeout=3000) as signal:
        manager.submit(_bearing(), 100.0, 100.0, "A")
    failure = signal.args[0]
    assert failure.exception_type == "RuntimeError"
    assert failure.message == "solver sentinel failure"
    assert "solver sentinel failure" in failure.traceback


def test_b14_selection_key_is_immutable_request_identity(qtbot):
    _ControlledFacade.instances.clear()
    manager = BearingJobManager(solver_factory=_ControlledFacade, poll_ms=25)
    job = manager.submit(_bearing(), 100.0, 90.0, "selection-A")
    qtbot.waitUntil(
        lambda: _ControlledFacade.instances and _ControlledFacade.instances[0].entered.is_set(),
        timeout=2000,
    )
    assert job.request.selection_key == "selection-A"
    # A later GUI selection has a distinct identity; the page uses this key to
    # reject A's result rather than painting it onto B.
    assert job.request.selection_key != "selection-B"
    _ControlledFacade.instances[0].release.set()
    with qtbot.waitSignal(manager.completed, timeout=3000) as signal:
        pass
    assert signal.args[0].request.selection_key == "selection-A"


def test_b14_shutdown_with_active_job_is_cooperative(qtbot):
    _ControlledFacade.instances.clear()
    manager = BearingJobManager(solver_factory=_ControlledFacade, poll_ms=25)
    manager.submit(_bearing(), 100.0, 100.0, "A")
    qtbot.waitUntil(
        lambda: _ControlledFacade.instances and _ControlledFacade.instances[0].entered.is_set(),
        timeout=2000,
    )
    assert manager.shutdown(3000)
    assert _ControlledFacade.instances[0].cancelled.is_set()
