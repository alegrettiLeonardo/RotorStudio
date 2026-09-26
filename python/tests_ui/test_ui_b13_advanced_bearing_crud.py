from __future__ import annotations

import math

import pytest
from PySide6.QtWidgets import QDialog

from drm_core import Node, RotorModel, RotorProject
from drm_core.domain.bearings import (
    CoefficientBearing,
    PlainJournalPhysicsBearing,
    TiltingPadPhysicsBearing,
)
from drm_studio.application.session import EntityRef, ProjectSession
from drm_studio.commands import (
    AddAdvancedBearingCommand,
    DeleteAdvancedBearingCommand,
    DuplicateAdvancedBearingCommand,
    EditAdvancedBearingCommand,
)
from drm_studio.docks.advanced_bearing_editor import (
    AdvancedBearingEditor,
    FAMILY_COEFFICIENT,
    FAMILY_PLAIN,
    FAMILY_TILTING,
)
from drm_studio.docks.project_explorer import ProjectExplorerDock


def _project():
    return RotorProject(
        "B13 UI",
        RotorModel(nodes=[Node(1, 0.0), Node(2, 0.5), Node(3, 1.0)]),
    )


def _set_pad(editor, row, pivot, arc, length, preload, offset, krotate=None):
    values = [pivot, arc, length, preload, offset]
    if krotate is not None:
        values.append(krotate)
    for col, value in enumerate(values, 1):
        editor.pads.item(row, col).setText(str(value))


def test_b13_plain_gui_input_converts_exactly_to_si(qtbot):
    model = _project().model
    editor = AdvancedBearingEditor(model, family=FAMILY_PLAIN)
    qtbot.addWidget(editor)
    editor.node_combo.setCurrentIndex(editor.node_combo.findData(2))
    editor.tag_edit.setText("PJ GUI")
    editor.weight.setText("1234.5")
    editor.journal_diameter_mm.setText("101.6")
    editor.clearance_um.setText("74.9")
    editor.oil_viscosity.setText("0.0197")
    editor.pads.setRowCount(0)
    editor.add_pad((90.0, 176.0, 50.1, 0.11, 0.49))
    editor.add_pad((270.0, 175.0, 50.2, 0.12, 0.51))

    bearing = editor.bearing()
    assert type(bearing) is PlainJournalPhysicsBearing
    assert bearing.node == 2
    assert bearing.tag == "PJ GUI"
    assert bearing.journal_diameter_m == pytest.approx(0.1016, rel=0, abs=1e-15)
    assert bearing.radial_clearance_m == pytest.approx(74.9e-6, rel=0, abs=1e-15)
    assert bearing.pivot_angle_rad == pytest.approx((math.pi / 2.0, 3.0 * math.pi / 2.0))
    assert bearing.pad_axial_length_m == pytest.approx((0.0501, 0.0502))


def test_b13_tilting_gui_five_pad_sentinels_are_not_permuted(qtbot):
    model = _project().model
    editor = AdvancedBearingEditor(model, family=FAMILY_TILTING)
    qtbot.addWidget(editor)
    editor.tag_edit.setText("TP GUI")
    editor.journal_diameter_mm.setText("101.6")
    editor.clearance_um.setText("74.9")
    editor.pad_thickness_mm.setText("12.7")
    editor.pad_density.setText("7835.6")

    pivots = [18, 90, 162, 234, 306]
    arcs = [58, 59, 60, 61, 62]
    lengths = [50.1, 50.2, 50.3, 50.4, 50.5]
    preloads = [0.41, 0.42, 0.43, 0.44, 0.45]
    offsets = [0.46, 0.47, 0.48, 0.49, 0.50]
    krots = [101001, 102002, 103003, 104004, 105005]
    for i in range(5):
        _set_pad(editor, i, pivots[i], arcs[i], lengths[i], preloads[i], offsets[i], krots[i])

    bearing = editor.bearing()
    assert type(bearing) is TiltingPadPhysicsBearing
    assert bearing.journal_diameter_m == pytest.approx(0.1016, rel=0, abs=1e-15)
    assert bearing.radial_clearance_m == pytest.approx(74.9e-6, rel=0, abs=1e-15)
    assert bearing.pad_thickness_m == pytest.approx(0.0127, rel=0, abs=1e-15)
    assert bearing.pivot_angle_rad == pytest.approx(tuple(math.radians(x) for x in pivots))
    assert bearing.pad_arc_rad == pytest.approx(tuple(math.radians(x) for x in arcs))
    assert bearing.pad_axial_length_m == pytest.approx(tuple(x * 1e-3 for x in lengths))
    assert bearing.preload == pytest.approx(tuple(preloads))
    assert bearing.offset == pytest.approx(tuple(offsets))
    assert bearing.k_rotate_nm_rad == pytest.approx(tuple(krots))


