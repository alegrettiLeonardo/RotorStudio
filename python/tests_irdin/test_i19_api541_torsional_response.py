from __future__ import annotations

import math
import numpy as np
import pytest

from drm_core.analysis.api541_torsional_contract import (
    API541TorsionalModel,
    TorsionalConnection,
    TorsionalExcitation,
    TorsionalStation,
)
from drm_core.analysis.api541_torsional_response import run_api541_torsional_response


def _p(source):
    return {"source": source}


def _model():
    omega=5.0
    hz=omega/(2.0*math.pi)
    return API541TorsionalModel(
        stations=(
            TorsionalStation("J1",2.0,_p("analytic")),
            TorsionalStation("J2",3.0,_p("analytic")),
        ),
        connections=(
            TorsionalConnection(0,1,120.0,0.0,"K12",_p("analytic")),
        ),
        excitations=(
            TorsionalExcitation(
                0,1.0,phase_rad=0.0,frequency_hz=hz,
                name="positive torque",provenance=_p("analytic"),
            ),
            TorsionalExcitation(
                1,-1.0,phase_rad=0.0,frequency_hz=hz,
                name="reaction torque",provenance=_p("analytic"),
            ),
        ),
        operating_speed_rpm=1800.0,
        motor_station=0,
        driven_equipment_station=1,
        coupling_connection=0,
        driven_equipment="analytic load",
        authority="closed-form two-inertia response",
    )


def test_i19_closed_form_two_inertia_response_and_connection_torque():
    r=run_api541_torsional_response(_model())
    assert r.excitation_frequency_rad_s.tolist()==pytest.approx([5.0])
    np.testing.assert_allclose(r.torque_input[:,0],[1.0,-1.0],rtol=0,atol=1e-15)
    np.testing.assert_allclose(
        r.angle_response_rad[:,0],
        np.array([1.0/150.0,-1.0/225.0]),
        rtol=1e-11,atol=1e-13,
    )
    assert r.connection_torque_nm[0,0].real==pytest.approx(4.0/3.0,rel=1e-11)
    assert r.connection_torque_nm[0,0].imag==pytest.approx(0.0,abs=1e-13)
    assert r.metadata["status"]=="PASS_I19_NATIVE_TORSIONAL_HARMONIC_RESPONSE"
    assert r.metadata["separation_acceptance_evaluated"] is False


def test_i19_separation_is_reported_without_invented_acceptance_threshold():
    r=run_api541_torsional_response(_model())
    assert len(r.separation_checks)==1
    check=r.separation_checks[0]
    assert check.natural_frequency_rad_s==pytest.approx(10.0,rel=1e-11)
    assert check.excitation_frequency_rad_s==pytest.approx(5.0,rel=1e-12)
    assert check.separation_fraction==pytest.approx(1.0,rel=1e-11)
    assert check.required_fraction is None
    assert check.passed is None


def test_i19_project_supplied_separation_criterion_is_evaluated_explicitly():
    passed=run_api541_torsional_response(_model(),required_separation_fraction=0.15)
    check=passed.separation_checks[0]
    assert check.required_fraction==pytest.approx(0.15)
    assert check.passed is True

    failed=run_api541_torsional_response(_model(),required_separation_fraction=1.1)
    assert failed.separation_checks[0].passed is False


def test_i19_grouping_sums_equal_frequency_complex_torques():
    m=_model()
    result=run_api541_torsional_response(m)
    assert result.torque_input.shape==(2,1)
    assert result.excitation_frequency_rad_s.shape==(1,)


def test_i19_rejects_invalid_separation_criterion():
    with pytest.raises(ValueError,match="required_separation_fraction"):
        run_api541_torsional_response(_model(),required_separation_fraction=-0.1)
