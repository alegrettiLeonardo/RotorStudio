from __future__ import annotations

import copy
import numpy as np
import pytest

from drm_core import AsymmetricShaftElement,Bearing,CoefficientBearing,Disk,Force,Node,RotorModel
from drm_core.analysis.asymmetric import (
    B21_ROTATING_ADVANCED_POLICY,run_asymmetric_frequency_response,run_asymmetric_modal,
)
from drm_core.solver.backend import FortranBackend
from drm_core.solver.bearings_backend import AdvancedBearingBackend
from drm_core.solver.ffi import SolverLibraryError


J=np.array([[0.0,-1.0],[1.0,0.0]])


def _base():
    return RotorModel(
        [Node(1,0.0),Node(2,0.3),Node(3,0.6)],
        [
            AsymmetricShaftElement(12,1,2,1.2e5,1.0e5,.08,.09,12.,.004),
            AsymmetricShaftElement(12,2,3,1.2e5,1.0e5,.08,.09,12.,.004),
        ],
        [Disk.anisotropic(2,8.,.03,.04,.05)],
        [
            Bearing(4,1,(1e6,1e6,2e4,2e4,100.,100.,5.,5.)),
            Bearing(4,3,(1e6,1e6,2e4,2e4,100.,100.,5.,5.)),
        ],
        [Force(1,(2,1e-4,.2)),Force(2,(2,2e-5,-.1))],
    )


def _surface(axis,diag0,diag_s,skew0=0.0,skew_s=0.0):
    diag=tuple(diag0+diag_s*w for w in axis)
    skew=tuple(skew0+skew_s*w for w in axis)
    return diag,skew


def _advanced():
    axis=(80.0,200.0,320.0)
    kd,ks=_surface(axis,1.15e6,120.0,2.0e4,3.0)
    cd,cs=_surface(axis,190.0,.05,7.0,.002)
    md,ms=_surface(axis,11.0,.002,.35,.0001)
    # a*I+b*J => [[a,-b],[b,a]], which is invariant under planar rotation.
    return CoefficientBearing(
        node=2,speed_rad_s=axis,interpolation="linear",
        kxx=kd,kxy=tuple(-v for v in ks),kyx=ks,kyy=kd,
        cxx=cd,cxy=tuple(-v for v in cs),cyx=cs,cyy=cd,
        mxx=md,mxy=tuple(-v for v in ms),myx=ms,myy=md,
        tag="B21 rotation-invariant advanced",
    )


def _embed(global_matrix,node,local):
    ii=np.array([4*node-4,4*node-3])
    global_matrix[np.ix_(ii,ii)]+=local


def _parts(base):
    backend=FortranBackend()
    M,C0,C1,K0,K1,K2=backend.asymmetric_assemble(base)
    Cb,Kb,K1legacy,mask=backend.asymmetric_bearings(base)
    return M,C0,C1,K0,K1,K2,Cb,Kb,K1legacy,mask


def _advanced_terms(ev,node,ndof):
    Mb=np.zeros((ndof,ndof));Cb=np.zeros_like(Mb);C1b=np.zeros_like(Mb)
    Kb=np.zeros_like(Mb);K1b=np.zeros_like(Mb);K2b=np.zeros_like(Mb)
    _embed(Mb,node,ev.M);_embed(Cb,node,ev.C);_embed(C1b,node,2.0*ev.M@J)
    _embed(Kb,node,ev.K);_embed(K1b,node,ev.C@J);_embed(K2b,node,-ev.M)
    return Mb,Cb,C1b,Kb,K1b,K2b


def _match_error(actual,expected):
    remaining=list(expected);errors=[]
    for value in actual:
        j=min(range(len(remaining)),key=lambda k:abs(remaining[k]-value))
        ref=remaining.pop(j);errors.append(abs(value-ref)/max(1.0,abs(ref)))
    return max(errors)


