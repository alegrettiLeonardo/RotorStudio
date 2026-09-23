import os, numpy as np
from drm_core import RotorModel,Node,ShaftElement,TaperedShaftElement,Disk,Bearing,Force
from drm_core.solver.backend import FortranBackend

def rotor(taper=False):
    E=2e11; G=E/(2*(1+.27)); rho=7800.
    nodes=[Node(1,0),Node(2,.3),Node(3,.6)]
    if taper:
        shafts=[TaperedShaftElement(22,1,2,.08,.075,.02,.018,rho,E,G),TaperedShaftElement(22,2,3,.075,.07,.018,.015,rho,E,G)]
    else:
        shafts=[ShaftElement(2,1,2,.08,.02,rho,E,G),ShaftElement(2,2,3,.08,.02,rho,E,G)]
    return RotorModel(nodes,shafts,[Disk.geometric(2,rho,.05,.25,.08)],[Bearing(3,1,(1e7,1e7,100.,100.)),Bearing(3,3,(1e7,1e7,100.,100.))])

def backend(): return FortranBackend(os.environ['DRMROTOR_LIB'])

def test_assembled_matrix_invariants():
    M,C,K,G=backend().assemble_matrices(rotor(),300.)
    assert np.allclose(M,M.T,rtol=1e-12,atol=1e-10)
    assert np.allclose(G,-G.T,rtol=1e-12,atol=1e-10)
    assert np.all(np.diag(M)>0)
    assert np.isfinite([M,C,K,G]).all()

def test_tapered_modal_executes():
    e=backend().modal_eigenvalues(rotor(True),300.)
    assert np.isfinite(e).all() and len(e)>0

def test_frequency_response_unbalance_and_zero_speed():
    m=rotor();m.forces=[Force(1,(2,1e-4,0.3))]
    r=backend().frequency_response(m,[0.,100.,200.])
    assert r.shape==(12,3);assert np.allclose(r[:,0],0);assert np.isfinite(r).all();assert np.linalg.norm(r[:,2])>0

def test_critical_speed_direct():
    c=backend().critical_speeds(rotor(),ncrit=2)
    assert np.isfinite(c).all();assert np.all(c>=0)
