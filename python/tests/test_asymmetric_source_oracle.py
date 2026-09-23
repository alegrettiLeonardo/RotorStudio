import os, numpy as np
from drm_core import RotorModel,Node,AsymmetricShaftElement,ShaftElement,Disk,Bearing,Force
from drm_core.solver.backend import FortranBackend

def backend(): return FortranBackend(os.environ['DRMROTOR_LIB'])
def _shftasym_oracle(st,L,EIx,EIy,Phix,Phiy,rhoA,rhoI):
    shear=st not in (11,15,17,18);rotary=st not in (11,14,16,18);gyro=st not in (13,16,17,18)
    if not shear:Phix=Phiy=0.
    Kx=np.array([[12,6*L,-12,6*L],[6*L,(4+Phix)*L*L,-6*L,(2-Phix)*L*L],[-12,-6*L,12,-6*L],[6*L,(2-Phix)*L*L,-6*L,(4+Phix)*L*L]],float)*EIx/((1+Phix)*L**3)
    Ky=np.array([[12,-6*L,-12,-6*L],[-6*L,(4+Phiy)*L*L,6*L,(2-Phiy)*L*L],[-12,6*L,12,6*L],[-6*L,(2-Phiy)*L*L,6*L,(4+Phiy)*L*L]],float)*EIy/((1+Phiy)*L**3)
    K0=np.zeros((8,8));ix=np.array([0,3,4,7]);iy=np.array([1,2,5,6]);K0[np.ix_(ix,ix)]=Kx;K0[np.ix_(iy,iy)]=Ky
    m1=156;m2=22*L;m3=54;m4=-13*L;m5=4*L**2;m6=-3*L**2
    M=np.array([[m1,0,0,m2,m3,0,0,m4],[0,m1,-m2,0,0,m3,-m4,0],[0,-m2,m5,0,0,m4,m6,0],[m2,0,0,m5,-m4,0,0,m6],[m3,0,0,-m4,m1,0,0,-m2],[0,m3,m4,0,0,m1,m2,0],[0,-m4,m6,0,0,m2,m5,0],[m4,0,0,m6,-m2,0,0,m5]],float)*rhoA*L/420
    K2=-M.copy()
    C1=np.array([[0,-m1,m2,0,0,-m3,m4,0],[m1,0,0,m2,m3,0,0,m4],[-m2,0,0,-m5,m4,0,0,-m6],[0,-m2,m5,0,0,m4,m6,0],[0,-m3,-m4,0,0,-m1,-m2,0],[m3,0,0,-m4,m1,0,0,-m2],[-m4,0,0,-m6,m2,0,0,-m5],[0,-m4,m6,0,0,m2,m5,0]],float)*rhoA*L/210
    if rotary:
        m7=36;m8=3*L;m9=4*L**2;m10=-L**2
        Ms=np.array([[m7,0,0,m8,-m7,0,0,m8],[0,m7,-m8,0,0,-m7,-m8,0],[0,-m8,m9,0,0,m8,m10,0],[m8,0,0,m9,-m8,0,0,m10],[-m7,0,0,-m8,m7,0,0,-m8],[0,-m7,m8,0,0,m7,m8,0],[0,-m8,m10,0,0,m8,m9,0],[m8,0,0,m10,-m8,0,0,m9]],float)*rhoI/(30*L)
        M+=Ms
        Cs=np.array([[0,-m7,m8,0,0,m7,m8,0],[m7,0,0,m8,-m7,0,0,m8],[-m8,0,0,-m9,m8,0,0,-m10],[0,-m8,m9,0,0,m8,m10,0],[0,m7,-m8,0,0,-m7,-m8,0],[-m7,0,0,-m8,m7,0,0,-m8],[-m8,0,0,-m10,m8,0,0,-m9],[0,-m8,m10,0,0,m8,m9,0]],float)
        Cs=rhoI*Ms/(15*L);C1+=Cs
    if gyro:
        k1=36;k2=3*L;k3=4*L**2;k4=-L**2
        Ge=np.array([[0,-k1,k2,0,0,k1,k2,0],[k1,0,0,k2,-k1,0,0,k2],[-k2,0,0,-k3,k2,0,0,-k4],[0,-k2,k3,0,0,k2,k4,0],[0,k1,-k2,0,0,-k1,-k2,0],[-k1,0,0,-k2,k1,0,0,-k2],[-k2,0,0,-k4,k2,0,0,-k3],[0,-k2,k4,0,0,k2,k3,0]],float);C1-=rhoI*Ge/(15*L)
        G1=np.array([[k1,0,0,k2,-k1,0,0,k2],[0,k1,-k2,0,0,-k1,-k2,0],[0,-k2,k3,0,0,k4,k4,0],[k2,0,0,k3,-k4,0,0,k4],[-k1,0,0,-k2,k1,0,0,-k2],[0,-k1,k2,0,0,k1,k2,0],[0,-k2,k4,0,0,k2,k3,0],[k2,0,0,k4,-k2,0,0,k3]],float);K2+=2*rhoI*G1/(15*L)
    return M,C1,K0,K2

