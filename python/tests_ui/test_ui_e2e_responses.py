from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from drm_core import AnalysisCase, RotorProject, Force
from drm_core.analysis.frequency_response import FrequencyResponseResult
from drm_core.analysis.transient import TransientResult
from drm_core.units import rpm_to_rad_s
from drm_studio.application.session import ProjectSession
from drm_studio.main_window import MainWindow
from drm_studio.result_views import FrequencyResponseResultView, TransientResultView

ROOT = Path(__file__).resolve().parents[2]


def _base_model():
    path = ROOT / "examples" / "chapter05" / "example_05_08_01.py"
    spec = importlib.util.spec_from_file_location("stage2_response_example", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build(6)


def _run(qtbot, model, case, result_type, view_type):
    window = MainWindow(session=ProjectSession(RotorProject(case.name, model, [case])))
    qtbot.addWidget(window)
    window.show()
    with qtbot.waitSignal(window.session.resultAdded, timeout=60000) as signal:
        assert window.run_analysis(case) is True
    record = signal.args[0]
    assert isinstance(record.execution.result, result_type)
    assert record.execution.build_metadata["backend"] == "Fortran2018/ctypes"
    assert any(isinstance(window.workspace.widget(i), view_type) for i in range(window.workspace.count()))
    return record


pytestmark = pytest.mark.skipif(
    not os.environ.get("DRMROTOR_LIB"), reason="real Fortran library required"
)


def test_synchronous_response_e2e(qtbot):
    model = _base_model()
    model.forces = [Force(1, (3, 2.321e-4, 0.217))]
    case = AnalysisCase(
        "frequency_response",
        {"speeds_rad_s": [float(rpm_to_rad_s(v)) for v in (100.0, 1500.0, 3000.0)]},
        "Synchronous E2E",
        {"outnodes": [3.1]},
    )
    record = _run(qtbot, model, case, FrequencyResponseResult, FrequencyResponseResultView)
    assert np.isfinite(record.execution.result.response).all()


def test_auxiliary_frequency_response_e2e(qtbot):
    model = _base_model()
    model.forces = [Force(7, (3, 12.321, -4.567))]
    case = AnalysisCase(
        "auxiliary_frequency_response",
        {
            "rotor_speed_rad_s": float(rpm_to_rad_s(2500.0)),
            "omega_rad_s": (2.0 * np.pi * np.asarray([5.0, 30.0, 90.0])).tolist(),
            "direction": 1.0,
        },
        "Auxiliary FRF E2E",
        {"outnodes": [3.1]},
    )
    record = _run(qtbot, model, case, FrequencyResponseResult, FrequencyResponseResultView)
    assert record.execution.result.response.shape[1] == 3


def test_foundation_frequency_and_time_response_e2e(qtbot):
    model_frf = _base_model()
    model_frf.forces = [Force(4, (0.0, 1.123e-5, 0.0, 2.234e-5))]
    frf_case = AnalysisCase(
        "foundation_frequency_response",
        {
            "rotor_speed_rad_s": float(rpm_to_rad_s(3000.0)),
            "omega_rad_s": (2.0 * np.pi * np.asarray([1.0, 10.0, 35.0])).tolist(),
        },
        "Foundation FRF E2E",
        {"outnodes": [3.1]},
    )
    frf = _run(qtbot, model_frf, frf_case, FrequencyResponseResult, FrequencyResponseResultView)
    assert np.isfinite(frf.execution.result.response).all()

    model_time = _base_model()
    model_time.forces = [Force(5, (0.0, 1.0e-3, 0.0, 1.0e-3, 0.025))]
    time_case = AnalysisCase(
        "foundation_time_response",
        {
            "rotor_speed_rad_s": float(rpm_to_rad_s(3000.0)),
            "dt": 5.0e-4,
            "npts": 81,
            "nr": 4,
            "rtol": 1.0e-5,
            "atol": 1.0e-8,
        },
        "Foundation Time E2E",
        {"outnode": 3.1},
    )
    transient = _run(qtbot, model_time, time_case, TransientResult, TransientResultView)
    assert transient.execution.result.time_s.size == 81


def test_runup_e2e(qtbot):
    model = _base_model()
    model.forces = [Force(1, (3, 1.234e-4, 0.0))]
    case = AnalysisCase(
        "runup",
        {
            "alpha": [0.20 * 2.0 * np.pi, 8.0 * np.pi, 0.0],
            "tspan": [0.0, 0.25],
            "nr": 4,
            "rtol": 1.0e-5,
            "atol": 1.0e-8,
            "max_points": 20000,
        },
        "Run-up E2E",
        {"outnode": 3.1},
    )
    record = _run(qtbot, model, case, TransientResult, TransientResultView)
    assert record.execution.result.speed_rad_s is not None
    assert np.all(np.diff(record.execution.result.time_s) > 0.0)
