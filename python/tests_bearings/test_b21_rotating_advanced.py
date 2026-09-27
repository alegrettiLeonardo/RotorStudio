from __future__ import annotations
import numpy as np
import pytest
from drm_core import Bearing,CoefficientBearing,Force,Node,RotorModel,ShaftElement
from drm_core.analysis.asymmetric import run_asymmetric_frequency_response,run_asymmetric_modal
from drm_core.solver.backend import FortranBackend
from drm_core.solver.bearings_backend import AdvancedBearingBackend
from drm_core.solver.ffi import SolverLibraryError

J=np.array([[0.0,-1.0],[1.0,0.0]])

def _bearing(node=1,anisotropic=False):
    speed=(80.0,180.0,300.0)
    if anisotropic:
        return CoefficientBearing(node=node,speed_rad_s=speed,interpolation="linear",
          kxx=(1.0e6,1.1e6,1.2e6),kyy=(1.4e6,1.5e6,1.6e6),
          cxx=(100.,110.,120.),cyy=(100.,110.,120.))
    return CoefficientBearing(node=node,speed_rad_s=speed,interpolation="linear",
      kxx=tuple(1.2e6+250*w for w in speed),kxy=tuple(-(2e4+10*w) for w in speed),
      kyx=tuple(2e4+10*w for w in speed),kyy=tuple(1.2e6+250*w for w in speed),
      cxx=tuple(170+.08*w for w in speed),cxy=tuple(-(6+.01*w) for w in speed),
      cyx=tuple(6+.01*w for w in speed),cyy=tuple(170+.08*w for w in speed),
      mxx=tuple(1.5+.001*w for w in speed),mxy=0.,myx=0.,
      myy=tuple(1.5+.001*w for w in speed))

def _model(advanced=None,legacy=None):
    E=2.1e11;G=8.1e10;rho=7800.
    bearings=[Bearing(3,2,(1.6e6,1.6e6,140.,140.)),*([] if legacy is None else [legacy])]
    return RotorModel([Node(1,0.),Node(2,.5)],[ShaftElement(2,1,2,.05,0.,rho,E,G)],[],
      bearings,[Force(1,(1,1e-4,.2))],advanced_bearings=[] if advanced is None else [advanced])

def _type10(bearing,speed):
    return AdvancedBearingBackend().as_rotating_bearing(bearing,speed,speed)

def _match_error(a,b):
    rem=list(np.asarray(b,dtype=complex));err=[]
    for x in np.asarray(a,dtype=complex):
        j=min(range(len(rem)),key=lambda k:abs(rem[k]-x));y=rem.pop(j)
        err.append(abs(x-y)/max(1.,abs(y)))
    return max(err)

def test_b21_rotation_invariant_provider_creates_type10_and_preserves_mass():
    bearing=_bearing();row=_type10(bearing,180.)
    assert row.bearing_type==10
    ev=AdvancedBearingBackend().evaluate(bearing,180.,180.)
    np.testing.assert_allclose(np.asarray(row.properties[8:12]).reshape(2,2),ev.M,rtol=0,atol=0)

def test_b21_general_anisotropic_fixed_frame_bearing_fails_closed():
    with pytest.raises(SolverLibraryError,match="2\\*Omega-periodic"):
        _type10(_bearing(anisotropic=True),180.)

def test_b21_rotating_modal_matches_explicit_type10_for_both_nargout_paths():
    bearing=_bearing();speed=180.;advanced=_model(advanced=bearing);oracle=_model(legacy=_type10(bearing,speed))
    for vectors in (False,True):
        a=run_asymmetric_modal(advanced,speed,with_eigenvectors=vectors)
        o=run_asymmetric_modal(oracle,speed,with_eigenvectors=vectors)
        assert _match_error(a.eigenvalues,o.eigenvalues)<2e-10

def test_b21_rotating_transformation_matrices_follow_coordinate_identity():
    bearing=_bearing();speed=180.;model=_model(advanced=bearing);b=FortranBackend()
    M,C,C1,K,K1legacy,K1adv,K2,mask=b.asymmetric_bearings(model,speed)
    ev=AdvancedBearingBackend().evaluate(bearing,speed,speed);sl=np.ix_([0,1],[0,1])
    np.testing.assert_allclose(M[sl],ev.M,rtol=0,atol=2e-13)
    np.testing.assert_allclose(C[sl],ev.C,rtol=0,atol=2e-13)
    np.testing.assert_allclose(C1[sl],2*ev.M@J,rtol=0,atol=2e-13)
    np.testing.assert_allclose(K[sl],ev.K,rtol=0,atol=2e-13)
    np.testing.assert_allclose(K1adv[sl],ev.C@J,rtol=0,atol=2e-13)
    np.testing.assert_allclose(K2[sl],-ev.M,rtol=0,atol=2e-13)
    assert np.allclose(K1legacy,0);assert not mask.any()

def test_b21_rotating_frf_re_evaluates_at_each_synchronous_speed():
    bearing=_bearing();speeds=np.array([90.,180.,280.])
    actual=run_asymmetric_frequency_response(_model(advanced=bearing),speeds).response
    for j,speed in enumerate(speeds):
        oracle=run_asymmetric_frequency_response(_model(legacy=_type10(bearing,float(speed))),np.array([speed])).response[:,0]
        np.testing.assert_allclose(actual[:,j],oracle,rtol=5e-11,atol=5e-12)
