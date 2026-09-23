import os, numpy as np
from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing,Force
from drm_core.solver.backend import FortranBackend

def backend():return FortranBackend(os.environ['DRMROTOR_LIB'])
def base(force):
    E=211e9;G=81.2e9;rho=7810.
    return RotorModel([Node(i+1,.25*i) for i in range(7)],
        [ShaftElement(2,i,i+1,.05,0,rho,E,G,0) for i in range(1,7)],
        [Disk.geometric(3,rho,.07,.28,.05),Disk.geometric(5,rho,.07,.35,.05)],
        [Bearing(3,1,(1e6,1e6,100,100)),Bearing(3,7,(1e6,1e6,100,100))],[force])

def test_freq_aux_spinner_forward_backward_and_vibrator_match_source_equation():
    b=backend();rs=300.;omega=np.array([20.,120.,260.])
    for force,direction in [(Force(6,(4,1e-4,.3)),1.),(Force(6,(4,1e-4,.3)),-1.),(Force(7,(4,10.,-2.)),1.)]:
        m=base(force);actual=b.auxiliary_frequency_response(m,rs,omega,direction);M,C,K,_=b.assemble_matrices(m,rs);f=np.zeros(28,complex);node=4
        if force.force_type==6:
            q=1e-4*np.exp(1j*.3);f[4*node-4]=q;f[4*node-3]=(-1j if direction>0 else 1j)*q
        else:f[4*node-4]=10.;f[4*node-3]=-2.
        for j,w in enumerate(omega):
            A=K-w*w*M+1j*w*C;rhs=(w*w*f if force.force_type==6 else f);exp=np.linalg.solve(A,rhs)
            assert np.allclose(actual[:,j],exp,rtol=3e-11,atol=3e-12)

def test_freq_fdn_matches_v2_dynamic_stiffness_and_legacy_bearing_mapping():
    b=backend();m=base(Force(4,(0.,1e-5,0.,2e-5)));rs=2*np.pi*3000/60;omega=2*np.pi*np.array([1.,10.,35.]);actual=b.foundation_frequency_response(m,rs,omega)
    M,C,K,_=b.assemble_matrices(m,rs);Mb,Cb,Kb,mask,_=b.bearings_matrices(m,rs);qf=np.zeros(28);qf[0]=0;qf[1]=1e-5;qf[24]=0;qf[25]=2e-5
    for j,w in enumerate(omega):
        rhs=(-w*w*Mb+1j*w*Cb+Kb)@qf;exp=np.zeros(28,complex);keep=~mask;exp[keep]=np.linalg.solve((K-w*w*M+1j*w*C)[np.ix_(keep,keep)],rhs[keep])
        assert np.allclose(actual[:,j],exp,rtol=3e-11,atol=3e-12)
