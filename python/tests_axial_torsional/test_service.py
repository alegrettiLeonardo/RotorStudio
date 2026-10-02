from __future__ import annotations
import numpy as np
from drm_core import (
    RotorModel,Node,ShaftElement,AnalysisCase,AnalysisService,RotorProject,save_project,load_project,
    run_axial_modal_6dof,run_torsional_modal_6dof,
)
from drm_core.solver.facade import SolverFacade

def simple_model():
    return RotorModel(
        nodes=[Node(1,0.0),Node(2,0.25)],
        shafts=[ShaftElement(2,1,2,0.05,0.0,7810.0,211e9,81.2e9,0.0,0.0,0.0)],
    )

def test_b3_analysis_service_modal_dispatch():
    model=simple_model();service=AnalysisService()
    axial=service.execute(model,AnalysisCase("axial_modal",{"speed_rad_s":0.0},"Axial"))
    torsion=service.execute(model,AnalysisCase("torsional_modal",{"speed_rad_s":0.0},"Torsional"))
    assert axial.result.family=="Axial" and torsion.result.family=="Torsional"
    assert axial.result.metadata["analysis_hash"]==axial.analysis_hash
    assert torsion.result.metadata["analysis_hash"]==torsion.analysis_hash

def test_b3_analysis_service_sweep_and_project_roundtrip(tmp_path):
    model=simple_model()
    cases=[
        AnalysisCase("axial_sweep",{"speed_range_rad_s":[0.0,100.0,200.0]},"Axial sweep"),
        AnalysisCase("torsional_sweep",{"speed_range_rad_s":[0.0,100.0,200.0]},"Torsional sweep"),
    ]
    project=RotorProject("B3",model,cases)
    path=save_project(project,tmp_path/"b3.rds")
    reopened=load_project(path)
    service=AnalysisService()
    for case in reopened.analyses:
        result=service.execute(reopened,case)
        np.testing.assert_array_equal(result.result.speed_rad_s,[0.0,100.0,200.0])
        assert result.result.metadata["analysis_hash"]==result.analysis_hash
        assert np.max(np.abs(result.result.wn_rad_s-result.result.wn_rad_s[0:1,:]))<1e-7


def test_b3_public_core_and_facade_api():
    model=simple_model()
    assert run_axial_modal_6dof(model,0.0).family=="Axial"
    assert run_torsional_modal_6dof(model,0.0).family=="Torsional"
    facade=SolverFacade()
    assert facade.axial_modal_6dof(model,0.0).family=="Axial"
    assert facade.torsional_modal_6dof(model,0.0).family=="Torsional"
    a=facade.axial_sweep_6dof(model,[0.0,100.0])
    t=facade.torsional_sweep_6dof(model,[0.0,100.0])
    assert a.wn_rad_s.shape==(2,1)
    assert t.wn_rad_s.shape==(2,1)
