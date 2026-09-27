from __future__ import annotations

from dataclasses import replace
import numpy as np
import pytest

from drm_core import Bearing, CoefficientBearing, Force, Node, RotorModel, ShaftElement
from drm_core.solver.backend import FortranBackend
from drm_core.solver.bearings_backend import AdvancedBearingBackend
from drm_core.solver.ffi import SolverLibraryError


def _bearing(**changes):
    base=CoefficientBearing(
        node=1,
        kxx=1.20e6,kxy=2.0e4,kyx=-3.0e4,kyy=1.45e6,
        cxx=180.0,cxy=8.0,cyx=-6.0,cyy=210.0,
        mxx=12.0,mxy=0.4,myx=0.4,myy=9.0,
        tag="B19 nonzero bearing mass",
    )
    return replace(base,**changes)


def _model(bearing=None, *, force=False):
    return RotorModel(
        nodes=[Node(1,0.0),Node(2,1.0)],
        shafts=[ShaftElement(2,1,2,0.05,0.0,7810.0,211e9,81.2e9,0.0,0.0,0.0)],
        bearings=[Bearing(5,2,(1.3e6,0.0,0.0,1.4e6,160.0,0.0,0.0,170.0))],
        forces=[Force(1,(1,1.0e-4,0.25))] if force else [],
        advanced_bearings=[bearing or _bearing()],
    )


def _match_error(actual,expected):
    remaining=list(expected);errors=[]
    for value in actual:
        j=min(range(len(remaining)),key=lambda k:abs(remaining[k]-value))
        ref=remaining.pop(j)
        errors.append(abs(value-ref)/max(1.0,abs(ref)))
    return max(errors)


def test_b19_internal_adapter_preserves_full_translational_mass_matrix():
    bearing=_bearing(mxy=0.7,myx=-0.2)
    legacy=AdvancedBearingBackend().as_legacy_bearing(bearing,100.0,70.0)
    assert legacy.bearing_type==9
    np.testing.assert_allclose(
        legacy.properties,
        (
            1.20e6,2.0e4,-3.0e4,1.45e6,
            180.0,8.0,-6.0,210.0,
            12.0,0.7,-0.2,9.0,
        ),
        rtol=0,atol=0,
    )


def test_b19_zero_mass_keeps_b12_type5_bridge():
    zero=_bearing(mxx=0.0,mxy=0.0,myx=0.0,myy=0.0)
    legacy=AdvancedBearingBackend().as_legacy_bearing(zero,100.0)
    assert legacy.bearing_type==5
    assert len(legacy.properties)==8


def test_b19_native_bearing_assembly_adds_M_C_K_at_exact_node():
    bearing=_bearing(mxy=0.7,myx=-0.2)
    backend=FortranBackend()
    Mb,Cb,Kb,mask,_=backend.bearings_matrices(_model(bearing),125.0)
    expectedM=np.array([[12.0,0.7],[-0.2,9.0]])
    expectedC=np.array([[180.0,8.0],[-6.0,210.0]])
    expectedK=np.array([[1.20e6,2.0e4],[-3.0e4,1.45e6]])
    np.testing.assert_allclose(Mb[:2,:2],expectedM,rtol=0,atol=1e-14)
    np.testing.assert_allclose(Cb[:2,:2],expectedC,rtol=0,atol=1e-12)
    np.testing.assert_allclose(Kb[:2,:2],expectedK,rtol=0,atol=1e-9)
    assert np.count_nonzero(Mb[2:,:])==0
    assert not mask.any()


def test_b19_stationary_modal_uses_bearing_mass_in_second_order_equation():
    backend=FortranBackend()
    model=_model()
    speed=150.0
    M,C,K,_=backend.assemble_matrices(model,speed)
    n=M.shape[0]
    A=np.block([
        [np.zeros((n,n)),np.eye(n)],
        [-np.linalg.solve(M,K),-np.linalg.solve(M,C)],
    ])
    expected=np.linalg.eigvals(A)
    actual=backend.modal_eigenvalues(model,speed)
    assert _match_error(actual,expected)<2e-9


def test_b19_synchronous_frf_contains_negative_omega_squared_bearing_mass_term():
    backend=FortranBackend()
    model=_model(force=True)
    omega=120.0
    actual=backend.frequency_response(model,[omega])[:,0]
    M,C,K,_=backend.assemble_matrices(model,omega)
    q=1.0e-4*np.exp(1j*0.25)
    rhs=np.zeros(M.shape[0],dtype=complex)
    rhs[0]+=q*omega**2
    rhs[1]+=-1j*q*omega**2
    expected=np.linalg.solve(K+1j*omega*C-omega**2*M,rhs)
    np.testing.assert_allclose(actual,expected,rtol=3e-10,atol=3e-11)


def test_b19_mass_table_interpolation_is_used_at_operating_point():
    b=CoefficientBearing(
        node=1,speed_rad_s=(100.0,200.0),interpolation="linear",
        kxx=(1.2e6,1.2e6),kyy=(1.4e6,1.4e6),
        cxx=(180.0,180.0),cyy=(210.0,210.0),
        mxx=(10.0,14.0),mxy=(1.0,3.0),myx=(1.0,3.0),myy=(8.0,12.0),
    )
    Mb,_,_,_,_=FortranBackend().bearings_matrices(_model(b),150.0)
    np.testing.assert_allclose(Mb[:2,:2],[[12.0,2.0],[2.0,10.0]],rtol=2e-14,atol=2e-14)


def test_b19_b18_runup_still_fails_closed_for_nonzero_M():
    from drm_core.analysis.transient import run_runup
    with pytest.raises(SolverLibraryError,match="nonzero advanced-bearing M"):
        run_runup(_model(),np.array([10.0,100.0,0.0]),[0.0,0.1],nr=0)
