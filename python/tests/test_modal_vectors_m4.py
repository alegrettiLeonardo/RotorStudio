import os, numpy as np
from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing,run_modal
from drm_core.solver.backend import FortranBackend

def model(rigid=False):
    E=2.1e11;G=8.0e10;rho=7800.
    b=[Bearing(1,1),Bearing(3,3,(7e6,7e6,100.,100.))] if rigid else [Bearing(3,1,(8e6,8e6,100.,100.)),Bearing(3,3,(7e6,7e6,100.,100.))]
    return RotorModel([Node(1,0),Node(2,.3),Node(3,.6)],
        [ShaftElement(2,1,2,.05,.005,rho,E,G),ShaftElement(2,2,3,.05,.005,rho,E,G)],
        [Disk.geometric(2,rho,.04,.22,.05)],b)

def _match_error(a,b):
    rem=list(b); errs=[]
    for x in a:
        j=min(range(len(rem)),key=lambda k:abs(rem[k]-x)); y=rem.pop(j); errs.append(abs(x-y)/max(1.,abs(y)))
    return max(errs)

def test_modal_vector_abi_matches_eigenvalue_only_path():
    b=FortranBackend(os.environ['DRMROTOR_LIB']);m=model();w0=b.modal_eigenvalues(m,230.);w,v,ecc=b.modal_eigensystem(m,230.)
    assert v.shape==(12,len(w)); assert ecc.shape==(2,); assert np.all(np.isfinite(v))
    assert _match_error(w,w0)<2e-8

def test_constrained_dofs_restored_as_zero_in_stationary_modes():
    r=run_modal(model(True),180.,with_eigenvectors=True,with_kappa=True)
    assert np.allclose(r.eigenvectors[0:2,:],0,atol=0)
    assert np.all(np.isfinite(r.kappa)); assert r.bearing_eccentricity.shape==(2,)
