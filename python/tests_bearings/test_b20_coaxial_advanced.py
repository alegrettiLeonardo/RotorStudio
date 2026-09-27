from __future__ import annotations

import copy
import numpy as np

from drm_core import (
    Bearing, CoefficientBearing, Disk, Force, Node, RotorDefinition, RotorModel,
    ShaftElement,
)
from drm_core.analysis.coaxial import run_coaxial_frequency_response, run_coaxial_modal
from drm_core.solver.bearings_backend import AdvancedBearingBackend


def _advanced(node=1):
    speed=(80.0,200.0,340.0)
    return CoefficientBearing(
        node=node,speed_rad_s=speed,interpolation="linear",
        kxx=tuple(5.5e6+1000*w for w in speed),
        kxy=tuple(2.0e4+30*w for w in speed),
        kyx=tuple(-1.5e4+20*w for w in speed),
        kyy=tuple(5.8e6+900*w for w in speed),
        cxx=tuple(90.0+.1*w for w in speed),
        cxy=tuple(4.0+.01*w for w in speed),
        cyx=tuple(-3.0+.005*w for w in speed),
        cyy=tuple(95.0+.08*w for w in speed),
        mxx=tuple(1.2+.001*w for w in speed),
        mxy=tuple(.06+.0001*w for w in speed),
        myx=tuple(-.03+.00005*w for w in speed),
        myy=tuple(1.4+.0008*w for w in speed),
    )


def _coax(advanced=None, legacy=None):
    E=2.05e11;G=7.9e10;rho=7800.
    nodes=[Node(1,0),Node(2,.3),Node(3,.6),Node(4,0),Node(5,.3),Node(6,.6)]
    shafts=[
        ShaftElement(2,1,2,.045,.005,rho,E,G,1e-5),
        ShaftElement(2,2,3,.045,.005,rho,E,G,1e-5),
        ShaftElement(2,4,5,.04,.004,rho,E,G,1.2e-5),
        ShaftElement(2,5,6,.04,.004,rho,E,G,1.2e-5),
    ]
    disks=[Disk.geometric(2,rho,.04,.20,.045),Disk.geometric(5,rho,.035,.18,.04)]
    bearings=[
        Bearing(3,3,(6e6,6e6,80.,80.)),
        Bearing(3,4,(5e6,5e6,70.,70.)),
        Bearing(3,6,(5e6,5e6,70.,70.)),
        Bearing(20,2,(5,1.2e6,1.0e6,150.,140.)),
    ]
    if legacy is not None:
        bearings.append(legacy)
    return RotorModel(
        nodes,shafts,disks,bearings,[Force(1,(5,1.3e-4,.25))],
        rotors=[RotorDefinition(1,3,1.0),RotorDefinition(4,6,-0.7)],
        advanced_bearings=[] if advanced is None else [advanced],
    )


def _legacy_at(bearing,speed):
    return AdvancedBearingBackend().as_legacy_bearing(bearing,speed,speed)


def _match_error(a,b):
    remaining=list(np.asarray(b,dtype=complex));errors=[]
    for value in np.asarray(a,dtype=complex):
        idx=min(range(len(remaining)),key=lambda k:abs(remaining[k]-value))
        ref=remaining.pop(idx)
        errors.append(abs(value-ref)/max(1.0,abs(ref)))
    return max(errors)


def test_b20_coaxial_modal_matches_explicit_operating_point_type9():
    bearing=_advanced()
    speed=210.0
    advanced=run_coaxial_modal(_coax(advanced=bearing),speed)
    oracle=run_coaxial_modal(_coax(legacy=_legacy_at(bearing,speed)),speed)
    assert _match_error(advanced.eigenvalues,oracle.eigenvalues)<5e-10
    # Modal vectors are defined up to complex scale/phase; compare eigenvalues
    # here while the existing coaxial source-oracle suite continues to gate
    # the native relative-speed equations.


def test_b20_coaxial_frf_evaluates_advanced_bearing_at_each_reference_speed():
    bearing=_advanced()
    speeds=np.array([90.0,190.0,320.0])
    actual=run_coaxial_frequency_response(_coax(advanced=bearing),speeds).response
    for j,speed in enumerate(speeds):
        oracle=run_coaxial_frequency_response(
            _coax(legacy=_legacy_at(bearing,float(speed))),
            np.array([speed]),
        ).response[:,0]
        np.testing.assert_allclose(actual[:,j],oracle,rtol=5e-11,atol=5e-11)


def test_b20_reference_speed_rule_is_not_individual_rotor_spin():
    bearing=_advanced()
    speed=200.0
    ev=AdvancedBearingBackend().evaluate(bearing,speed,speed)
    adapted=_legacy_at(bearing,speed)
    assert adapted.bearing_type==9
    assert adapted.properties[0]==ev.K[0,0]
    # Bearing is on rotor 1 (factor 1.0); the contract is explicitly reference
    # speed. B20 does not multiply the bearing operating point by an arbitrary
    # rotor factor or by the unbalance excitation rotor factor.
