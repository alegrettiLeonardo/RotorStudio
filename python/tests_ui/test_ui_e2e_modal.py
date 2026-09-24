from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from drm_core import AnalysisCase, ModalResult, RotorProject, save_project
from drm_core.analysis.critical_speed import CriticalSpeedResult
from drm_core.units import rpm_to_rad_s
from drm_studio.application.session import ProjectSession
from drm_studio.main_window import MainWindow
from drm_studio.result_views.modal_view import ModalResultView
from drm_studio.result_views.campbell_view import CampbellResultView
from drm_studio.result_views.critical_speed_view import CriticalSpeedResultView


def _load_example_05_08_01():
    root = Path(__file__).resolve().parents[2]
    path = root / "examples" / "chapter05" / "example_05_08_01.py"
    spec = importlib.util.spec_from_file_location("example_05_08_01_stage2", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(
    not os.environ.get("DRMROTOR_LIB"),
    reason="real Fortran library is required for Stage 2 M1 qualification",
)
def test_example_05_08_01_modal_vertical_slice_real_fortran(qtbot, tmp_path):
    example = _load_example_05_08_01()
    model = example.build(6)
    case = AnalysisCase(
        "modal",
        {
            "speed_rad_s": rpm_to_rad_s(5000.0),
            "with_eigenvectors": True,
            "with_kappa": True,
        },
        "Example_05_08_01 — Modal",
    )
    project = RotorProject("Example_05_08_01", model, [case])
    path = tmp_path / "Example_05_08_01.rds"
    save_project(project, path)

    window = MainWindow()
    qtbot.addWidget(window)
    window.open_project(path)
    window.show()

    with qtbot.waitSignal(window.session.resultAdded, timeout=60000) as first_signal:
        assert window.run_analysis(case) is True

    first_record = first_signal.args[0]
    first_result = first_record.execution.result
    assert isinstance(first_result, ModalResult)
    assert first_result.eigenvectors is not None
    assert first_result.eigenvalues.size > 0
    assert np.all(np.isfinite(first_result.natural_frequency_hz))
    assert first_record.execution.build_metadata["backend"] == "Fortran2018/ctypes"

    result_widgets = [
        window.workspace.widget(i) for i in range(window.workspace.count())
        if isinstance(window.workspace.widget(i), ModalResultView)
    ]
    assert len(result_widgets) == 1
    assert result_widgets[0].table.rowCount() > 0

    before_hash = window.session.current_model_hash
    window.save_project(path)
    window.close()

    reopened = MainWindow()
    qtbot.addWidget(reopened)
    reopened.open_project(path)
    reopened.show()
    assert reopened.session.current_model_hash == before_hash
    assert any(c.name == case.name and c.kind == "modal" for c in reopened.session.project.analyses)

    with qtbot.waitSignal(reopened.session.resultAdded, timeout=60000) as second_signal:
        assert reopened.run_analysis(case) is True

    second_result = second_signal.args[0].execution.result
    assert isinstance(second_result, ModalResult)
    assert np.allclose(
        second_result.natural_frequency_hz,
        first_result.natural_frequency_hz,
        rtol=1e-10,
        atol=1e-12,
    )


@pytest.mark.skipif(
    not os.environ.get("DRMROTOR_LIB"),
    reason="real Fortran library is required for Stage 2 Campbell qualification",
)
def test_campbell_workspace_uses_real_modal_sweep(qtbot):
    example = _load_example_05_08_01()
    model = example.build(6)
    speeds = [float(rpm_to_rad_s(v)) for v in (0.0, 2500.0, 5000.0)]
    case = AnalysisCase(
        "modal_sweep",
        {
            "speeds_rad_s": speeds,
            "with_eigenvectors": True,
            "with_kappa": True,
        },
        "Campbell — M1 extension",
        {"nx": 2.0},
    )
    window = MainWindow(session=ProjectSession(RotorProject("Campbell E2E", model, [case])))
    qtbot.addWidget(window)
    window.show()

    with qtbot.waitSignal(window.session.resultAdded, timeout=60000) as signal:
        assert window.run_analysis(case) is True

    record = signal.args[0]
    assert isinstance(record.execution.result, list)
    assert len(record.execution.result) == 3
    assert all(isinstance(item, ModalResult) for item in record.execution.result)
    assert all(item.metadata["backend"] == "Fortran2018/ctypes" for item in record.execution.result)

    widgets = [
        window.workspace.widget(i) for i in range(window.workspace.count())
        if isinstance(window.workspace.widget(i), CampbellResultView)
    ]
    assert len(widgets) == 1
    assert widgets[0].tabs.count() == 3
    assert widgets[0].summary.rowCount() > 0


@pytest.mark.skipif(
    not os.environ.get("DRMROTOR_LIB"),
    reason="real Fortran library is required for Stage 2 critical-speed qualification",
)
def test_critical_speed_workspace_uses_real_fortran(qtbot):
    example = _load_example_05_08_01()
    model = example.build(6)
    case = AnalysisCase(
        "critical_speeds",
        {"NX": 1.0, "damped": True, "ncrit": 3},
        "Critical Speeds — E2E",
    )
    window = MainWindow(session=ProjectSession(RotorProject("Critical E2E", model, [case])))
    qtbot.addWidget(window)
    window.show()

    with qtbot.waitSignal(window.session.resultAdded, timeout=60000) as signal:
        assert window.run_analysis(case) is True

    record = signal.args[0]
    assert isinstance(record.execution.result, CriticalSpeedResult)
    values = np.asarray(record.execution.result.critical_speeds_rad_s)
    assert values.shape == (3,)
    assert np.all(np.isfinite(values))

    widgets = [
        window.workspace.widget(i) for i in range(window.workspace.count())
        if isinstance(window.workspace.widget(i), CriticalSpeedResultView)
    ]
    assert len(widgets) == 1
    assert widgets[0].table.rowCount() == 3
