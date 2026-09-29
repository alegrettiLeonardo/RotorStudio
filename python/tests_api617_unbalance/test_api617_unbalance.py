from pathlib import Path
import json
import numpy as np
import pytest

from drm_core import (
    Bearing,CoefficientBearing,Disk,Node,RotorModel,ShaftElement,
    run_api617_unbalance,
)
from drm_core.solver.ffi import SolverLibraryError

ROOT=Path(__file__).resolve().parents[2]
GOLD=ROOT/"validation"/"ross_parity"/"api617_unbalance"


def golden(name):
    return json.loads((GOLD/f"{name}.json").read_text())


def standard_model(*,advanced=()):
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[
        ShaftElement(2,i+1,i+2,.05,0.,7810.,211e9,81.2e9)
        for i in range(6)
    ]
    disks=[
        Disk.geometric(3,7810.,.07,.28,.05),
        Disk.geometric(5,7810.,.06,.24,.05),
    ]
    bearings=[] if advanced else [
        Bearing(5,1,(1e6,0.,0.,1e6,1e3,0.,0.,1e3)),
        Bearing(5,7,(1e6,0.,0.,1e6,1e3,0.,0.,1e3)),
    ]
    return RotorModel(
        nodes,shafts,disks,bearings,advanced_bearings=list(advanced)
    )


def overhung_model():
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[
        ShaftElement(2,i+1,i+2,.05,0.,7810.,211e9,81.2e9)
        for i in range(6)
    ]
    disks=[Disk.geometric(7,7810.,.07,.28,.05)]
    bearings=[
        Bearing(5,1,(1e7,0.,0.,1e7,1e3,0.,0.,1e3)),
        Bearing(5,3,(1e7,0.,0.,1e7,1e3,0.,0.,1e3)),
    ]
    return RotorModel(nodes,shafts,disks,bearings)


def speed_dependent_model():
    sp=(0.,300.,600.,900.,1200.)
    kx=(.8e6,.95e6,1.12e6,1.32e6,1.55e6)
    ky=(.70e6,.82e6,.96e6,1.12e6,1.30e6)
    cx=(1100.,1050.,1000.,950.,900.)
    cy=(1000.,960.,920.,880.,840.)
    a=[
        CoefficientBearing(1,kx,cx,ky,cy,speed_rad_s=sp),
        CoefficientBearing(
            7,tuple(1.04*x for x in kx),tuple(.98*x for x in cx),
            tuple(1.02*x for x in ky),tuple(1.01*x for x in cy),
            speed_rad_s=sp,
        ),
    ]
    return standard_model(advanced=a)


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
    a=[
        CoefficientBearing(1,gx,gc,gy,scale(gc,.92),speed_rad_s=sp,frequency_rad_s=fr),
        CoefficientBearing(7,scale(gx,1.03),scale(gc,.97),scale(gy,1.02),scale(gc,.95),
                           speed_rad_s=sp,frequency_rad_s=fr),
    ]
    return standard_model(advanced=a)


def model_for(name):
    if name=="overhung_6000rpm":return overhung_model()
    if name=="speed_dependent_9000rpm":return speed_dependent_model()
    if name=="map_2d_9000rpm":return map2d_model()
    return standard_model()


CASES=[
    "first_mode_9000rpm",
    "conical_mode_9000rpm",
    "below_boundary_24999rpm",
    "high_speed_25000rpm",
    "high_speed_30000rpm",
    "overhung_6000rpm",
    "speed_dependent_9000rpm",
    "map_2d_9000rpm",
]


@pytest.mark.parametrize("name",CASES)
def test_api617_unbalance_frozen_ross_4dof_parity(name):
    g=golden(name);inp=g["input"];ref=g["ross_adapted_4dof"]
    r=run_api617_unbalance(
        model_for(name),
        mode=inp["mode"],
        maximum_continuous_speed_rad_s=inp["maximum_continuous_speed_rad_s"],
        num_modes=inp["num_modes"],
    )

    np.testing.assert_array_equal(r.nodes-1,np.asarray(ref["result"]["node"],dtype=int))
    np.testing.assert_allclose(
        r.unbalance_magnitude_kg_m,ref["result"]["unbalance_magnitude"],
        rtol=2e-9,atol=2e-13,
    )
    np.testing.assert_allclose(
        r.static_load_kg,ref["result"]["static_load"],rtol=2e-9,atol=2e-9
    )
    assert r.mode_index==ref["result"]["mode_index"]
    np.testing.assert_allclose(
        r.mode_frequency_rad_s,ref["result"]["mode_frequency"],rtol=3e-8,atol=3e-7
    )
    np.testing.assert_allclose(
        r.whirl_ratio,np.asarray(ref["modal"]["whirl_ratio"])[:len(r.whirl_ratio)],
        rtol=3e-7,atol=3e-8,
    )

    got_major=np.asarray(r.mode_major_axis,float)
    ref_major=np.asarray(ref["modal"]["amplitude"],float)
    got_major/=got_major.max();ref_major/=ref_major.max()
    np.testing.assert_allclose(got_major,ref_major,rtol=4e-7,atol=4e-8)

    # Phase is meaningful only relatively. Symmetric conical antinodes have an
    # exactly equivalent global pi rotation when the numerically tied reference
    # end swaps between ARPACK and DGEEV.
    got_phase=np.mod(r.unbalance_phase_rad-r.unbalance_phase_rad[0],2*np.pi)
    ref_phase=np.asarray(ref["result"]["unbalance_phase"],float)
    ref_phase=np.mod(ref_phase-ref_phase[0],2*np.pi)
    np.testing.assert_allclose(got_phase,ref_phase,rtol=0,atol=2e-10)


def test_api617_boundary_switch_is_exactly_25000_rpm():
    lo=golden("below_boundary_24999rpm")
    hi=golden("high_speed_25000rpm")
    rlo=run_api617_unbalance(
        standard_model(),lo["input"]["mode"],lo["input"]["maximum_continuous_speed_rad_s"],12
    )
    rhi=run_api617_unbalance(
        standard_model(),hi["input"]["mode"],hi["input"]["maximum_continuous_speed_rad_s"],12
    )
    np.testing.assert_allclose(rlo.unbalance_magnitude_kg_m,lo["ross_adapted_4dof"]["result"]["unbalance_magnitude"],rtol=2e-9)
    np.testing.assert_allclose(rhi.unbalance_magnitude_kg_m,hi["ross_adapted_4dof"]["result"]["unbalance_magnitude"],rtol=2e-9)
    assert not np.isclose(rlo.unbalance_magnitude_kg_m[0],rhi.unbalance_magnitude_kg_m[0],rtol=1e-3)


def test_api617_mode_not_available_and_scope_fail_closed():
    g=golden("mode_not_available")
    with pytest.raises(SolverLibraryError,match="unavailable"):
        run_api617_unbalance(standard_model(),20,9000*2*np.pi/60,12)

    with pytest.raises(ValueError,match="expected finite > 0"):
        run_api617_unbalance(standard_model(),0,0.0,12)
    with pytest.raises(ValueError,match="forward-mode index"):
        run_api617_unbalance(standard_model(),-1,100.0,12)
    with pytest.raises(ValueError,match="even integer"):
        run_api617_unbalance(standard_model(),0,100.0,11)

    m=standard_model()
    bad=RotorModel(m.nodes,m.shafts,m.disks,[Bearing(1,1,())])
    with pytest.raises(ValueError,match="type 3/5"):
        run_api617_unbalance(bad,0,100.0,12)
