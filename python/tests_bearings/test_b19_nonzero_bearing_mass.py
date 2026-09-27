from __future__ import annotations

import numpy as np
import pytest

from drm_core import Bearing, CoefficientBearing, Force, Node, RotorModel, ShaftElement
from drm_core.analysis.frequency_response import run_frequency_response
from drm_core.analysis.modal import run_modal
from drm_core.analysis.transient import run_runup
from drm_core.solver.bearings_backend import AdvancedBearingBackend
from drm_core.solver.facade import SolverFacade
from drm_core.solver.ffi import SolverLibraryError


def _shaft():
    return ShaftElement(2,1,2,0.05,0.0,7810.0,211e9,81.2e9,0.0,0.0,0.0)


def _bearing(node=1, speed_axis=()):
    if speed_axis:
        s=tuple(float(x) for x in speed_axis)
        return CoefficientBearing(
            node=node,speed_rad_s=s,interpolation="linear",
            kxx=tuple(1.2e6+300*w for w in s),
            kxy=tuple(2.0e4-10*w for w in s),
            kyx=tuple(-1.8e4+12*w for w in s),
            kyy=tuple(1.4e6+250*w for w in s),
            cxx=tuple(180+0.2*w for w in s),
            cxy=tuple(8+0.01*w for w in s),
            cyx=tuple(-6+0.02*w for w in s),
            cyy=tuple(210+0.15*w for w in s),
            mxx=tuple(2.0+0.002*w for w in s),
            mxy=tuple(0.15+0.0002*w for w in s),
            myx=tuple(-0.08+0.0001*w for w in s),
            myy=tuple(2.4+0.0015*w for w in s),
        )
    return CoefficientBearing(
        node=node,
        kxx=1.25e6,kxy=2.1e4,kyx=-1.7e4,kyy=1.45e6,
        cxx=185.0,cxy=7.0,cyx=-5.0,cyy=215.0,
        mxx=2.2,mxy=0.16,myx=-0.07,myy=2.6,
    )


def _base(advanced=None, legacy=None):
    return RotorModel(
        nodes=[Node(1,0.0),Node(2,1.0)],
        shafts=[_shaft()],
        bearings=[
            Bearing(5,2,(1.3e6,0.0,0.0,1.4e6,160.0,0.0,0.0,170.0)),
            *([] if legacy is None else [legacy]),
        ],
        forces=[Force(1,(1,1.0e-4,0.0))],
        advanced_bearings=[] if advanced is None else [advanced],
    )


def _type9_from(bearing, speed):
    ev=AdvancedBearingBackend().evaluate(bearing,speed,speed)
    K,C,M=ev.K,ev.C,ev.M
    return Bearing(9,bearing.node,(
        K[0,0],K[0,1],K[1,0],K[1,1],
        C[0,0],C[0,1],C[1,0],C[1,1],
        M[0,0],M[0,1],M[1,0],M[1,1],
    ))


def _sorted(values):
    a=np.asarray(values,dtype=np.complex128)
    return a[np.lexsort((np.angle(a),np.abs(a)))]


def test_b19_nonzero_mass_uses_additive_type9_without_discarding_cross_coupling():
    b=_bearing()
    adapted=AdvancedBearingBackend().as_legacy_bearing(b,120.0,120.0)
    assert adapted.bearing_type==9
    assert adapted.properties[8:12]==pytest.approx((2.2,0.16,-0.07,2.6))


def test_b19_zero_mass_preserves_b12_type5_bridge():
    b=CoefficientBearing(node=1,kxx=1e6,kyy=1.2e6,cxx=100.0,cyy=120.0)
    adapted=AdvancedBearingBackend().as_legacy_bearing(b,100.0,100.0)
    assert adapted.bearing_type==5
    assert len(adapted.properties)==8


def test_b19_stationary_assembly_modal_and_frf_match_explicit_type9_oracle():
    b=_bearing()
    speed=120.0
    advanced=_base(advanced=b)
    oracle=_base(legacy=_type9_from(b,speed))
    facade=SolverFacade()
    aa=facade.assemble(advanced,speed)
    oo=facade.assemble(oracle,speed)
    for lhs,rhs in zip(aa,oo):
        np.testing.assert_allclose(lhs,rhs,rtol=0.0,atol=2e-12)

    ma=run_modal(advanced,speed,with_eigenvectors=True)
    mo=run_modal(oracle,speed,with_eigenvectors=True)
    np.testing.assert_allclose(_sorted(ma.eigenvalues),_sorted(mo.eigenvalues),rtol=2e-12,atol=2e-8)

    speeds=np.array([speed])
    ra=run_frequency_response(advanced,speeds).response[:,0]
    ro=run_frequency_response(oracle,speeds).response[:,0]
    np.testing.assert_allclose(ra,ro,rtol=2e-12,atol=2e-12)


def test_b19_speed_dependent_mass_is_evaluated_at_operating_point():
    b=_bearing(speed_axis=(80.0,120.0,160.0))
    facade=SolverFacade()
    for speed in (80.0,100.0,160.0):
        advanced=_base(advanced=b)
        oracle=_base(legacy=_type9_from(b,speed))
        for lhs,rhs in zip(facade.assemble(advanced,speed),facade.assemble(oracle,speed)):
            np.testing.assert_allclose(lhs,rhs,rtol=2e-13,atol=2e-10)


def test_b19_b18_runup_still_fails_closed_for_nonzero_mass():
    model=_base(advanced=_bearing(speed_axis=(80.0,120.0,160.0)))
    with pytest.raises(SolverLibraryError,match="nonzero advanced-bearing M"):
        run_runup(model,[10.0,100.0,0.0],[0.0,1.0],nr=0)
