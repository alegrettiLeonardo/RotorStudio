from pathlib import Path
import json
import numpy as np
import pytest

from drm_core import (
    Bearing,CoefficientBearing,Disk,Node,RotorModel,ShaftElement,run_clearance
)
from drm_core.solver.ffi import SolverLibraryError

ROOT=Path(__file__).resolve().parents[2]
GOLD=ROOT/"validation"/"ross_parity"/"clearance"

TOL={
    "speed":dict(rtol=0.0,atol=2e-12),
    "unbalance":dict(rtol=2e-9,atol=2e-13),
    "response":dict(rtol=5e-7,atol=5e-11),
    "scalar":dict(rtol=5e-7,atol=5e-11),
    "scale":dict(rtol=5e-7,atol=5e-9),
}


def golden(name):
    return json.loads((GOLD/f"{name}.json").read_text())


def standard_model(*,advanced=()):
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[ShaftElement(2,i+1,i+2,.05,0.,7810.,211e9,81.2e9) for i in range(6)]
    disks=[Disk.geometric(3,7810.,.07,.28,.05),Disk.geometric(5,7810.,.07,.28,.05)]
    bearings=[] if advanced else [
        Bearing(5,1,(1e6,0.,0.,.8e6,1e3,0.,0.,1e3)),
        Bearing(5,7,(1e6,0.,0.,.8e6,1e3,0.,0.,1e3)),
    ]
    return RotorModel(nodes,shafts,disks,bearings,advanced_bearings=list(advanced))


def map2d_model():
    sp=(0.,300.,600.,900.,1200.);fr=sp
    gx=(
        (.75e6,.78e6,.82e6,.86e6,.90e6),
        (.88e6,.92e6,.97e6,1.02e6,1.08e6),
        (1.02e6,1.07e6,1.13e6,1.20e6,1.28e6),
        (1.18e6,1.24e6,1.31e6,1.39e6,1.48e6),
        (1.36e6,1.43e6,1.51e6,1.60e6,1.70e6),
    )
    gy=tuple(tuple(.83*x+8e4 for x in row) for row in gx)
    gc=(
        (1150.,1120.,1090.,1060.,1030.),
        (1100.,1070.,1040.,1010.,980.),
        (1050.,1020.,990.,960.,930.),
        (1000.,970.,940.,910.,880.),
        (950.,920.,890.,860.,830.),
    )
    scale=lambda a,f:tuple(tuple(f*x for x in row) for row in a)
    bearings=[
        CoefficientBearing(1,gx,gc,gy,scale(gc,.92),speed_rad_s=sp,frequency_rad_s=fr),
        CoefficientBearing(7,scale(gx,1.03),scale(gc,.97),scale(gy,1.02),scale(gc,.95),
                           speed_rad_s=sp,frequency_rad_s=fr),
    ]
    return standard_model(advanced=bearings)


def args_for(name):
    g=golden(name);i=g["input"]
    kwargs=dict(
        speed_range_rad_s=i["speed_range_rad_s"],
        minimum_allowable_speed_rad_s=i["minimum_allowable_speed_rad_s"],
        maximum_continuous_speed_rad_s=i["maximum_continuous_speed_rad_s"],
        probe_nodes=i["probe_nodes_one_based"],
        probe_angles_rad=i["probe_angles_rad"],
        clearance_nodes=i["clearance_nodes_one_based"],
        radial_clearance_m=i["radial_clearance_m"],
        probe_tags=["DE-45","NDE-45"],
        clearance_tags=i["clearance_tags"],
        mode=i["mode"],
        scale_factor_cap=i["scale_factor_cap"],
        num_modes=i["num_modes"],
    )
    e=i["explicit_unbalance"]
    if e is not None:
        kwargs.update(
            unbalance_nodes=[int(n)+1 for n in e["node"]],
            unbalance_magnitude_kg_m=e["magnitude"],
            unbalance_phase_rad=e["phase"],
        )
    return g,kwargs


CASES=[
    "baseline_mode0","conical_mode1","high_speed_limit","cap_6",
    "operating_speed_insertion","explicit_20_gmm","explicit_80_gmm","map_2d",
]


