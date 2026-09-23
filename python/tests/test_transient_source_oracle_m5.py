import os, copy
import numpy as np
import scipy.linalg as la
from scipy.integrate import solve_ivp
from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing,Force
from drm_core.solver.backend import FortranBackend
from drm_core.analysis.transient import run_foundation_time_response,run_runup
from drm_core.units import rpm_to_rad_s


def backend(): return FortranBackend(os.environ['DRMROTOR_LIB'])

def foundation_model():
    E=211e9;G=81.2e9;rho=7810.
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[ShaftElement(2,i,i+1,.05,0.,rho,E,G,0.) for i in range(1,7)]
    disks=[Disk.geometric(3,rho,.07,.28,.05),Disk.geometric(5,rho,.07,.35,.05)]
    bearings=[Bearing(3,1,(1e6,1e6,100.,100.)),Bearing(3,7,(1e6,1e6,100.,100.))]
    return RotorModel(nodes,shafts,disks,bearings,[Force(5,(0.,1e-3,0.,1e-3,.025))])

def runup_model():
    E=211e9;G=E/(2*(1+.3));rho=7810.
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[ShaftElement(2,i,i+1,.025,0.,rho,E,G,0.) for i in range(1,7)]
    disks=[Disk.geometric(7,rho,.04,.25,0.)]
    bearings=[Bearing(3,1,(1e7,2e7,4e5,4e5)),Bearing(3,5,(1e7,2e7,4e5,4e5))]
    return RotorModel(nodes,shafts,disks,bearings,[Force(1,(7,1e-3,0.))])

def modal_basis(M,K,nr):
    w,V=la.eig(K,M)
    assert np.max(np.abs(w.imag))<1e-7*np.maximum(1,np.max(np.abs(w.real)))
    order=np.argsort(w.real);w=w.real[order];V=V.real[:,order]
    if nr>0 and nr<M.shape[0]: return V[:,:nr],w
    return np.eye(M.shape[0]),w

def foundation_oracle(model,rotor_speed,dt,npts,nr):
    b=backend();M,C,K,_=b.assemble_matrices(model,rotor_speed);Mb,Cb,Kb,mask,_=b.bearings_matrices(model,rotor_speed);keep=~mask
    qf=np.zeros(M.shape[0]);vals=model.forces[0].values
    for i,br in enumerate(model.bearings):qf[4*br.node-4]=vals[2*i];qf[4*br.node-3]=vals[2*i+1]
    pulse=vals[2*len(model.bearings)];Mr=M[np.ix_(keep,keep)];Cr=C[np.ix_(keep,keep)];Kr=K[np.ix_(keep,keep)]
    Tr,eig=modal_basis(Mr,Kr,nr);Mr2=Tr.T@Mr@Tr;Cr2=Tr.T@Cr@Tr;Kr2=Tr.T@Kr@Tr
    Mf=Tr.T@(Mb@qf)[keep];Cf=Tr.T@(Cb@qf)[keep];Kf=Tr.T@(Kb@qf)[keep]
    XK=la.solve(Mr2,Kr2);XC=la.solve(Mr2,Cr2);B2=la.solve(Mr2,Mf);B1=la.solve(Mr2,Cf);B0=la.solve(Mr2,Kf);om=np.pi/pulse;nred=Tr.shape[1]
    def rhs(t,y):
        d=np.empty_like(y);d[:nred]=y[nred:];d[nred:]=-XK@y[:nred]-XC@y[nred:]
        if t<=pulse:
            yy=np.sin(om*t);yd=om*np.cos(om*t);ydd=-om*om*yy;d[nred:]+=B2*ydd+B1*yd+B0*yy
        return d
    te=dt*np.arange(npts);sol=solve_ivp(rhs,(te[0],te[-1]),np.zeros(2*nred),method='DOP853',rtol=2e-11,atol=2e-13,t_eval=te)
    out=np.zeros((M.shape[0],npts));out[keep,:]=Tr@sol.y[:nred,:]
    force=np.where(te<=pulse,np.sin(np.pi*te/pulse),0.)
    return te,out,force,float(np.sqrt(eig[(nr if 0<nr<len(eig) else len(eig))-1])/(2*np.pi))

