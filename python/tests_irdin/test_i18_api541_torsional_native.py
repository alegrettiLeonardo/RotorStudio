from __future__ import annotations

import numpy as np
import pytest

from drm_core.analysis.api541_torsional_contract import (
    API541TorsionalModel,
    TorsionalConnection,
    TorsionalExcitation,
    TorsionalStation,
)
from drm_core.solver.api541_torsional_native import run_api541_torsional_modes


def _p(name):
    return {"source": name}


def _two_inertia():
    return API541TorsionalModel(
        stations=(
            TorsionalStation("J1",2.0,_p("sentinel")),
            TorsionalStation("J2",3.0,_p("sentinel")),
        ),
        connections=(
            TorsionalConnection(0,1,120.0,0.0,"K12",_p("sentinel")),
        ),
        excitations=(
            TorsionalExcitation(0,1.0,order=1.0,provenance=_p("sentinel")),
        ),
        operating_speed_rpm=1800.0,
        motor_station=0,
        driven_equipment_station=1,
        coupling_connection=0,
        driven_equipment="analytic sentinel",
        authority="closed-form two-inertia model",
    )


def _three_inertia():
    return API541TorsionalModel(
        stations=(
            TorsionalStation("motor",8.0,_p("drawing")),
            TorsionalStation("coupling",1.5,_p("vendor")),
            TorsionalStation("compressor",14.0,_p("vendor")),
        ),
        connections=(
            TorsionalConnection(0,1,2.4e6,90.0,"motor shaft",_p("calc")),
            TorsionalConnection(1,2,9.0e5,45.0,"coupling",_p("vendor")),
        ),
        excitations=(
            TorsionalExcitation(0,1200.0,order=2.0,provenance=_p("EM")),
        ),
        operating_speed_rpm=1800.0,
        motor_station=0,
        driven_equipment_station=2,
        coupling_connection=1,
        driven_equipment="compressor",
        authority="engineering train dataset",
    )


def test_i18_two_inertia_closed_form_frequency_and_matrices():
    r=run_api541_torsional_modes(_two_inertia())
    np.testing.assert_array_equal(r.M,np.diag([2.0,3.0]))
    np.testing.assert_array_equal(r.C,np.zeros((2,2)))
    np.testing.assert_array_equal(r.K,np.array([[120.0,-120.0],[-120.0,120.0]]))
    assert r.frequency_rad_s[0]==pytest.approx(0.0,abs=1e-7)
    assert r.frequency_rad_s[1]==pytest.approx(10.0,rel=1e-11,abs=1e-11)
    assert r.frequency_hz[1]==pytest.approx(10.0/(2*np.pi),rel=1e-11)
    assert r.metadata["status"]=="PASS_I18_NATIVE_TORSIONAL_MODAL"
    assert r.metadata["rigid_body_mode_retained"] is True
    assert r.metadata["forced_response_qualified"] is False


def test_i18_three_inertia_native_modes_match_independent_generalized_eigenproblem():
    r=run_api541_torsional_modes(_three_inertia())
    expected=np.linalg.eigvals(np.linalg.solve(r.M,r.K))
    expected=np.sqrt(np.clip(expected.real,0.0,None))
    expected=np.sort(expected)
    np.testing.assert_allclose(r.frequency_rad_s,expected,rtol=2e-10,atol=2e-8)
    np.testing.assert_allclose(r.M,r.M.T,rtol=0,atol=0)
    np.testing.assert_allclose(r.K,r.K.T,rtol=0,atol=0)
    np.testing.assert_allclose(r.C,r.C.T,rtol=0,atol=0)


def test_i18_modes_are_mass_orthogonal_for_distinct_free_modes():
    r=run_api541_torsional_modes(_three_inertia())
    gram=r.modes.T@r.M@r.modes
    scale=max(1.0,float(np.max(np.abs(np.diag(gram)))))
    off=gram-np.diag(np.diag(gram))
    assert np.max(np.abs(off)) <= 1e-9*scale


def test_i18_connection_damping_assembles_expected_laplacian():
    r=run_api541_torsional_modes(_three_inertia())
    expected=np.array([
        [90.0,-90.0,0.0],
        [-90.0,135.0,-45.0],
        [0.0,-45.0,45.0],
    ])
    np.testing.assert_array_equal(r.C,expected)
