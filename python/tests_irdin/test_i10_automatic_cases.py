from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from drm_core import AnalysisCase, AnalysisService, load_irdin_project, load_project, save_project
from drm_core.importers.irdin_cases import (
    RPM_TO_RAD_S,
    campbell_speed_grid_rpm,
    response_speed_grid_rpm,
)

ROOT=Path(__file__).resolve().parents[2]
CASE=ROOT/"validation/irdin/cases/ST41_1000_B3_60HZ_1675_63536.txt"


def _project():
    return load_irdin_project(CASE)


def test_i10_st41_legacy_grids_preserve_demonstrated_semantics():
    p=_project()
    camp=campbell_speed_grid_rpm(p.metadata)
    rsp=response_speed_grid_rpm(p.metadata)
    assert camp.size==25
    assert camp[0]==0.0 and camp[-1]==3000.0
    np.testing.assert_allclose(camp,np.linspace(0.0,3000.0,25),rtol=0,atol=0)
    np.testing.assert_array_equal(rsp,np.array([300.,700.,1100.,1500.,1900.,2300.,2700.]))


def test_i10_import_creates_exact_two_qualified_legacy_cases_and_unlocks_only_them():
    p=_project()
    assert p.metadata["numerical_readiness"]["status"]=="LEGACY_NUMERIC_READY"
    assert p.metadata["numerical_readiness"]["blockers"]==[]
    comp=p.metadata["numerical_readiness"]["components"]
    assert comp["expanded_solver"]=="PASS_I9_NATIVE_MODAL_RESPONSE"
    assert comp["automatic_cases"]=="PASS_I10_LEGACY_CASES"
    assert [(c.kind,c.name) for c in p.analyses]==[
        ("irdin_modal_sweep","iRdin Campbell"),
        ("irdin_synchronous_response","iRdin Unbalance Response"),
    ]
    camp=np.asarray(p.analyses[0].parameters["speeds_rad_s"])
    rsp=np.asarray(p.analyses[1].parameters["speeds_rad_s"])
    np.testing.assert_allclose(camp/RPM_TO_RAD_S,np.linspace(0.0,3000.0,25),rtol=2e-15,atol=1e-12)
    np.testing.assert_allclose(rsp/RPM_TO_RAD_S,[300,700,1100,1500,1900,2300,2700],rtol=2e-15,atol=1e-12)


def test_i10_analysis_service_executes_only_expanded_irdin_paths():
    p=_project();svc=AnalysisService()
    small_modal=AnalysisCase(
        "irdin_modal_sweep",
        {"speeds_rad_s":[500*RPM_TO_RAD_S,1000*RPM_TO_RAD_S]},
        "I10 modal sentinel",
    )
    modal=svc.execute(p,small_modal)
    assert len(modal.result)==2
    assert all(np.isfinite(point.eigenvalues).all() for point in modal.result)

    small_rsp=AnalysisCase(
        "irdin_synchronous_response",
        {"speeds_rad_s":[500*RPM_TO_RAD_S,1000*RPM_TO_RAD_S]},
        "I10 response sentinel",
    )
    rsp=svc.execute(p,small_rsp)
    assert rsp.result.probe_response.shape==(4,2)
    assert np.isfinite(rsp.result.probe_response).all()
    assert np.all(rsp.result.residual<=1e-12)

    with pytest.raises(ValueError,match="Generic RotorStudio analyses are blocked"):
        svc.execute(p,AnalysisCase("modal",{"speed_rad_s":0.0},"unsafe generic modal"))


def test_i10_save_reopen_preserves_readiness_and_automatic_cases(tmp_path):
    p=_project();path=tmp_path/"st41-i10.rds";save_project(p,path);q=load_project(path)
    assert q.metadata["numerical_readiness"]==p.metadata["numerical_readiness"]
    assert [x.canonical_dict() for x in q.analyses]==[x.canonical_dict() for x in p.analyses]
    assert q.model.model_hash()==p.model.model_hash()
