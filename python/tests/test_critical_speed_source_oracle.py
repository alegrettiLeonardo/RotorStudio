import os, copy, numpy as np
from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing
from drm_core.solver.backend import FortranBackend

def backend(): return FortranBackend(os.environ['DRMROTOR_LIB'])
def const_model():
    E=2.1e11;G=8.0e10;rho=7800.
    return RotorModel([Node(1,0),Node(2,.3),Node(3,.65)],
      [ShaftElement(2,1,2,.055,.01,rho,E,G,2e-5),ShaftElement(2,2,3,.05,.008,rho,E,G,2e-5)],
      [Disk.geometric(2,rho,.05,.24,.055)],
      [Bearing(3,1,(9e6,9e6,120.,120.)),Bearing(3,3,(8e6,8e6,100.,100.))])
def fluid_model():
    m=const_model();m.bearings=[Bearing(7,1,(900.,.05,.025,55e-6,.02)),Bearing(3,3,(7e6,7e6,100.,100.))];return m

def _sort_matlab(v):
    return np.array(sorted(v,key=lambda z:(abs(z),np.angle(z))))
def _state_eigs(M,C,K):
    n=M.shape[0];XK=np.linalg.solve(M,K);XC=np.linalg.solve(M,C)
    A=np.block([[np.zeros((n,n)),np.eye(n)],[-XK,-XC]])
    return _sort_matlab(np.linalg.eigvals(A))
def _direct_oracle(m,NX=1.,damped=True,ncrit=3):
    b=backend();M,C0,K0,G=b.assemble_matrices(m,0.);_,_,K1p,_=b.assemble_matrices(m,1.);K1=K1p-K0
    NX=max(abs(NX),.2);MM=-NX**2*M+1j*NX*G;CC=1j*NX*C0+K1;KK=K0
    n=M.shape[0];A=np.block([[np.zeros((n,n),complex),np.eye(n)],[-np.linalg.solve(MM,KK),-np.linalg.solve(MM,CC)]])
    e=_sort_matlab(np.linalg.eigvals(A));sel=e[0:2*ncrit:2]
    return np.abs(sel.real) if damped else np.abs(sel)

def test_critical_direct_matches_source_equation_damped_and_undamped():
    m=const_model();b=backend()
    for damped in (True,False):
        expected=_direct_oracle(m,1.35,damped,3)
        actual=b.critical_speeds(m,NX=1.35,damped=damped,ncrit=3,method=1)
        assert np.allclose(actual,expected,rtol=2e-10,atol=2e-8)

def _rotor_parts_without_bearings(m):
    m0=copy.deepcopy(m);m0.bearings=[];b=backend();M,C0,K0,G=b.assemble_matrices(m0,0.);_,_,Kp,_=b.assemble_matrices(m0,1.);return M,C0,G,K0,Kp-K0

def _iter_mode_number_oracle(m,NX=1.,damped=True,ncrit=2,maxiter=30,tol=1e-8):
    b=backend();NX=max(abs(NX),.2);M0,C0,C1,K0,K1=_rotor_parts_without_bearings(m);guess=2*np.pi*500/60
    Mb,Cb,Kb,mask,_=b.bearings_matrices(m,guess);keep=~mask;e0=_state_eigs((M0+Mb)[np.ix_(keep,keep)],(C0+Cb+guess*C1)[np.ix_(keep,keep)],(K0+Kb+guess*K1)[np.ix_(keep,keep)])
    out=[]
    for ic in range(ncrit):
        ie=2*ic;ci=(abs(e0[ie].imag) if damped else abs(e0[ie]))/NX
        for _ in range(maxiter):
            Mb,Cb,Kb,mask,_=b.bearings_matrices(m,ci);keep=~mask
            e=_state_eigs((M0+Mb)[np.ix_(keep,keep)],(C0+Cb+ci*C1)[np.ix_(keep,keep)],(K0+Kb+ci*K1)[np.ix_(keep,keep)])
            old=ci;ci=(abs(e[ie].imag) if damped else abs(e[ie]))/NX
            rel=2*tol if old==0 else abs((ci-old)/old)
            if rel<=tol:break
        out.append(ci)
    return np.array(out)

def test_critical_iterative_method2_matches_source_iteration_with_fluid_bearing():
    m=fluid_model();expected=_iter_mode_number_oracle(m,ncrit=2,tol=1e-8)
    actual,it,conv=backend().critical_speeds(m,ncrit=2,max_iterations=30,tol=1e-8,method=2,return_diagnostics=True)
    assert it.tolist()==[30,6];assert conv.tolist()==[False,True];assert np.allclose(actual,expected,rtol=3e-9,atol=2e-7)

def _iter_initial_oracle(m,initial,NX=1.,damped=True,maxiter=30,tol=1e-9):
    b=backend();NX=max(abs(NX),.2);M0,C0,C1,K0,K1=_rotor_parts_without_bearings(m);out=[]
    for target in initial:
        ci=abs(target)
        for _ in range(maxiter):
            Mb,Cb,Kb,mask,_=b.bearings_matrices(m,ci);keep=~mask
            e=_state_eigs((M0+Mb)[np.ix_(keep,keep)],(C0+Cb+ci*C1)[np.ix_(keep,keep)],(K0+Kb+ci*K1)[np.ix_(keep,keep)])
            est=(np.abs(e.imag) if damped else np.abs(e))/NX
            old=ci;ci=est[np.argmin(np.abs(est-target))]
            rel=2*tol if old==0 else abs((ci-old)/old)
            if rel<=tol:break
        out.append(ci)
    return np.array(out)

def test_critical_iterative_method3_preserves_v2_closest_to_initial_estimate_rule():
    m=const_model();initial=np.array([80.,350.]);expected=_iter_initial_oracle(m,initial)
    actual,it,conv=backend().critical_speeds(m,ncrit=2,max_iterations=30,tol=1e-9,method=3,initial_estimates=initial,return_diagnostics=True)
    assert np.all(conv);assert np.allclose(actual,expected,rtol=2e-9,atol=2e-7)

def two_fluid_formal_model():
    E=211e9;G=81.2e9;rho=7810.
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[ShaftElement(2,i,i+1,.05,0.,rho,E,G,2e-5) for i in range(1,7)]
    disks=[Disk.geometric(3,rho,.07,.28,.05),Disk.geometric(5,rho,.07,.35,.05)]
    bearings=[Bearing(7,1,(525.,.1,.03,1e-4,.1)),Bearing(7,7,(525.,.1,.03,1e-4,.1))]
    return RotorModel(nodes,shafts,disks,bearings)

def test_method2_reuses_the_original_500rpm_spectrum_for_each_critical():
    m=two_fluid_formal_model()
    expected=_iter_mode_number_oracle(m,ncrit=2,maxiter=20,tol=1e-6)
    actual,it,conv=backend().critical_speeds(m,ncrit=2,max_iterations=20,tol=1e-6,method=2,return_diagnostics=True)
    assert it.tolist()==[20,20]
    assert conv.tolist()==[False,False]
    assert np.allclose(actual,expected,rtol=3e-9,atol=2e-7)
