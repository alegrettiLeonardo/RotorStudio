import os,copy,numpy as np
from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing,Force,RotorDefinition
from drm_core.solver.backend import FortranBackend

def backend():return FortranBackend(os.environ['DRMROTOR_LIB'])
def coax_model(link=True,ratios=(1.0,-0.7)):
    E=2.05e11;G=7.9e10;rho=7800.
    nodes=[Node(1,0),Node(2,.3),Node(3,.6),Node(4,0),Node(5,.3),Node(6,.6)]
    shafts=[ShaftElement(2,1,2,.045,.005,rho,E,G,1e-5),ShaftElement(2,2,3,.045,.005,rho,E,G,1e-5),ShaftElement(2,4,5,.04,.004,rho,E,G,1.2e-5),ShaftElement(2,5,6,.04,.004,rho,E,G,1.2e-5)]
    disks=[Disk.geometric(2,rho,.04,.20,.045),Disk.geometric(5,rho,.035,.18,.04)]
    bearings=[Bearing(3,1,(6e6,6e6,80.,80.)),Bearing(3,3,(6e6,6e6,80.,80.)),Bearing(3,4,(5e6,5e6,70.,70.)),Bearing(3,6,(5e6,5e6,70.,70.))]
    if link: bearings.append(Bearing(20,2,(5,1.2e6,1.0e6,150.,140.)))
    return RotorModel(nodes,shafts,disks,bearings,[Force(1,(5,1.3e-4,.25))],rotors=[RotorDefinition(1,3,ratios[0]),RotorDefinition(4,6,ratios[1])])
def _sort(v):return np.array(sorted(v,key=lambda z:(abs(z),np.angle(z))))
def _match_error(a,b):
    rem=list(b);errs=[]
    for x in a:
        j=min(range(len(rem)),key=lambda k:abs(rem[k]-x));y=rem.pop(j);errs.append(abs(x-y)/max(1.,abs(y)))
    return max(errs)
def _parts(m):
    b=backend();m0=copy.deepcopy(m);m0.bearings=[];m0.rotors=[]
    M,C0,K0,C1=b.assemble_matrices(m0,0.);_,_,Kp,_=b.assemble_matrices(m0,1.);K1=Kp-K0
    Mb,Cb,Kb,mask,_=b.bearings_matrices(m,200.)
    for br in m.bearings:
        if br.bearing_type==20:
            n1=br.node;n2=int(br.properties[0]);kxx,kyy,cxx,cyy=br.properties[1:5]
            for off,val in ((0,kxx),(1,kyy)):
                a=4*n1-4+off;b2=4*n2-4+off
                K0[a,a]+=val;K0[b2,b2]+=val;K0[a,b2]-=val;K0[b2,a]-=val
            for off,val in ((0,cxx),(1,cyy)):
                a=4*n1-4+off;b2=4*n2-4+off
                C0[a,a]+=val;C0[b2,b2]+=val;C0[a,b2]-=val;C0[b2,a]-=val
    rel=np.zeros(24)
    for r in m.rotors:rel[4*r.node1-4:4*r.node2]=r.speed_factor
    return M+Mb,C0+Cb,C1,K0+Kb,K1,rel,mask

def test_coaxial_with_all_speed_factors_one_reduces_to_stationary_solver_without_links():
    m=coax_model(False,(1.,1.));coax,_=backend().coaxial_modal(m,180.)
    ms=copy.deepcopy(m);ms.rotors=[];stationary=backend().modal_eigenvalues(ms,180.)
    assert _match_error(coax,stationary)<3e-10

def test_chr_root_coax_matches_v2_relspd_and_link_equation():
    m=coax_model(True,(1.,-.7));speed=210.;M,C0,C1,K0,K1,rel,mask=_parts(m);keep=~mask
    C=C0+speed*(rel[:,None]*C1);K=K0+speed*(rel[:,None]*K1)
    Mr=M[np.ix_(keep,keep)];Cr=C[np.ix_(keep,keep)];Kr=K[np.ix_(keep,keep)];n=Mr.shape[0]
    A=np.block([[np.zeros((n,n)),np.eye(n)],[-np.linalg.solve(Mr,Kr),-np.linalg.solve(Mr,Cr)]])
    expected=_sort(np.linalg.eigvals(A));actual,_=backend().coaxial_modal(m,speed)
    assert _match_error(actual,expected)<5e-9

def test_freq_rsp_coax_matches_v2_reference_speed_and_excitation_speed_rules():
    m=coax_model(True,(1.,-.7));speeds=np.array([80.,190.,330.]);actual=backend().coaxial_frequency_response(m,speeds);M,C0,C1,K0,K1,rel,mask=_parts(m);keep=~mask
    ub=np.zeros(24,complex);f=m.forces[0];node=int(f.values[0]);q=f.values[1]*np.exp(1j*f.values[2]);ub[4*node-4]+=q;ub[4*node-3]+=-1j*q
    ratio=m.rotors[1].speed_factor
    for j,w in enumerate(speeds):
        exc=ratio*w;C=C0+w*(rel[:,None]*C1);K=K0+w*(rel[:,None]*K1);A=-M*exc*exc+1j*C*exc+K;exp=np.zeros(24,complex);exp[keep]=np.linalg.solve(A[np.ix_(keep,keep)],ub[keep]*exc*exc)
        assert np.allclose(actual[:,j],exp,rtol=3e-10,atol=3e-11)
