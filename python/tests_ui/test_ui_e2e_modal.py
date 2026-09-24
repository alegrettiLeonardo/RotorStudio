from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from drm_core import AnalysisCase, ModalResult, RotorProject, save_project
from drm_core.units import rpm_to_rad_s
from drm_studio.application.session import ProjectSession
from drm_studio.main_window import MainWindow
from drm_studio.result_views.modal_view import ModalResultView


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
