from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from drm_core import AnalysisCase, RotorProject
from drm_core.units import rpm_to_rad_s
from drm_studio.application.session import ProjectSession, EntityRef
from drm_studio.main_window import MainWindow

ROOT = Path(__file__).resolve().parents[2]


def _model():
    path = ROOT / "examples" / "chapter05" / "example_05_08_01.py"
    spec = importlib.util.spec_from_file_location("disk_ui_example", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build(6)


def test_geometric_disk_edit_uses_canonical_si_and_undo(qtbot):
    session = ProjectSession(RotorProject("disk sentinel", _model()))
    window = MainWindow(session=session)
    qtbot.addWidget(window)
    session.set_selection(EntityRef("disk", 0))
    editor = window.property_dock.disk_tab

    assert editor.type_combo.currentData() in (1, 3)
    editor.od.setValue(301.217)
    editor.od.editingFinished.emit()
    assert session.project.model.disks[0].p5 == pytest.approx(0.301217)

    session.undo_stack.undo()
    assert session.project.model.disks[0].p5 != pytest.approx(0.301217)


def test_disk_type_change_is_undoable(qtbot):
    session = ProjectSession(RotorProject("disk type", _model()))
    window = MainWindow(session=session)
    qtbot.addWidget(window)
    session.set_selection(EntityRef("disk", 0))
    editor = window.property_dock.disk_tab
    original = session.project.model.disks[0]

    editor.type_combo.setCurrentIndex(editor.type_combo.findData(2))
    assert session.project.model.disks[0].disk_type == 2
    session.undo_stack.undo()
    assert session.project.model.disks[0] == original


@pytest.mark.skipif(not os.environ.get("DRMROTOR_LIB"), reason="real Fortran library required")
def test_disk_edit_then_modal_real_fortran(qtbot):
    session = ProjectSession(RotorProject("disk e2e", _model()))
    window = MainWindow(session=session)
    qtbot.addWidget(window)
    window.show()
    session.set_selection(EntityRef("disk", 0))
    editor = window.property_dock.disk_tab
    editor.thickness.setValue(71.413)
    editor.thickness.editingFinished.emit()
    assert session.project.model.disks[0].p4 == pytest.approx(0.071413)

    case = AnalysisCase(
        "modal",
        {
            "speed_rad_s": float(rpm_to_rad_s(2000.0)),
            "with_eigenvectors": True,
            "with_kappa": True,
        },
        "Disk Edited Modal",
    )
    with qtbot.waitSignal(session.resultAdded, timeout=60000) as signal:
        assert window.run_analysis(case)
    record = signal.args[0]
    assert record.execution.build_metadata["backend"] == "Fortran2018/ctypes"
    assert np.isfinite(record.execution.result.eigenvalues).all()
