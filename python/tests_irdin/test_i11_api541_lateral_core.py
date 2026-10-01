from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pytest

from drm_core import load_irdin_project
from drm_core.analysis.api541_lateral import (
    API541ModalTracking,
    API541CriticalSpeed,
    critical_crossings,
    separation_checks,
    run_api541_lateral_core,
    RPM_TO_RAD_S,
)
from validation.irdin.i0_authority import CASE_PATH


def test_i11_linear_crossing_interpolation_is_exact():
    speed=np.array([0.0,50.0,100.0,150.0])
    tracking=API541ModalTracking(
        speed_rad_s=speed,
        frequency_rad_s=np.array([[100.0,100.0,100.0,100.0]]),
        damping_ratio=np.array([[0.01,0.02,0.03,0.04]]),
        mac_to_previous=np.ones((1,4)),
    )
    out=critical_crossings(tracking,excitation_orders=(1.0,))
    assert len(out)==1
    assert out[0].branch==1
    assert out[0].speed_rad_s==pytest.approx(100.0,rel=0,abs=0)
    assert out[0].modal_frequency_rad_s==pytest.approx(100.0,rel=0,abs=0)
    assert out[0].damping_ratio==pytest.approx(0.03,rel=0,abs=0)


def test_i11_fixed_speed_separation_uses_declared_fraction():
    c1=API541CriticalSpeed(1,1.0,80.0,80.0/RPM_TO_RAD_S,80.0,0.02,1.0)
    c2=API541CriticalSpeed(2,1.0,90.0,90.0/RPM_TO_RAD_S,90.0,0.02,1.0)
    checks=separation_checks(
        (c1,c2),required_fraction=0.15,operating_speed_rad_s=100.0
    )
    assert checks[0].separation_fraction==pytest.approx(0.20)
    assert checks[0].passed is True
    assert checks[1].separation_fraction==pytest.approx(0.10)
    assert checks[1].passed is False


def test_i11_speed_range_inside_is_zero_margin_and_fails():
    c=API541CriticalSpeed(1,1.0,105.0,105.0/RPM_TO_RAD_S,105.0,0.01,1.0)
    check=separation_checks(
        (c,),required_fraction=0.15,operating_range_rad_s=(90.0,110.0)
    )[0]
    assert check.reference=="SPEED_RANGE"
    assert check.separation_fraction==0.0
    assert check.passed is False


def test_i11_st41_core_executes_native_modal_response_and_support_sensitivity():
    p=load_irdin_project(CASE_PATH)
    camp=np.array([0.0,750.0,1500.0,2250.0,3000.0])*RPM_TO_RAD_S
    rsp=np.array([500.0,1800.0,2700.0])*RPM_TO_RAD_S
    result=run_api541_lateral_core(
        p,
        campbell_speeds_rad_s=camp,
        response_speeds_rad_s=rsp,
        mode_count=4,
        excitation_orders=(1.0,),
        required_separation_fraction=0.15,
        operating_speed_rad_s=1800.0*RPM_TO_RAD_S,
        support_stiffness_factors=(0.75,1.0,1.25),
    )
    assert result.metadata["status"]=="PASS_I11_API541_LATERAL_CORE"
    assert result.metadata["api541_analytical_unbalance_qualified"] is False
    assert result.metadata["full_api541_compliance_claim"] is False
    assert result.tracking.frequency_rad_s.shape==(4,5)
    assert result.tracking.damping_ratio.shape==(4,5)
    assert result.tracking.mac_to_previous.shape==(4,5)
    assert np.isfinite(result.tracking.frequency_rad_s).all()
    assert np.isfinite(result.tracking.damping_ratio).all()
    assert np.all((result.tracking.mac_to_previous>=0.0)&(result.tracking.mac_to_previous<=1.0))
    assert len(result.legacy_probe_peaks)==4
    assert all(x.amplitude_m>=0.0 and math.isfinite(x.phase_rad) for x in result.legacy_probe_peaks)
    assert [x.stiffness_factor for x in result.support_sensitivity]==[0.75,1.0,1.25]
    # Sensitivity is temporary: persisted source supports must remain unchanged.
    assert all(s.kxx_n_m==pytest.approx(2.73e9) for s in p.model.supports)
    assert all(s.kyy_n_m==pytest.approx(3.41e9) for s in p.model.supports)


def test_i11_requires_one_operating_reference_only():
    with pytest.raises(ValueError,match="exactly one"):
        separation_checks((),required_fraction=0.15)
    with pytest.raises(ValueError,match="exactly one"):
        separation_checks(
            (),required_fraction=0.15,
            operating_speed_rad_s=100.0,
            operating_range_rad_s=(90.0,110.0),
        )