def test_b21_rotating_modal_matches_independent_frame_transform_with_nonzero_M():
    base=_base();adv=_advanced();model=copy.deepcopy(base);model.advanced_bearings=[adv]
    speed=200.0
    actual,_=FortranBackend().asymmetric_modal(model,speed,False)
    M,C0,C1,K0,K1,K2,Cb,Kb,K1legacy,mask=_parts(base)
    ev=AdvancedBearingBackend().evaluate(adv,speed,speed)
    Mb,Cba,C1ba,Kba,K1ba,K2ba=_advanced_terms(ev,adv.node,len(M))
    Mt=M+Mb;Ct=C0+Cb+Cba+speed*(C1+C1ba)
    Kt=K0+Kb+Kba+speed*(K1+K1legacy+K1ba)+speed**2*(K2+K2ba)
    keep=~mask;Mr=Mt[np.ix_(keep,keep)];Cr=Ct[np.ix_(keep,keep)];Kr=Kt[np.ix_(keep,keep)]
    n=len(Mr);A=np.block([[np.zeros((n,n)),np.eye(n)],[-np.linalg.solve(Mr,Kr),-np.linalg.solve(Mr,Cr)]])
    assert _match_error(actual,np.linalg.eigvals(A))<8e-9


def test_b21_vector_semantics_omit_only_legacy_K1b_not_advanced_transform():
    base=_base();adv=_advanced();model=copy.deepcopy(base);model.advanced_bearings=[adv]
    speed=180.0
    actual,_=FortranBackend().asymmetric_modal(model,speed,True)
    M,C0,C1,K0,K1,K2,Cb,Kb,K1legacy,mask=_parts(base)
    ev=AdvancedBearingBackend().evaluate(adv,speed,speed)
    Mb,Cba,C1ba,Kba,K1ba,K2ba=_advanced_terms(ev,adv.node,len(M))
    Mt=M+Mb;Ct=C0+Cb+Cba+speed*(C1+C1ba)
    # Historical chr_asym nargout==2 omits legacy K1b. B21 K1ba is new
    # coordinate-transform physics and must remain.
    Kt=K0+Kb+Kba+speed*(K1+K1ba)+speed**2*(K2+K2ba)
    keep=~mask;Mr=Mt[np.ix_(keep,keep)];Cr=Ct[np.ix_(keep,keep)];Kr=Kt[np.ix_(keep,keep)]
    n=len(Mr);A=np.block([[np.zeros((n,n)),np.eye(n)],[-np.linalg.solve(Mr,Kr),-np.linalg.solve(Mr,Cr)]])
    assert _match_error(actual,np.linalg.eigvals(A))<8e-9


def test_b21_rotating_static_frf_contains_CJ_and_minus_M_omega_squared_terms():
    base=_base();adv=_advanced();model=copy.deepcopy(base);model.advanced_bearings=[adv]
    speeds=np.array([90.0,200.0,300.0]);actual=FortranBackend().asymmetric_frequency_response(model,speeds)
    M,C0,C1,K0,K1,K2,Cb,Kb,K1legacy,mask=_parts(base);keep=~mask
    ub=np.zeros(len(M))
    for f in base.forces:
        node=int(f.values[0]);mag,phase=f.values[1],f.values[2]
        if f.force_type==1:
            ub[4*node-4]+=mag*np.cos(phase);ub[4*node-3]+=mag*np.sin(phase)
        else:
            ub[4*node-2]+=-mag*np.sin(phase);ub[4*node-1]+=mag*np.cos(phase)
    provider=AdvancedBearingBackend()
    for col,w in enumerate(speeds):
        ev=provider.evaluate(adv,float(w),float(w))
        Mb,Cba,C1ba,Kba,K1ba,K2ba=_advanced_terms(ev,adv.node,len(M))
        Kt=K0+Kb+Kba+w*(K1+K1legacy+K1ba)+w*w*(K2+K2ba)
        expected=np.zeros(len(M));expected[keep]=w*w*np.linalg.solve(Kt[np.ix_(keep,keep)],ub[keep])
        np.testing.assert_allclose(actual[:,col],expected,rtol=3e-10,atol=3e-12)


def test_b21_general_anisotropic_stationary_support_fails_closed():
    bad=CoefficientBearing(
        node=2,kxx=1.0e6,kyy=1.4e6,kxy=0.0,kyx=0.0,cxx=100.0,cyy=100.0
    )
    model=_base();model.advanced_bearings=[bad]
    with pytest.raises(SolverLibraryError,match="not rotation-invariant"):
        FortranBackend().asymmetric_modal(model,200.0)


def test_b21_analysis_metadata_records_frame_policy():
    model=_base();model.advanced_bearings=[_advanced()]
    result=run_asymmetric_modal(model,200.0)
    frf=run_asymmetric_frequency_response(model,[100.0,200.0])
    assert result.metadata["advanced_bearing_policy"]==B21_ROTATING_ADVANCED_POLICY
    assert frf.metadata["rotation_invariance_requirement"]=="A*J = J*A for K,C,M"