@pytest.mark.parametrize("name",CASES)
def test_clearance_frozen_ross_4dof_parity(name):
    g,kwargs=args_for(name)
    r=run_clearance(map2d_model() if name=="map_2d" else standard_model(),**kwargs)
    ref=g["ross_adapted_4dof"]

    np.testing.assert_allclose(r.speed_range_rad_s,ref["speed_range"],**TOL["speed"])
    np.testing.assert_array_equal(r.unbalance_nodes-1,np.asarray(ref["unbalance_node"],int))
    np.testing.assert_allclose(r.unbalance_magnitude_kg_m,ref["unbalance_magnitude"],**TOL["unbalance"])

    # Global modal phase is arbitrary for symmetric conical placement. Relative
    # phase is observable and is what drives the response.
    got=np.mod(r.unbalance_phase_rad-r.unbalance_phase_rad[0],2*np.pi)
    rr=np.asarray(ref["unbalance_phase"],float)
    expected=np.mod(rr-rr[0],2*np.pi)
    np.testing.assert_allclose(got,expected,rtol=0,atol=2e-10)

    np.testing.assert_array_equal(r.probe_nodes-1,np.asarray(ref["probe_nodes"],int))
    np.testing.assert_allclose(r.probe_angles_rad,ref["probe_angles"],rtol=0,atol=2e-15)
    np.testing.assert_allclose(r.probe_response_m_pp,ref["probe_response"],**TOL["response"])
    np.testing.assert_allclose(r.vibration_limit_m_pp,ref["vibration_limit"],rtol=2e-12,atol=2e-15)
    np.testing.assert_allclose(r.max_probe_amplitude_m_pp,ref["max_probe_amplitude"],**TOL["scalar"])
    np.testing.assert_allclose(r.scale_factor,ref["scale_factor"],**TOL["scale"])

    np.testing.assert_array_equal(r.clearance_nodes-1,np.asarray(ref["clearance_nodes"],int))
    np.testing.assert_allclose(r.clearance_positions_m,ref["clearance_positions"],rtol=0,atol=2e-15)
    np.testing.assert_allclose(r.diametral_clearance_m,ref["diametral_clearance"],rtol=2e-12,atol=2e-15)
    np.testing.assert_allclose(r.clearance_limit_m,ref["clearance_limit"],rtol=2e-12,atol=2e-15)
    np.testing.assert_allclose(r.clearance_response_m_pp,ref["clearance_response"],**TOL["response"])
    np.testing.assert_allclose(r.max_clearance_response_m_pp,ref["max_clearance_response"],**TOL["response"])
    np.testing.assert_allclose(r.speed_at_max_response_rad_s,ref["speed_at_max_response"],**TOL["speed"])
    np.testing.assert_array_equal(r.passed,np.asarray(ref["passed"],bool))

    if ref["mode"] is None:
        assert r.mode is None and r.mode_index is None and r.mode_frequency_rad_s is None
    else:
        assert r.mode==ref["mode"] and r.mode_index==ref["mode_index"]
        np.testing.assert_allclose(r.mode_frequency_rad_s,ref["mode_frequency"],rtol=3e-8,atol=3e-7)


def test_speed_union_and_explicit_unbalance_scale_invariance():
    g20,k20=args_for("explicit_20_gmm")
    g80,k80=args_for("explicit_80_gmm")
    r20=run_clearance(standard_model(),**k20)
    r80=run_clearance(standard_model(),**k80)

    np.testing.assert_allclose(
        r80.max_probe_amplitude_m_pp,
        4*r20.max_probe_amplitude_m_pp,
        rtol=3e-8,atol=5e-12,
    )
    np.testing.assert_allclose(r80.scale_factor,r20.scale_factor/4,rtol=3e-8,atol=5e-10)
    np.testing.assert_allclose(
        r80.clearance_response_m_pp,r20.clearance_response_m_pp,
        rtol=3e-8,atol=5e-12,
    )

    gi,ki=args_for("operating_speed_insertion")
    ri=run_clearance(standard_model(),**ki)
    assert len(ri.speed_range_rad_s)==13
    assert ki["minimum_allowable_speed_rad_s"] in ri.speed_range_rad_s
    assert ki["maximum_continuous_speed_rad_s"] in ri.speed_range_rad_s


def test_active_scale_factor_cap_semantics():
    _,kwargs=args_for("baseline_mode0")
    uncapped=run_clearance(standard_model(),**kwargs)
    kwargs["scale_factor_cap"]=0.5*uncapped.scale_factor
    capped=run_clearance(standard_model(),**kwargs)
    np.testing.assert_allclose(capped.probe_response_m_pp,uncapped.probe_response_m_pp,rtol=0,atol=0)
    np.testing.assert_allclose(capped.scale_factor,.5*uncapped.scale_factor,rtol=2e-12)
    np.testing.assert_allclose(capped.clearance_response_m_pp,.5*uncapped.clearance_response_m_pp,rtol=2e-10,atol=2e-13)


def test_vibration_limit_formula_and_strict_clearance_semantics():
    _,kwargs=args_for("high_speed_limit")
    r=run_clearance(standard_model(),**kwargs)
    rpm=r.maximum_continuous_speed_rad_s*60/(2*np.pi)
    expected=min(25.4,25.4*np.sqrt(12000/rpm))*1e-6
    np.testing.assert_allclose(r.vibration_limit_m_pp,expected,rtol=2e-12,atol=2e-15)
    np.testing.assert_array_equal(r.passed,r.max_clearance_response_m_pp<r.clearance_limit_m)


def test_clearance_fail_closed_inputs():
    _,kwargs=args_for("baseline_mode0")
    m=standard_model()
    bad=dict(kwargs);bad["probe_nodes"]=[]
    with pytest.raises(ValueError,match="probe_nodes"):
        run_clearance(m,**bad)
    bad=dict(kwargs);bad["minimum_allowable_speed_rad_s"]=1000.;bad["maximum_continuous_speed_rad_s"]=900.
    with pytest.raises(ValueError,match="minimum_allowable"):
        run_clearance(m,**bad)
    bad=dict(kwargs);bad["radial_clearance_m"]=[0.,1e-4,1e-4]
    with pytest.raises(ValueError,match="clearances"):
        run_clearance(m,**bad)
    bad=dict(kwargs);bad["unbalance_nodes"]=[4]
    with pytest.raises(ValueError,match="required"):
        run_clearance(m,**bad)