def test_b13_coefficient_gui_builds_2d_kcm_without_zeroing_mass(qtbot):
    model = _project().model
    editor = AdvancedBearingEditor(model, family=FAMILY_COEFFICIENT)
    qtbot.addWidget(editor)
    editor.speed_axis.setText("101, 202")
    editor.frequency_axis.setText("303, 404, 505")
    editor.interpolation_combo.setCurrentText("linear")
    rows = {name: row for row, name in enumerate(editor.coeff_names)}
    editor.coeff_table.item(rows["Kxx"], 1).setText("[[11,12,13],[21,22,23]]")
    editor.coeff_table.item(rows["Cxx"], 1).setText("[[1.1,1.2,1.3],[2.1,2.2,2.3]]")
    editor.coeff_table.item(rows["Mxx"], 1).setText("[[0.11,0.12,0.13],[0.21,0.22,0.23]]")
    # Any coefficient may be scalar while axes exist.
    for name in ("Kxy", "Kyx", "Kyy", "Cxy", "Cyx", "Cyy", "Mxy", "Myx", "Myy"):
        editor.coeff_table.item(rows[name], 1).setText("0")

    bearing = editor.bearing()
    assert type(bearing) is CoefficientBearing
    assert bearing.speed_rad_s == (101.0, 202.0)
    assert bearing.frequency_rad_s == (303.0, 404.0, 505.0)
    assert bearing.interpolation == "linear"
    assert bearing.kxx == [[11.0, 12.0, 13.0], [21.0, 22.0, 23.0]]
    assert bearing.mxx == [[0.11, 0.12, 0.13], [0.21, 0.22, 0.23]]


def test_b13_commands_add_edit_delete_duplicate_undo_redo_and_selection(qtbot):
    session = ProjectSession(_project())
    first = CoefficientBearing(node=1, kxx=1.01e6, cxx=101.0, tag="A")
    second = CoefficientBearing(node=2, kxx=2.02e6, cxx=202.0, tag="B")

    session.undo_stack.push(AddAdvancedBearingCommand(session, first))
    assert session.project.model.advanced_bearings == [first]
    assert session.selection == EntityRef("advanced_bearing", 0)
    session.undo_stack.undo()
    assert session.project.model.advanced_bearings == []
    session.undo_stack.redo()
    assert session.project.model.advanced_bearings == [first]

    session.undo_stack.push(EditAdvancedBearingCommand(session, 0, second))
    assert session.project.model.advanced_bearings[0] == second
    session.undo_stack.undo()
    assert session.project.model.advanced_bearings[0] == first
    session.undo_stack.redo()
    assert session.project.model.advanced_bearings[0] == second

    session.undo_stack.push(DuplicateAdvancedBearingCommand(session, 0))
    assert len(session.project.model.advanced_bearings) == 2
    original, copied = session.project.model.advanced_bearings
    assert copied.tag == "B copy"
    session.undo_stack.push(
        EditAdvancedBearingCommand(
            session, 1,
            CoefficientBearing(node=2, kxx=9.99e6, cxx=202.0, tag="B copy"),
        )
    )
    assert session.project.model.advanced_bearings[0] == original
    session.undo_stack.undo()
    session.undo_stack.undo()
    assert len(session.project.model.advanced_bearings) == 1

    session.undo_stack.push(DeleteAdvancedBearingCommand(session, 0))
    assert session.project.model.advanced_bearings == []
    assert session.selection is None
    session.undo_stack.undo()
    assert session.project.model.advanced_bearings == [second]
    assert session.selection == EntityRef("advanced_bearing", 0)


