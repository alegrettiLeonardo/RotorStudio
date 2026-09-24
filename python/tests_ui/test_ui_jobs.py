from __future__ import annotations

import threading
import time

from drm_core import AnalysisCase, AnalysisCancelled, RotorModel, RotorProject
from drm_studio.application.jobs import SolverJobManager


class _BlockingService:
    def __init__(self):
        self.calls=[]
        self.entered=threading.Event()
        self.release=threading.Event()

    def execute(self, project, case, **kwargs):
        self.calls.append(case.name)
        self.entered.set()
        self.release.wait(5)
        return object()


class _SweepService:
    def __init__(self):
        self.points=0

    def execute(self, project, case, *, progress_callback=None, cancel_check=None):
        for i in range(1,50):
            if cancel_check and cancel_check():
                raise AnalysisCancelled("cancelled at safe sweep boundary")
            self.points+=1
            if progress_callback:progress_callback(i,49)
            time.sleep(0.01)
        return object()


def test_queued_cancel_never_calls_solver(qtbot):
    service=_BlockingService();manager=SolverJobManager(service)
    p=RotorProject("jobs",RotorModel())
    first=manager.submit(p,AnalysisCase("modal",{},"first"))
    assert service.entered.wait(2)
    second=manager.submit(p,AnalysisCase("modal",{},"second"))
    with qtbot.waitSignal(manager.cancelled,timeout=2000) as sig:
        assert manager.cancel(second)
    assert sig.args[0].name=="second"
    service.release.set();manager.wait_for_done(5000)
    assert service.calls==["first"]


def test_safe_sweep_cancel_stops_at_boundary(qtbot):
    service=_SweepService();manager=SolverJobManager(service)
    p=RotorProject("jobs",RotorModel())
    case=AnalysisCase("modal_sweep",{"speeds_rad_s":[1,2,3]},"sweep")
    runnable=manager.submit(p,case)
    with qtbot.waitSignal(manager.progress,timeout=2000):
        pass
    with qtbot.waitSignal(manager.cancelled,timeout=3000):
        assert manager.cancel(runnable)
    manager.wait_for_done(5000)
    assert 1 <= service.points < 49


def test_monolithic_cancel_is_deferred_until_real_return(qtbot):
    service=_BlockingService();manager=SolverJobManager(service)
    p=RotorProject("jobs",RotorModel())
    case=AnalysisCase("modal",{},"monolithic")
    runnable=manager.submit(p,case)
    assert service.entered.wait(2)
    states=[]
    manager.jobStateChanged.connect(lambda state,_case:states.append(state))
    assert manager.cancel(runnable)
    assert "CANCELLING" in states
    assert runnable.state=="CANCELLING"
    service.release.set()
    with qtbot.waitSignal(manager.completed,timeout=3000) as sig:
        pass
    outcome=sig.args[0]
    assert outcome.cancellation_deferred is True
    assert "CANCELLED" not in states
