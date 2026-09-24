import copy

import numpy as np

from drm_core import (
    Node, ShaftElement, Bearing, RotorModel, RotorProject,
    AnalysisCase, AnalysisExecution
)
from drm_studio.application.session import ProjectSession, EntityRef
from drm_studio.commands.model_commands import SetShaftPropertyCommand
from drm_studio.main_window import MainWindow


def demo_project():
    model = RotorModel(
        nodes=[Node(1, 0.0), Node(2, 0.120)],
        shafts=[
            ShaftElement(
                2, 1, 2,
                0.050, 0.0,
                7831.7, 207321.0e6, 81.0e9, 0.001,
            )
        ],
        bearings=[Bearing(1, 1), Bearing(1, 2)],
    )
    return RotorProject("UI Sentinel", model)


def test_property_edit_uses_domain_si_and_undo_redo(qtbot):
    session = ProjectSession(demo_project())
    window = MainWindow(session=session)
    qtbot.addWidget(window)
    window.show()

    session.set_selection(EntityRef("shaft", 0))
    assert window.project_dock.tree.currentIndex().isValid()
    assert np.isclose(window.property_dock.do_field.value(), 50.0)

    window.property_dock.do_field.setValue(53.217)
    window.property_dock.do_field.editingFinished.emit()

    assert np.isclose(session.project.model.shafts[0].outer_diameter_m, 0.053217)
    assert session.dirty

    session.undo_stack.undo()
    assert np.isclose(session.project.model.shafts[0].outer_diameter_m, 0.050)

    session.undo_stack.redo()
    assert np.isclose(session.project.model.shafts[0].outer_diameter_m, 0.053217)


def test_invalid_inner_diameter_is_rejected_by_core_validation(qtbot):
    session = ProjectSession(demo_project())
    window = MainWindow(session=session)
    qtbot.addWidget(window)
    session.set_selection(EntityRef("shaft", 0))

    original = session.project.model.shafts[0].inner_diameter_m
    window.property_dock.di_field.setValue(60.0)
    window.property_dock.di_field.editingFinished.emit()

    assert session.project.model.shafts[0].inner_diameter_m == original
    assert "expected do > di" in window.property_dock.error_label.text()


def test_model_edit_marks_existing_result_stale(qtbot):
    session = ProjectSession(demo_project())
    case = AnalysisCase("modal", {"speed_rad_s": 100.0}, "Modal Baseline")
    fake = AnalysisExecution(
        case=case,
        result=object(),
        analysis_hash="fake",
        build_metadata={"model_hash": session.current_model_hash},
    )
    record = session.add_result(fake, model_snapshot=copy.deepcopy(session.project.model))
    assert not record.stale

    cmd = SetShaftPropertyCommand(
        session, 0, "outer_diameter_m", 0.053217, "sentinel diameter"
    )
    session.undo_stack.push(cmd)

    assert record.stale
    assert "Outdated" in record.display_name


def test_project_save_reopen_preserves_physical_model(tmp_path):
    session = ProjectSession(demo_project())
    path = tmp_path / "sentinel.rds"
    before = session.current_model_hash
    session.save(path)

    reopened = ProjectSession()
    reopened.open_project(path)
    assert reopened.current_model_hash == before
    assert np.isclose(
        reopened.project.model.shafts[0].rho_kg_m3,
        7831.7,
    )


class _NeverCalledService:
    def __init__(self):
        self.calls = 0

    def execute(self, project, case):
        self.calls += 1
        raise AssertionError("solver must not be called for invalid model")


def test_invalid_model_blocks_solver_submission(qtbot):
    project = demo_project()
    bad = project.model.shafts[0]
    project.model.shafts[0] = ShaftElement(
        bad.shaft_type, bad.node1, bad.node2,
        0.010, 0.020,
        bad.rho_kg_m3, bad.E_pa, bad.G_pa, bad.damping_factor,
    )
    service = _NeverCalledService()
    window = MainWindow(session=ProjectSession(project), analysis_service=service)
    qtbot.addWidget(window)

    ok = window.run_analysis(
        AnalysisCase("modal", {"speed_rad_s": 100.0}, "Invalid Modal")
    )
    assert ok is False
    assert service.calls == 0
    assert window.messages_dock.checks.count() == 1