def runup_oracle(model,alpha,t_eval,nr):
    b=backend();M,C,K,C1=b.assemble_matrices(model,0.);_,_,_,mask,_=b.bearings_matrices(model,0.);keep=~mask
    Mr=M[np.ix_(keep,keep)];Cr=C[np.ix_(keep,keep)];Kr=K[np.ix_(keep,keep)];G=C1[np.ix_(keep,keep)];Tr,eig=modal_basis(Mr,Kr,nr)
    Mr2=Tr.T@Mr@Tr;Cr2=Tr.T@Cr@Tr;Gr=Tr.T@G@Tr;Kr2=Tr.T@Kr@Tr
    XK=la.solve(Mr2,Kr2);XC=la.solve(Mr2,Cr2);XG=la.solve(Mr2,Gr)
    fc=np.zeros(M.shape[0],complex)
    for f in model.forces:
        if f.force_type==1:
            node=int(f.values[0]);q=f.values[1]*np.exp(1j*f.values[2]);fc[4*node-4]+=q;fc[4*node-3]+=-1j*q
        elif f.force_type==2:
            node=int(f.values[0]);q=f.values[1]*np.exp(1j*f.values[2]);fc[4*node-2]+=1j*q;fc[4*node-1]+=q
    B=la.solve(Mr2,Tr.T@fc[keep]);nred=Tr.shape[1];a2,a1,a0=alpha
    def rhs(t,y):
        phi=a2*t*t+a1*t+a0;dphi=2*a2*t+a1;ddphi=2*a2
        d=np.empty_like(y);d[:nred]=y[nred:]
        d[nred:]=-XK@y[:nred]-XC@y[nred:]-dphi*(XG@y[nred:])+np.real(B*(dphi*dphi-1j*ddphi)*np.exp(1j*phi))
        return d
    sol=solve_ivp(rhs,(t_eval[0],t_eval[-1]),np.zeros(2*nred),method='DOP853',rtol=2e-11,atol=2e-13,t_eval=t_eval)
    out=np.zeros((M.shape[0],len(t_eval)));out[keep,:]=Tr@sol.y[:nred,:]
    speed=2*a2*t_eval+a1
    return out,speed,float(np.sqrt(eig[(nr if 0<nr<len(eig) else len(eig))-1])/(2*np.pi))

def test_time_fdn_modal_truncation_and_dp45_against_independent_dop853():
    m=foundation_model();rs=rpm_to_rad_s(3000);r=run_foundation_time_response(m,rs,2e-4,601,nr=10,rtol=2e-7,atol=2e-10)
    t,x,f,maxf=foundation_oracle(m,rs,2e-4,601,10)
    assert r.metadata['nr_used']==10;assert abs(r.metadata['max_reduced_frequency_hz']-maxf)/maxf<3e-10
    assert np.allclose(r.time_s,t,rtol=0,atol=1e-15);assert np.allclose(r.forcing,f,rtol=0,atol=2e-15)
    assert np.allclose(r.response,x,rtol=3e-5,atol=4e-9)
    assert r.metadata['accepted_steps']>=600 and r.metadata['rejected_steps']>=0

def test_time_fdn_full_model_nr_zero_matches_v2_no_reduction_rule():
    m=foundation_model();rs=rpm_to_rad_s(3000);r=run_foundation_time_response(m,rs,5e-4,201,nr=0,rtol=2e-7,atol=2e-10)
    t,x,_,maxf=foundation_oracle(m,rs,5e-4,201,0)
    assert r.metadata['nr_used']==28;assert abs(r.metadata['max_reduced_frequency_hz']-maxf)/maxf<3e-10
    assert np.allclose(r.response,x,rtol=5e-5,atol=5e-9)

def test_runup_modal_truncation_and_dp45_against_independent_dop853():
    m=runup_model();alpha=np.array([.20*2*np.pi,8*np.pi,0.]);r=run_runup(m,alpha,[0,3.0],nr=4,rtol=2e-7,atol=2e-10,max_points=50000)
    x,s,maxf=runup_oracle(m,alpha,r.time_s,4)
    assert r.metadata['nr_used']==4;assert abs(r.metadata['max_reduced_frequency_hz']-maxf)/maxf<3e-10
    assert np.allclose(r.speed_rad_s,s,rtol=0,atol=2e-14)
    assert np.allclose(r.response,x,rtol=5e-5,atol=5e-9)
    assert np.all(np.diff(r.time_s)>0);assert r.time_s[0]==0 and abs(r.time_s[-1]-3.0)<1e-14

def test_runup_rejects_speed_dependent_bearings_like_v2():
    m=runup_model();m.bearings[0]=Bearing(7,1,(900.,.05,.025,55e-6,.02))
    try: run_runup(m,[.1,10,0],[0,1],nr=4)
    except Exception as e: assert 'status=20' in str(e)
    else: assert False