def test_shftasym_types_11_to_18_match_v2_source_including_legacy_cs_behavior():
    L=.31;pars=(1.25e5,1.05e5,.07,.09,11.5,.0042)
    for st in range(11,19):
        m=RotorModel([Node(1,0),Node(2,L)],[AsymmetricShaftElement(st,1,2,*pars)],[],[])
        M,C0,C1,K0,K1,K2=backend().asymmetric_assemble(m);Mo,C1o,K0o,K2o=_shftasym_oracle(st,L,*pars)
        assert np.allclose(C0,0);assert np.allclose(K1,0)
        for a,e in ((M,Mo),(C1,C1o),(K0,K0o),(K2,K2o)): assert np.allclose(a,e,rtol=2e-12,atol=1e-10), (st,np.max(np.abs(a-e)))

def _asym_model():
    return RotorModel([Node(1,0),Node(2,.3),Node(3,.6)],
      [AsymmetricShaftElement(12,1,2,1.2e5,1.0e5,.08,.09,12.,.004),AsymmetricShaftElement(12,2,3,1.2e5,1.0e5,.08,.09,12.,.004)],
      [Disk.anisotropic(2,8.,.03,.04,.05)],
      [Bearing(4,1,(1e6,1e6,2e4,2e4,100.,100.,5.,5.)),Bearing(4,3,(1e6,1e6,2e4,2e4,100.,100.,5.,5.))],
      [Force(1,(2,1e-4,.2)),Force(2,(2,2e-5,-.1))])

def test_bearasym_type4_preserves_v2_index_defect():
    m=_asym_model();C,K,K1,mask=backend().asymmetric_bearings(m)
    assert K1[0,1]==-100.;assert K1[1,0]==5.;assert K1[2,3]==-5.;assert K1[3,2]==0.
    assert not mask.any()

def test_chr_asym_preserves_nargout_dependent_k1b_behavior():
    m=_asym_model();e_only,_=backend().asymmetric_modal(m,200.,False);e_vec,_=backend().asymmetric_modal(m,200.,True)
    assert np.max(np.abs(e_only-e_vec))>1e-3

def test_freq_asym_matches_static_rotating_frame_source_equation():
    m=_asym_model();b=backend();M,C0,C1,K0,K1,K2=b.asymmetric_assemble(m);Cb,Kb,K1b,mask=b.asymmetric_bearings(m);keep=~mask
    speeds=np.array([0.,120.,260.]);actual=b.asymmetric_frequency_response(m,speeds)
    ub=np.zeros(12)
    for f in m.forces:
        node=int(f.values[0]);mag,phase=f.values[1],f.values[2]
        if f.force_type==1:ub[4*node-4]+=mag*np.cos(phase);ub[4*node-3]+=mag*np.sin(phase)
        if f.force_type==2:ub[4*node-2]+=-mag*np.sin(phase);ub[4*node-1]+=mag*np.cos(phase)
    for j,w in enumerate(speeds):
        K=K0+Kb+w*(K1+K1b)+w*w*K2;exp=np.zeros(12);exp[keep]=w*w*np.linalg.solve(K[np.ix_(keep,keep)],ub[keep])
        assert np.allclose(actual[:,j],exp,rtol=2e-11,atol=2e-12)

def test_rotorasym_circular_shaft_conversion_matches_explicit_asymmetric_properties():
    E=2.1e11;G=8.1e10;rho=7800.;do=.05;di=.01;L=.27
    I=np.pi*(do**4-di**4)/64;A=np.pi*(do**2-di**2)/4;nu=.5*(E/G)-1;r=di/do;r2=r*r;r12=(1+r2)**2;kappa=6*r12*(1+nu)/(r12*(7+6*nu)+r2*(20+12*nu));phi=12*E*I/(G*kappa*A*L**2)
    mc=RotorModel([Node(1,0),Node(2,L)],[ShaftElement(2,1,2,do,di,rho,E,G)],[],[])
    ma=RotorModel([Node(1,0),Node(2,L)],[AsymmetricShaftElement(12,1,2,E*I,E*I,phi,phi,rho*A,rho*I)],[],[])
    ac=backend().asymmetric_assemble(mc);aa=backend().asymmetric_assemble(ma)
    for x,y in zip(ac,aa): assert np.allclose(x,y,rtol=3e-12,atol=1e-10)
