from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from drm_core import (
    AnalysisCase, RotorProject, Bearing, RotorModel, Node, ShaftElement,
    TiltingPadPhysicsBearing,
)
from drm_core.units import rpm_to_rad_s
from drm_studio.application.session import ProjectSession, EntityRef
from drm_studio.main_window import MainWindow
from drm_studio.widgets.bearing_performance import BearingPerformancePage

ROOT=Path(__file__).resolve().parents[2]

def _load_example():
    path=ROOT/"examples/chapter05/example_05_08_01.py"
    spec=importlib.util.spec_from_file_location("bearing_ui_example",path)
    module=importlib.util.module_from_spec(spec);assert spec.loader is not None;spec.loader.exec_module(module);return module

def test_type7_and_seal_fields_convert_mm_to_si(qtbot):
    model=_load_example().build(6)
    model.bearings[0]=Bearing(7,model.bearings[0].node,(1234.5,0.053217,0.017413,0.000123,0.0321))
    session=ProjectSession(RotorProject("bearing sentinel",model))
    window=MainWindow(session=session);qtbot.addWidget(window);window.show()
    session.set_selection(EntityRef("bearing",0))
    editor=window.property_dock.bearing_tab
    assert editor.type_combo.currentData()==7
    assert float(editor.table.item(1,1).text())==pytest.approx(53.217)
    assert float(editor.table.item(2,1).text())==pytest.approx(17.413)
    editor.table.item(3,1).setText("0.222")
    assert session.project.model.bearings[0].properties[3]==pytest.approx(0.000222)

    idx=editor.type_combo.findData(8);editor.type_combo.setCurrentIndex(idx)
    assert session.project.model.bearings[0].bearing_type==8
    assert len(session.project.model.bearings[0].properties)==6
    session.undo_stack.undo()
    assert session.project.model.bearings[0].bearing_type==7

def test_full_kc_type5_cross_coupling_roundtrip(qtbot):
    model=_load_example().build(6)
    model.bearings[0]=Bearing(5,model.bearings[0].node,(1.1e6,2.2e5,-3.3e5,1.4e6,11.0,22.0,-33.0,44.0))
    session=ProjectSession(RotorProject("full kc",model));window=MainWindow(session=session);qtbot.addWidget(window)
    session.set_selection(EntityRef("bearing",0));editor=window.property_dock.bearing_tab
    assert editor.table.rowCount()==8
    editor.table.item(1,1).setText("222321")
    assert session.project.model.bearings[0].properties[1]==pytest.approx(222321.0)

@pytest.mark.skipif(not os.environ.get("DRMROTOR_LIB"),reason="real Fortran library required")
def test_bearing_edit_then_modal_real_fortran(qtbot):
    model=_load_example().build(6)
    session=ProjectSession(RotorProject("bearing e2e",model))
    window=MainWindow(session=session);qtbot.addWidget(window);window.show()
    session.set_selection(EntityRef("bearing",0));editor=window.property_dock.bearing_tab
    if session.project.model.bearings[0].bearing_type!=3:
        editor.type_combo.setCurrentIndex(editor.type_combo.findData(3))
    editor.table.item(0,1).setText("1234321")
    assert session.project.model.bearings[0].properties[0]==pytest.approx(1234321.0)
    case=AnalysisCase("modal",{"speed_rad_s":float(rpm_to_rad_s(2000.0)),"with_eigenvectors":True,"with_kappa":True},"Bearing Edited Modal")
    with qtbot.waitSignal(session.resultAdded,timeout=60000) as signal:assert window.run_analysis(case)
    assert signal.args[0].execution.build_metadata["backend"]=="Fortran2018/ctypes"
    assert np.isfinite(signal.args[0].execution.result.eigenvalues).all()

@pytest.mark.skipif(
    not os.environ.get("DRMBEARINGS_LIB"),
    reason="real native advanced-bearing library required",
)
def test_bearing_performance_runs_qualified_native_tilting_pad(qtbot):
    bearing = TiltingPadPhysicsBearing(
        node=1,
        weight_n=112814.90696191376,
        journal_diameter_m=0.3999992,
        radial_clearance_m=0.000194564,
        oil_viscosity_pa_s=0.01901574061455835,
        pad_thickness_m=0.149614636,
        pad_density_kg_m3=7835.631544657211,
        pivot_angle_rad=(
            0.9424777960769379,
            2.199114857512855,
            3.4557519189487724,
            4.71238898038469,
            5.969026041820607,
        ),
        pad_arc_rad=(1.0471975511965976,) * 5,
        pad_axial_length_m=(0.263144,) * 5,
        preload=(0.3,) * 5,
        offset=(0.5,) * 5,
        k_rotate_nm_rad=(0.0,) * 5,
        total_e_x_film=20,
        total_e_z_film=10,
        xj_ratio_initial=0.15,
        yj_ratio_initial=-0.2,
        force_tolerance=5e-3,
    )
    model = RotorModel(
        nodes=[Node(1, 0.0), Node(2, 1.0)],
        shafts=[
            ShaftElement(
                2, 1, 2, 0.05, 0.0, 7810.0, 211e9, 81.2e9, 0.0, 0.0, 0.0
            )
        ],
        advanced_bearings=[bearing],
    )
    session = ProjectSession(RotorProject("native-bearing-performance", model))
    page = BearingPerformancePage(session)
    qtbot.addWidget(page)
    page.show()

    session.set_selection(EntityRef("advanced_bearing", 0))
    assert page.advanced_group.isVisible()
    assert page.evaluate_button.isEnabled()
    assert "6320eab9" in page.coefficient_note.toPlainText()

    page.speed_field.setValue(94.24777960769379)
    page.frequency_field.setValue(94.24777960769379)
    page._evaluate_advanced()

    text = page.coefficient_note.toPlainText()
    assert "ROSS_PARITY_PASS_B12" in text
    assert "K [N/m]" in text and "C [N·s/m]" in text
    assert page.lower_tabs.isTabEnabled(1)
    assert page.lower_tabs.isTabEnabled(2)
    assert "Native pressure field" in page.pressure_note.toPlainText()
    assert "Native film temperature field" in page.temperature_note.toPlainText()
    assert page._last_payload is not None
    assert np.isfinite(page._last_payload["evaluation"].K).all()