def test_b13_edit_cancel_and_invalid_input_leave_model_and_hash_unchanged(qtbot):
    bearing = TiltingPadPhysicsBearing(
        node=1,
        weight_n=1000.0,
        journal_diameter_m=0.1016,
        radial_clearance_m=74.9e-6,
        oil_viscosity_pa_s=0.02,
        pad_thickness_m=0.0127,
        pad_density_kg_m3=7800.0,
        pivot_angle_rad=tuple(math.radians(x) for x in (18, 90, 162, 234, 306)),
        pad_arc_rad=tuple(math.radians(60) for _ in range(5)),
        pad_axial_length_m=tuple(0.05 for _ in range(5)),
        preload=tuple(0.4 for _ in range(5)),
        offset=tuple(0.5 for _ in range(5)),
        k_rotate_nm_rad=tuple(0.0 for _ in range(5)),
        provenance={"qualification": "ROSS_PARITY_PASS_B12", "ross_authority_sha": "authority-sentinel"},
    )
    project = _project()
    project.model.advanced_bearings.append(bearing)
    session = ProjectSession(project)
    before_hash = session.current_model_hash

    editor = AdvancedBearingEditor(session.project.model, bearing=bearing)
    qtbot.addWidget(editor)
    assert editor.provenance_json.isReadOnly()
    editor.journal_diameter_mm.setText("111.111")
    editor.reject()
    assert session.project.model.advanced_bearings[0] == bearing
    assert session.current_model_hash == before_hash

    bad = AdvancedBearingEditor(session.project.model, bearing=bearing)
    qtbot.addWidget(bad)
    bad.pads.item(0, 4).setText("1.05")
    with pytest.raises(ValueError, match=r"received 1.05; expected 0 <= preload < 1"):
        bad.bearing()
    assert session.project.model.advanced_bearings[0] == bearing
    assert session.current_model_hash == before_hash


def test_b13_save_reopen_same_engineering_objects(qtbot, tmp_path):
    project = _project()
    model = project.model

    coeff_editor = AdvancedBearingEditor(model, family=FAMILY_COEFFICIENT)
    qtbot.addWidget(coeff_editor)
    coeff_editor.tag_edit.setText("coeff")
    coeff = coeff_editor.bearing()

    plain_editor = AdvancedBearingEditor(model, family=FAMILY_PLAIN)
    qtbot.addWidget(plain_editor)
    plain_editor.tag_edit.setText("plain")
    plain_editor.journal_diameter_mm.setText("101.6")
    plain_editor.clearance_um.setText("74.9")
    plain = plain_editor.bearing()

    tilting_editor = AdvancedBearingEditor(model, family=FAMILY_TILTING)
    qtbot.addWidget(tilting_editor)
    tilting_editor.tag_edit.setText("tilting")
    tilting_editor.journal_diameter_mm.setText("101.6")
    tilting_editor.clearance_um.setText("74.9")
    tilting = tilting_editor.bearing()

    session = ProjectSession(project)
    for item in (coeff, plain, tilting):
        session.undo_stack.push(AddAdvancedBearingCommand(session, item))

    path = tmp_path / "b13-ui-roundtrip.rds"
    session.save(path)
    reopened = ProjectSession()
    reopened.open_project(path)
    assert reopened.project.model.advanced_bearings == session.project.model.advanced_bearings


def test_b13_project_explorer_root_and_entity_contexts(qtbot):
    project = _project()
    project.model.advanced_bearings.append(
        CoefficientBearing(node=1, kxx=1e6, cxx=100.0, tag="tree sentinel")
    )
    session = ProjectSession(project)
    dock = ProjectExplorerDock(session)
    qtbot.addWidget(dock)
    dock.show()

    root_context = None
    entity_context = None

    def walk(parent):
        nonlocal root_context, entity_context
        for row in range(dock.model.rowCount(parent)):
            idx = dock.model.index(row, 0, parent)
            context = dock.model.data(idx, dock.model.ContextRole)
            ref = dock.model.data(idx, dock.model.EntityRole)
            if context == "advanced_bearings_root":
                root_context = idx
            if ref == EntityRef("advanced_bearing", 0):
                entity_context = idx
            walk(idx)

    from PySide6.QtCore import QModelIndex
    walk(QModelIndex())
    assert root_context is not None and root_context.isValid()
    assert entity_context is not None and entity_context.isValid()
    assert "tree sentinel" in str(dock.model.data(entity_context))
