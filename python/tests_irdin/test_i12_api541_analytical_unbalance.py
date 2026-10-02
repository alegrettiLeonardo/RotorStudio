from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from drm_core import RotorModel,Node,ShaftElement,Disk,load_irdin_project
from drm_core.domain.model import BearingSupport
from drm_core.analysis.irdin_lateral import run_irdin_modal
from drm_core.analysis.api541_lateral import API541CriticalSpeed,RPM_TO_RAD_S
from drm_core.analysis.api541_analytical_unbalance import (
    api541_minimum_analytical_unbalance_g_mm,
    api541_vibration_limit_pp_m,
    journal_static_loads_kg,
    analytical_unbalance_case,
)
from validation.irdin.i0_authority import CASE_PATH


def test_i12_api541_si_formulae_are_exact():
    assert api541_minimum_analytical_unbalance_g_mm(1000.0,1800.0)==pytest.approx(
        2.0*6350.0*1000.0/1800.0,rel=0,abs=0
    )
    assert api541_vibration_limit_pp_m(1800.0)==pytest.approx(
        25.4*math.sqrt(12000.0/1800.0)*1e-6,rel=0,abs=0
    )


def test_i12_two_support_static_equilibrium_is_symmetric_for_symmetric_rotor():
    model=RotorModel(
        nodes=[Node(1,0.0),Node(2,0.5),Node(3,1.0)],
        shafts=[
            ShaftElement(2,1,2,0.05,0.0,7800.0,2e11,8e10),
            ShaftElement(2,2,3,0.05,0.0,7800.0,2e11,8e10),
        ],
        disks=[Disk.inertial(2,100.0,1.0,2.0)],
        supports=[
            BearingSupport(1,1,10.0,1e8,0,0,1e8,0,0,0,0),
            BearingSupport(2,3,10.0,1e8,0,0,1e8,0,0,0,0),
        ],
    )
    project=type("P",(),{"model":model})()
    loads=journal_static_loads_kg(project)
    assert len(loads)==2
    assert loads[0].static_load_kg==pytest.approx(loads[1].static_load_kg,rel=2e-15)


def test_i12_st41_journal_loads_are_positive_and_close_mass_equilibrium():
    p=load_irdin_project(CASE_PATH)
    loads=journal_static_loads_kg(p)
    assert len(loads)==2
    assert all(x.static_load_kg>0.0 for x in loads)
    assert loads[0].z_m==pytest.approx(0.550)
    assert loads[1].z_m==pytest.approx(3.977)
    # At minimum, the two reactions must carry all qualified imported mass;
    # shaft self-weight adds to that total.
    assert sum(x.static_load_kg for x in loads)>10680.0


def test_i12_st41_native_pipeline_scales_to_vibration_limit_without_mutation():
    p=load_irdin_project(CASE_PATH)
    speed=1800.0*RPM_TO_RAD_S
    modal=run_irdin_modal(p,speed)
    eig=np.asarray(modal.eigenvalues,dtype=np.complex128)
    positive=np.flatnonzero(eig.imag>0)
    assert positive.size>0
    j=int(positive[np.argmin(np.abs(eig[positive].imag))])
    lam=eig[j]
    critical=API541CriticalSpeed(
        branch=1,
        excitation_order=1.0,
        speed_rad_s=speed,
        speed_rpm=1800.0,
        modal_frequency_rad_s=float(abs(lam.imag)),
        damping_ratio=float(-lam.real/abs(lam)) if abs(lam)>0 else 0.0,
        mac=1.0,
    )
    before_forces=tuple(p.model.forces)
    before_supports=tuple(p.model.supports)
    result=analytical_unbalance_case(
        p,critical,
        operating_speed_rpm=1800.0,
        mode_override="TRANSLATORY",
    )
    assert result.metadata["status"]=="PASS_I12_API541_ANALYTICAL_UNBALANCE"
    assert result.mode_kind=="TRANSLATORY"
    assert result.scale_factor>=1.0
    assert result.max_probe_pp_m>=result.vibration_limit_pp_m*(1.0-1e-12)
    assert len(result.planes)==1
    plane=result.planes[0]
    assert plane.applied_unbalance_g_mm>=plane.minimum_unbalance_g_mm
    assert np.isfinite(result.probe_response.real).all()
    assert np.isfinite(result.probe_response.imag).all()
    assert tuple(p.model.forces)==before_forces
    assert tuple(p.model.supports)==before_supports


def test_i12_rejects_nonpositive_inputs():
    with pytest.raises(ValueError):
        api541_minimum_analytical_unbalance_g_mm(0.0,1800.0)
    with pytest.raises(ValueError):
        api541_vibration_limit_pp_m(0.0)
