from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtWidgets import QToolButton

from drm_core import AnalysisCase, AnalysisService, RotorProject
from drm_core.post.modes import plot_mode_3d
from drm_core.units import rpm_to_rad_s
from drm_studio.application.session import ProjectSession
from drm_studio.main_window import MainWindow
from drm_studio.widgets import BearingPerformancePage


ROOT = Path(__file__).resolve().parents[2]


def _example_model():
    path = ROOT / "examples" / "chapter05" / "example_05_08_01.py"
    spec = importlib.util.spec_from_file_location("stage21_visual_example", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build(6)


def test_mockup_toolbar_and_workspace_structure(qtbot):
    session = ProjectSession(RotorProject("Visual Conformance", _example_model()))
    window = MainWindow(session=session)
    qtbot.addWidget(window)
    window.show()

    assert window.project_dock.minimumWidth() >= 245
    assert window.property_dock.minimumWidth() >= 330

    required_actions = [
        window.model_toolbar_action,
        window.analysis_toolbar_action,
        window.results_toolbar_action,
        window.repeat_toolbar_action,
        window.report_action,
        window.zoom_in_toolbar_action,
        window.zoom_out_toolbar_action,
        window.fit_toolbar_action,
        window.pan_toolbar_action,
        window.help_toolbar_action,
    ]
    assert all(not action.icon().isNull() for action in required_actions)

    cards = list(window.model_page.modules.buttons.values())
    assert len(cards) == 10
    assert all(isinstance(button, QToolButton) for button in cards)
    assert all(not button.icon().isNull() for button in cards)

    window._open_bearing_performance()
    assert isinstance(window.bearing_page, BearingPerformancePage)
    assert window.workspace.currentWidget() is window.bearing_page


@pytest.mark.skipif(
    not os.environ.get("DRMROTOR_LIB"),
    reason="real Fortran library is required for Stage 2.1 mode-shape qualification",
)
def test_real_modal_mode_shape_3d_contains_centerline_reference_and_orbits():
    model = _example_model()
    case = AnalysisCase(
        "modal",
        {
            "speed_rad_s": float(rpm_to_rad_s(4000.0)),
            "with_eigenvectors": True,
            "with_kappa": True,
        },
        "Stage 2.1 3D Mode Shape",
    )
    execution = AnalysisService().execute(RotorProject("mode3d", model), case)
    result = execution.result
    eig = np.asarray(result.eigenvalues)
    positive = np.flatnonzero(eig.imag > 1e-10)
    idx = int(positive[0] if positive.size else 0)

    import matplotlib.pyplot as plt

    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    plot_mode_3d(model, np.asarray(result.eigenvectors)[:, idx], eig[idx], ax=ax)

    colors = [line.get_color() for line in ax.lines]
    assert "red" in colors
    assert "#ff35f2" in colors
    assert "black" in colors
    assert len(ax.lines) >= len(model.nodes) + 2
    assert ax.get_xlabel() == "X"
    assert ax.get_ylabel() == "Y"
    assert ax.get_zlabel() == "Z"
    plt.close(fig)
