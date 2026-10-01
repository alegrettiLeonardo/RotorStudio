from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from drm_core import Force, load_irdin_project
from drm_core.analysis.irdin_lateral import (
    build_expanded_state,
    probe_value,
    rotate_probe_pair,
    run_irdin_modal,
    run_irdin_synchronous,
    run_irdin_synchronous_sweep,
)
from drm_core.domain.model import ResponseProbe
from drm_core.solver.irdin_support_analysis import expanded_modal, expanded_synchronous

ROOT=Path(__file__).resolve().parents[2]
CASE=ROOT/"validation/irdin/cases/ST41_1000_B3_60HZ_1675_63536.txt"


def test_i9_modal_diagonal_system_has_exact_natural_frequencies():
    M=np.diag([2.0,3.0])
    C=np.zeros((2,2))
    K=np.diag([8.0,27.0])
    result=expanded_modal(M,C,K)
    assert result.eigenvalues.shape==(4,)
    np.testing.assert_allclose(
        np.sort(np.abs(result.eigenvalues)),
        np.array([2.0,2.0,3.0,3.0]),
        rtol=2e-13,atol=2e-13,
    )
    assert result.eigenvectors.shape==(2,4)
    assert np.isfinite(result.eigenvectors).all()


def test_i9_synchronous_matches_legacy_resp_f_unbalance_orientation():
    M=np.eye(4)
    C=np.zeros((4,4))
    K=np.diag([100.0,120.0,140.0,160.0])
    omega=2.0;u=0.1;phase=0.3
    result=expanded_synchronous(
        M,C,K,nnode=1,omega_rad_s=omega,
        forces=[Force(1,(1,u,phase))],
    )
    p=u*omega**2*np.exp(1j*phase)
    expected=np.zeros(4,dtype=np.complex128)
    expected[0]=(-1j*p)/(100.0-omega**2)
    expected[1]=p/(120.0-omega**2)
    np.testing.assert_allclose(result.response,expected,rtol=2e-13,atol=2e-15)
    assert result.residual<=1e-14


def test_i9_probe_rotation_matches_frozen_legacy_vrotate():
    x=1.25+2.5j;z=-3.0+0.75j;angle=0.37
    xr,zr=rotate_probe_pair(x,z,angle)
    assert xr==pytest.approx(x*math.cos(angle)+z*math.sin(angle))
    assert zr==pytest.approx(z*math.cos(angle)-x*math.sin(angle))
    q=np.array([x,z,0j,0j])
    assert probe_value(q,ResponseProbe(1,1,angle))==pytest.approx(xr)
    assert probe_value(q,ResponseProbe(1,2,angle))==pytest.approx(zr)


def test_i9_st41_expanded_state_modal_and_synchronous_are_finite():
    p=load_irdin_project(CASE)
    speed=1000.0*2.0*math.pi/60.0
    state=build_expanded_state(p,speed)
    nd=4*len(p.model.nodes)+2*len(p.model.supports)
    assert state.M.shape==(nd,nd)
    assert state.C.shape==(nd,nd)
    assert state.K.shape==(nd,nd)
    assert len(state.bearing_metadata)==2

    modal=run_irdin_modal(p,speed)
    assert modal.eigenvalues.shape==(2*nd,)
    assert modal.eigenvectors.shape==(nd,2*nd)
    assert np.isfinite(modal.eigenvalues).all()
    assert np.isfinite(modal.eigenvectors).all()

    response=run_irdin_synchronous(p,speed)
    assert response.response.shape==(nd,)
    assert np.isfinite(response.response).all()
    assert response.residual<=1e-12


def test_i9_st41_probe_sweep_has_four_legacy_channels_and_preserves_blocker():
    p=load_irdin_project(CASE)
    speeds=np.array([500.0,1000.0,1800.0])*2.0*math.pi/60.0
    result=run_irdin_synchronous_sweep(p,speeds)
    assert result.full_response.shape[1]==3
    assert result.probe_response.shape==(4,3)
    assert np.isfinite(result.probe_response).all()
    assert np.all(result.residual<=1e-12)
    readiness=p.metadata["numerical_readiness"]
    assert readiness["status"]=="BLOCKED_FOR_NUMERICAL_ANALYSIS"
    assert readiness["components"]["support_native_assembly"]=="PASS_I8_GLOBAL_MATRICES"
    assert "IRDIN_EXPANDED_SOLVER_UNQUALIFIED" in {x["code"] for x in readiness["blockers"]}


def test_i9_rejects_non_unbalance_force_contract():
    M=np.eye(4);C=np.zeros((4,4));K=np.eye(4)*100.0
    with pytest.raises(ValueError,match="Force type 1"):
        expanded_synchronous(
            M,C,K,nnode=1,omega_rad_s=1.0,
            forces=[Force(2,(1,1.0,0.0))],
        )
