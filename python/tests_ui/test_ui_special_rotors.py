from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest

from drm_core import AnalysisCase, RotorProject, RotorDefinition, Bearing
from drm_core.analysis.coaxial import CoaxialModalResult, CoaxialFrequencyResponseResult
from drm_core.analysis.asymmetric import AsymmetricModalResult, AsymmetricFrequencyResponseResult
from drm_core.units import rpm_to_rad_s
from drm_studio.analysis_pages.special_rotor_setup import SpecialRotorSetupDialog
from drm_studio.application.session import ProjectSession
from drm_studio.commands import ReplaceRotorDefinitionsCommand
from drm_studio.main_window import MainWindow
from drm_studio.result_views import SpecialRotorResultView

ROOT=Path(__file__).resolve().parents[2]

def _load(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);assert spec.loader is not None;spec.loader.exec_module(module);return module

def test_coaxial_dialog_preserves_negative_speed_factor(qtbot):
    dialog=SpecialRotorSetupDialog("coaxial",rotor_definitions=[RotorDefinition(1,8,1.0),RotorDefinition(9,13,-1.5)])
    qtbot.addWidget(dialog)
    values=dialog.rotor_definitions()
    assert values[1].speed_factor == -1.5

def test_rotor_definition_edit_is_undoable(qtbot):
    example=_load("examples/chapter06/example_06_06_01.py","coax_cmd")
    session=ProjectSession(RotorProject("coax",example.build(1)))
    old=list(session.project.model.rotors)
    new=[RotorDefinition(1,8,1.0),RotorDefinition(9,13,-1.25)]
    session.undo_stack.push(ReplaceRotorDefinitionsCommand(session,new))
    assert session.project.model.rotors[1].speed_factor == -1.25
    session.undo_stack.undo();assert session.project.model.rotors == old
    session.undo_stack.redo();assert session.project.model.rotors == new

@pytest.mark.skipif(not os.environ.get("DRMROTOR_LIB"),reason="real Fortran library required")
def test_coaxial_modal_and_response_e2e(qtbot):
    example=_load("examples/chapter06/example_06_06_01.py","coax_e2e")
    window=MainWindow(session=ProjectSession(RotorProject("Coaxial E2E",example.build(1))));qtbot.addWidget(window);window.show()
    modal=AnalysisCase("coaxial_modal",{"speed_rad_s":float(rpm_to_rad_s(3000.0))},"Coaxial Modal")
    with qtbot.waitSignal(window.session.resultAdded,timeout=60000) as s:assert window.run_analysis(modal)
    rec=s.args[0];assert isinstance(rec.execution.result,CoaxialModalResult);assert rec.execution.build_metadata["backend"]=="Fortran2018/ctypes"
    assert np.isfinite(rec.execution.result.eigenvalues).all()
    assert any(isinstance(window.workspace.widget(i),SpecialRotorResultView) for i in range(window.workspace.count()))
    response=AnalysisCase("coaxial_frequency_response",{"speeds_rad_s":[float(rpm_to_rad_s(v)) for v in (100.0,500.0,1000.0)]},"Coaxial Response",{"outnodes":[2.1]})
    with qtbot.waitSignal(window.session.resultAdded,timeout=60000) as s2:assert window.run_analysis(response)
    assert isinstance(s2.args[0].execution.result,CoaxialFrequencyResponseResult)

@pytest.mark.skipif(not os.environ.get("DRMROTOR_LIB"),reason="real Fortran library required")
def test_asymmetric_modal_and_response_e2e(qtbot):
    example=_load("examples/chapter07/example_07_06_01.py","asym_e2e")
    window=MainWindow(session=ProjectSession(RotorProject("Asymmetric E2E",example.build(1))));qtbot.addWidget(window);window.show()
    modal=AnalysisCase("asymmetric_modal",{"speed_rad_s":float(rpm_to_rad_s(2000.0)),"with_eigenvectors":True},"Asymmetric Modal")
    with qtbot.waitSignal(window.session.resultAdded,timeout=60000) as s:assert window.run_analysis(modal)
    rec=s.args[0];assert isinstance(rec.execution.result,AsymmetricModalResult);assert rec.execution.build_metadata["backend"]=="Fortran2018/ctypes"
    response=AnalysisCase("asymmetric_frequency_response",{"speeds_rad_s":[float(rpm_to_rad_s(v)) for v in (100.0,500.0,1000.0)]},"Asymmetric Response",{"outnodes":[3.1]})
    with qtbot.waitSignal(window.session.resultAdded,timeout=60000) as s2:assert window.run_analysis(response)
    assert isinstance(s2.args[0].execution.result,AsymmetricFrequencyResponseResult)

def test_asymmetric_rejects_fluid_bearing_before_solver(qtbot):
    example=_load("examples/chapter07/example_07_06_01.py","asym_invalid")
    model=example.build(1);model.bearings[0]=Bearing(7,model.bearings[0].node,(100.0,0.05,0.02,1e-4,0.02))
    window=MainWindow(session=ProjectSession(RotorProject("invalid",model)));qtbot.addWidget(window)
    assert window.run_analysis(AnalysisCase("asymmetric_modal",{"speed_rad_s":100.0},"Invalid Asym")) is False
