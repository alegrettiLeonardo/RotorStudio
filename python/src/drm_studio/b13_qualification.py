from __future__ import annotations

import json
from pathlib import Path

from drm_core import Node, RotorModel, RotorProject
from drm_studio.application.session import ProjectSession
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


def run_b13_frozen_crud_smoke(window, output_dir) -> dict:
    """Exercise the B13 GUI-draft -> command -> persistence chain in a frozen app.

    The editors are real PySide6 B13 widgets. No solver is invoked merely to
    construct/read the advanced bearings.
    """

    output_dir = Path(output_dir)
    model = RotorModel(nodes=[Node(1, 0.0), Node(2, 1.0)])
    session = ProjectSession(RotorProject("B13 Frozen CRUD", model), parent=window)

    built = []
    for family, tag in (
        (FAMILY_COEFFICIENT, "Frozen Coefficient"),
        (FAMILY_PLAIN, "Frozen Plain"),
        (FAMILY_TILTING, "Frozen Tilting"),
    ):
        editor = AdvancedBearingEditor(model, family=family, parent=window)
        editor.tag_edit.setText(tag)
        editor.node_combo.setCurrentIndex(editor.node_combo.findData(1))
        if family == FAMILY_COEFFICIENT:
            editor.speed_axis.setText("101, 202")
            editor.frequency_axis.setText("303, 404")
            editor.interpolation_combo.setCurrentText("linear")
            rows = {name: row for row, name in enumerate(editor.coeff_names)}
            editor.coeff_table.item(rows["Kxx"], 1).setText("[[11,12],[21,22]]")
            editor.coeff_table.item(rows["Cxx"], 1).setText("[[1.1,1.2],[2.1,2.2]]")
            editor.coeff_table.item(rows["Mxx"], 1).setText("[[0.11,0.12],[0.21,0.22]]")
        else:
            editor.journal_diameter_mm.setText("101.6")
            editor.clearance_um.setText("74.9")
            if family == FAMILY_TILTING:
                editor.pad_thickness_mm.setText("12.7")
        built.append(editor.bearing())

    for bearing in built:
        session.undo_stack.push(AddAdvancedBearingCommand(session, bearing))

    if len(model.advanced_bearings) != 3:
        raise RuntimeError("B13 frozen create did not produce three advanced bearings")

    # One transactional Edit per family.
    edited = []
    for index, old in enumerate(list(model.advanced_bearings)):
        editor = AdvancedBearingEditor(model, bearing=old, parent=window)
        editor.tag_edit.setText(old.tag + " edited")
        if index == 1:
            editor.journal_diameter_mm.setText("102.4")
        if index == 2:
            editor.clearance_um.setText("75.3")
        new = editor.bearing()
        session.undo_stack.push(EditAdvancedBearingCommand(session, index, new))
        edited.append(new)

    # Exercise duplicate/delete/undo without changing the final three-object set.
    session.undo_stack.push(DuplicateAdvancedBearingCommand(session, 0))
    if len(model.advanced_bearings) != 4:
        raise RuntimeError("B13 frozen duplicate did not add an independent entity")
    session.undo_stack.push(DeleteAdvancedBearingCommand(session, 3))
    if len(model.advanced_bearings) != 3:
        raise RuntimeError("B13 frozen delete did not remove the duplicate")
    session.undo_stack.undo()
    if len(model.advanced_bearings) != 4:
        raise RuntimeError("B13 frozen undo delete did not restore the duplicate")
    session.undo_stack.undo()
    if model.advanced_bearings != edited:
        raise RuntimeError("B13 frozen undo duplicate did not restore the edited three-object set")

    save_path = output_dir / "B13_FROZEN_CRUD.rds"
    session.save(save_path)
    reopened = ProjectSession()
    reopened.open_project(save_path)
    if reopened.project.model.advanced_bearings != edited:
        raise RuntimeError("B13 frozen save/reopen changed an advanced-bearing engineering object")

    payload = {
        "status": "PASS",
        "families": [type(x).__name__ for x in edited],
        "count": len(edited),
        "save_reopen": "PASS",
        "undo_redo": "PASS",
        "duplicate_delete": "PASS",
        "saved_project": str(save_path),
    }
    (output_dir / "B13_FROZEN_CRUD.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True)
    )
    return payload
