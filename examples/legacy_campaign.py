from __future__ import annotations
from pathlib import Path
import json, numpy as np
from drm_core import (RotorModel,Node,ShaftElement,TaperedShaftElement,Disk,Bearing,Force,BendPoint,
                      run_modal,run_frequency_response,run_auxiliary_frequency_response,run_foundation_frequency_response,
                      run_critical_speeds,run_foundation_time_response,run_runup)
from drm_core.units import rpm_to_rad_s,rad_s_to_rpm
from drm_core.solver.facade import SolverFacade

E_STD=211e9; G_STD=81.2e9; RHO_STD=7810.0

def _out(outdir,name):
    p=Path(outdir)/name.lower();p.mkdir(parents=True,exist_ok=True);return p

def _save_status(p,status,**kw):
    data={'status':status,**kw};(p/'status.json').write_text(json.dumps(data,indent=2,default=lambda x:np.asarray(x).tolist()));return data

def _standard(bearings,forces=None,bend=None,od=.05):
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[ShaftElement(2,i,i+1,od,0.,RHO_STD,E_STD,G_STD,0.) for i in range(1,7)]
    disks=[Disk.geometric(3,RHO_STD,.07,.28,od),Disk.geometric(5,RHO_STD,.07,.35,od)]
    return RotorModel(nodes,shafts,disks,bearings,forces or [],bend or [])

def _modal_sweep(m,rpm,with_kappa=False):
    sp=np.asarray(rpm,float); vals=[]; kappa=[]; ecc=[]
    for x in sp:
        r=run_modal(m,rpm_to_rad_s(x),with_eigenvectors=with_kappa,with_kappa=with_kappa)
        vals.append(r.eigenvalues)
        if with_kappa:kappa.append(r.kappa);ecc.append(r.bearing_eccentricity)
    return np.column_stack(vals), (np.stack(kappa,axis=2) if kappa else None), (np.column_stack(ecc) if ecc else None)

def _plot_modesweep(p,rpm,eig,title='Campbell'):
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,ax=plt.subplots(); n=min(12,eig.shape[0])
    for i in range(0,n,2):ax.plot(rpm,np.abs(eig[i].imag)/(2*np.pi))
    ax.set_xlabel('Rotor speed (rev/min)');ax.set_ylabel('Frequency (Hz)');ax.set_title(title);ax.grid(True);fig.savefig(p/'campbell.png',dpi=120);plt.close(fig)

def _critical_modes(m,crit,method=2,NX=1,damped=True):
    out=[]
    for ic,w in enumerate(crit):
        r=run_modal(m,float(w),with_eigenvectors=True)
        if method==2: idx=min(2*ic,len(r.eigenvalues)-1)
        else:
            est=(np.abs(r.eigenvalues.imag) if damped else np.abs(r.eigenvalues))/max(abs(NX),.2)
            idx=int(np.argmin(np.abs(est-w)))
        out.append(r.eigenvectors[:,idx])
    return np.column_stack(out)

def run_05_08_03(outdir,smoke=True):
    p=_out(outdir,'Example_05_08_03');E=200e9;G=E/(2*(1+.27));rho=7800.;d=0.
    def mk(z,shaft,disc,bear):return RotorModel.from_legacy_arrays([[i+1,x] for i,x in enumerate(z)],shaft,disc,bear)
    m1=mk([0,.2,.4,.6,.8,1,1.2],[[2,i,i+1,.08,.03,rho,E,G,d] for i in range(1,7)],[[1,4,rho,.08,.4,.08]],[[1,1],[1,7]])
    z=[0,.2,.4,.56,.6,.64,.8,1,1.2]; s=[]
    for i in range(1,9):s.append([2,i,i+1,.16 if i in (4,5) else .08,.03,rho,E,G,d])
    m2=mk(z,s,[[1,5,rho,.08,.4,.16]],[[1,1],[1,9]])
    m3=mk(z,s,[[1,4,rho,.02,.4,.16],[1,5,rho,.04,.4,.16],[1,6,rho,.02,.4,.16]],[[1,1],[1,9]])
    z4=[0,.2,.4,.56,.64,.8,1,1.2];s4=[[2,i,i+1,.4 if i==4 else .08,.03,rho,E,G,d] for i in range(1,8)]
    m4=mk(z4,s4,[],[[1,1],[1,8]])
    vals=[]
    for m in (m1,m2,m3,m4):vals.append(np.abs(run_modal(m,rpm_to_rad_s(3000)).eigenvalues[0:16:2])/(2*np.pi))
    a=np.column_stack(vals);np.savetxt(p/'natural_frequencies_hz.csv',a,delimiter=',');return _save_status(p,'PASS_IMPLEMENTED_SCOPE',models=4,max_hz=float(a.max()))

def _run_509(case,outdir,smoke=True):
    p=_out(outdir,f'Example_05_09_{case:02d}')
    if case==1:b=[Bearing(3,1,(1e6,1e6,0,0)),Bearing(3,7,(1e6,1e6,0,0))]
    elif case==2:b=[Bearing(3,1,(1e6,.8e6,0,0)),Bearing(3,7,(1e6,.8e6,0,0))]
    elif case==3:b=[Bearing(3,1,(1e6,.2e6,0,0)),Bearing(3,7,(1e6,.2e6,0,0))]
    elif case==4:b=[Bearing(5,1,(1e6,.5e6,.5e6,1e6,0,0,0,0)),Bearing(5,7,(1e6,.5e6,.5e6,1e6,0,0,0,0))]
    elif case==5:b=[Bearing(3,1,(1e6,1e6,3e3,3e3)),Bearing(3,7,(1e6,1e6,3e3,3e3))]
    elif case==6:b=[Bearing(7,1,(525,.1,.03,1e-4,.1)),Bearing(7,7,(525,.1,.03,1e-4,.1))]
    m=_standard(b);rpm=np.arange(100 if case==6 else 0,4501,500 if smoke else 100,dtype=float);eig,kap,ecc=_modal_sweep(m,rpm,with_kappa=True);np.savez(p/'modal.npz',rpm=rpm,eigenvalues=eig,kappa=kap,eccentricity=ecc);_plot_modesweep(p,rpm,eig)
    r4=run_modal(m,rpm_to_rad_s(4000),with_eigenvectors=True,with_kappa=True);np.savez(p/'modes_4000.npz',eigenvalues=r4.eigenvalues,eigenvectors=r4.eigenvectors,kappa=r4.kappa)
    return _save_status(p,'PASS_IMPLEMENTED_SCOPE',points=len(rpm),fluid=(case==6))

def run_05_09_07(outdir,smoke=True):
    p=_out(outdir,'Example_05_09_07');b=[Bearing(3,1,(1e6,1e6,0,0)),Bearing(3,7,(1e6,1e6,0,0))]
    cases=[(0,0),(1e4,0),(1e5,0),(-1e4,0),(0,5e4),(0,1e5)];rows=[]
    for axial,torque in cases:
        m=_standard(b);m.shafts=[ShaftElement(2,i,i+1,.05,0,RHO_STD,E_STD,G_STD,0,axial,torque) for i in range(1,7)]
        for rpm in (0,4000):rows.append([axial,torque,rpm,*list(np.abs(run_modal(m,rpm_to_rad_s(rpm)).eigenvalues[0:12:2])/(2*np.pi))])
    np.savetxt(p/'cases.csv',np.asarray(rows),delimiter=',');return _save_status(p,'PASS_IMPLEMENTED_SCOPE',cases=len(cases))

def run_05_09_09(outdir,smoke=True):
    p=_out(outdir,'Example_05_09_09');m=_standard([Bearing(3,1,(1e7,1e7,0,0)),Bearing(3,5,(1e7,1e7,0,0))]);m.disks=[Disk.geometric(7,RHO_STD,.07,.35,.05)]
    rpm=np.arange(0,4501,500 if smoke else 100,dtype=float);eig,kap,_=_modal_sweep(m,rpm,True);np.savez(p/'modal.npz',rpm=rpm,eigenvalues=eig,kappa=kap);_plot_modesweep(p,rpm,eig);return _save_status(p,'PASS_IMPLEMENTED_SCOPE',points=len(rpm))

def run_05_09_10(outdir,smoke=True):
    p=_out(outdir,'Example_05_09_10');NEs=range(4,31,6 if smoke else 2);step=[];taper=[];NN=[]
    for NE in NEs:
        NN.append(NE);z=np.linspace(0,1.5,NE+1);nodes=[Node(i+1,float(x)) for i,x in enumerate(z)];disc=[Disk.geometric(int(np.floor(NE/2+1.1)),RHO_STD,.04,.25,0)];bear=[Bearing(3,1,(1e7,1e7,1e3,1e3)),Bearing(3,NE+1,(1e7,1e7,1e3,1e3))]
        diam=.025+.5*(.04-.025)*np.arange(1,2*NE,2)/NE;m=RotorModel(nodes,[ShaftElement(1,i,i+1,float(diam[i-1]),0,RHO_STD,E_STD,G_STD,0) for i in range(1,NE+1)],disc,bear);step.append(np.abs(run_modal(m,rpm_to_rad_s(3000)).eigenvalues[0:12:2])/(2*np.pi))
        dn=np.linspace(.025,.04,NE+1);m=RotorModel(nodes,[TaperedShaftElement(21,i,i+1,float(dn[i-1]),float(dn[i]),0,0,RHO_STD,E_STD,G_STD,0) for i in range(1,NE+1)],disc,bear);taper.append(np.abs(run_modal(m,rpm_to_rad_s(3000)).eigenvalues[0:12:2])/(2*np.pi))
    np.savez(p/'convergence.npz',NE=np.array(NN),step=np.column_stack(step),taper=np.column_stack(taper));return _save_status(p,'PASS_IMPLEMENTED_SCOPE',mesh_sizes=NN)

def run_06_03_01(outdir,smoke=True,case=1):
    p=_out(outdir,'Example_06_03_01');b=[Bearing(3,1,(1e6,1e6,100,100)),Bearing(3,7,(1e6,1e6,100,100))] if case==1 else [Bearing(3,1,(1e6,.8e6,10,10)),Bearing(3,7,(1e6,.8e6,10,10))];m=_standard(b,[Force(1,(3,.001,0))])
    rpm=np.arange(10,4501,100 if smoke else 10,dtype=float);rsp=run_frequency_response(m,rpm_to_rad_s(rpm)).response;np.savez(p/f'response_case{case}.npz',rpm=rpm,response=rsp);return _save_status(p,'PASS_IMPLEMENTED_SCOPE',case=case,points=len(rpm))

def run_06_03_02(outdir,smoke=True,case=1):
    p=_out(outdir,'Example_06_03_02');b=[Bearing(3,1,(1e6,1e6,100,100)),Bearing(3,7,(1e6,1e6,100,100))] if case==1 else [Bearing(3,1,(1e6,.8e6,10,10)),Bearing(3,7,(1e6,.8e6,10,10))]
    if case in (1,2):m=_standard(b,[Force(3,())],[BendPoint(i+1,x) for i,x in enumerate([0,.005,.00866,.01,.00866,.005,0])])
    else:m=_standard(b,[Force(1,(3,.001,0)),Force(1,(5,.001,0))])
    rpm=np.arange(10,4501,100 if smoke else 10,dtype=float);rsp=run_frequency_response(m,rpm_to_rad_s(rpm)).response;np.savez(p/f'response_case{case}.npz',rpm=rpm,response=rsp);return _save_status(p,'PASS_IMPLEMENTED_SCOPE',case=case,points=len(rpm))

def run_06_03_03(outdir,smoke=True,case=1):
    p=_out(outdir,'Example_06_03_03');b=[Bearing(3,1,(1e6,1e6,100,100)),Bearing(3,7,(1e6,1e6,100,100))];f=Force(6,(4,.0001,0)) if case in (1,2) else Force(7,(4,10,0));m=_standard(b,[f]);direction=1 if case==1 else -1
    omrpm=np.arange(0,4501,100 if smoke else 10,dtype=float);rsp=run_auxiliary_frequency_response(m,rpm_to_rad_s(3000),rpm_to_rad_s(omrpm),direction).response;np.savez(p/f'aux_case{case}.npz',omega_rpm=omrpm,response=rsp)
    return _save_status(p,'PASS_IMPLEMENTED_SCOPE',case=case,points=len(omrpm),freq_aux=True)

def run_06_05_01(outdir,smoke=True,case=1):
    p=_out(outdir,'Example_06_05_01');b=[Bearing(3,1,(1e6,1e6,100,100)),Bearing(3,7,(1e6,1e6,100,100))]
    if case==1:
        m=_standard(b,[Force(4,(0,1e-5,0,1e-5))]);hz=np.arange(0,55.001,1 if smoke else .05);rsp=run_foundation_frequency_response(m,rpm_to_rad_s(3000),2*np.pi*hz).response;np.savez(p/'foundation_frequency.npz',hz=hz,response=rsp);return _save_status(p,'PASS_IMPLEMENTED_SCOPE',case=1,freq_fdn=True,phase8=True)
    m=_standard(b,[Force(5,(0,1e-3,0,1e-3,.025))]);rs=rpm_to_rad_s(3000)
    if smoke:
        full=run_foundation_time_response(m,rs,2e-4,5001,nr=0,rtol=1e-5,atol=1e-8)
        red=run_foundation_time_response(m,rs,1e-3,4096,nr=10,rtol=1e-5,atol=1e-8)
    else:
        full=run_foundation_time_response(m,rs,0.00006,65536,nr=0)
        red=run_foundation_time_response(m,rs,0.001,16384,nr=10)
    np.savez(p/'foundation_time_full.npz',time=full.time_s,response=full.response,force=full.forcing)
    np.savez(p/'foundation_time_reduced.npz',time=red.time_s,response=red.response,force=red.forcing)
    return _save_status(p,'PASS_IMPLEMENTED_SCOPE',case=2,time_fdn=True,nr_full=full.metadata['nr_used'],nr_reduced=red.metadata['nr_used'],accepted_full=full.metadata['accepted_steps'],accepted_reduced=red.metadata['accepted_steps'])

def _overhung(case_l=4,case_r=4,damping_factor=0):
    E=211e9;G=E/(2*(1+.3));rho=7810.;cases=np.array([[1e7,1e7,0,0],[1e7,2e7,0,0],[1e7,2e7,6e4,6e4],[1e7,2e7,4e5,4e5],[2e5,4e5,0,0]],float)
    nodes=[Node(i+1,.25*i) for i in range(7)];shafts=[ShaftElement(2,i,i+1,.025,0,rho,E,G,damping_factor) for i in range(1,7)];disks=[Disk.geometric(7,rho,.04,.25,0)];b=[Bearing(3,1,tuple(cases[case_l-1])),Bearing(3,5,tuple(cases[case_r-1]))];return RotorModel(nodes,shafts,disks,b)

def run_06_08_01(outdir,smoke=True,lhcase=4,rhcase=4):
    p=_out(outdir,'Example_06_08_01');m=_overhung(lhcase,rhcase);rpm=np.array([0,1000,2000,3000.]);eig,_k,_e=_modal_sweep(m,rpm);direct=run_critical_speeds(m,NX=1,damped=True,ncrit=10,method=1).critical_speeds_rad_s;it=run_critical_speeds(m,NX=1,damped=True,ncrit=10,max_iterations=20,tol=1e-6,method=2,return_diagnostics=True);modes=_critical_modes(m,it.critical_speeds_rad_s,2);initial=rpm_to_rad_s(np.array([300,400,2000,2500,3000.]));near=run_critical_speeds(m,NX=1,damped=True,ncrit=5,max_iterations=20,tol=1e-6,method=3,initial_estimates=initial,return_diagnostics=True);np.savez(p/f'critical_l{lhcase}_r{rhcase}.npz',rpm=rpm,eigenvalues=eig,direct=direct,iterative=it.critical_speeds_rad_s,mode_shapes=modes,nearest=near.critical_speeds_rad_s);return _save_status(p,'PASS_IMPLEMENTED_SCOPE',lhcase=lhcase,rhcase=rhcase)

def run_06_10_01(outdir,smoke=True):
    p=_out(outdir,'Example_06_10_01');ks=np.logspace(5,7.3,8 if smoke else 60);crit=[];modes=[]
    for kr in ks:
        m=_overhung(1,1);m.bearings[1]=Bearing(3,5,(kr,kr,0,0));r=run_critical_speeds(m,NX=1,damped=True,ncrit=6,max_iterations=20,tol=1e-6,method=2,return_diagnostics=True);crit.append(r.critical_speeds_rad_s);modes.append(_critical_modes(m,r.critical_speeds_rad_s,2))
    np.savez(p/'critical_map.npz',right_bearing_k=ks,critical_rad_s=np.column_stack(crit),mode_shapes=np.stack(modes,axis=2));return _save_status(p,'PASS_IMPLEMENTED_SCOPE',stiffness_points=len(ks))

def run_06_11_01(outdir,smoke=True,case=1):
    p=_out(outdir,'Example_06_11_01');m=_overhung(4,4);m.forces=[Force(1,(7,1e-3,0))];rpm=np.arange(0,3201,400 if smoke else 40,dtype=float);eig,_k,_e=_modal_sweep(m,rpm);np.savez(p/'pre_runup_modal.npz',rpm=rpm,eigenvalues=eig)
    if case==1:alpha=np.array([.05*2*np.pi,8*np.pi,0.]);tspan=[0.,70.]
    else:alpha=np.array([.20*2*np.pi,8*np.pi,0.]);tspan=[0.,20.]
    if smoke:tspan=[0.,min(tspan[1],8.)]
    rr=run_runup(m,alpha,tspan,nr=4,rtol=1e-3,atol=1e-6,max_points=200000)
    np.savez(p/f'runup_case{case}.npz',time=rr.time_s,response=rr.response,speed=rr.speed_rad_s)
    return _save_status(p,'PASS_IMPLEMENTED_SCOPE',case=case,runup=True,points=len(rr.time_s),nr=rr.metadata['nr_used'],accepted=rr.metadata['accepted_steps'],rejected=rr.metadata['rejected_steps'])

def run_07_07_01(outdir,smoke=True,lhcase=1,rhcase=1,id_case=1):
    p=_out(outdir,'Example_07_07_01');cases=np.array([[1e7,1e7,6e4,6e4],[1e7,2e7,0,0],[1e7,2e7,6e4,6e4]],float);m=_overhung(1,1,0 if id_case==1 else 1e-5);m.bearings=[Bearing(3,1,tuple(cases[lhcase-1])),Bearing(3,5,tuple(cases[rhcase-1]))];rpm=np.arange(500,3501,200 if smoke else 40,dtype=float);eig,_k,_e=_modal_sweep(m,rpm);np.savez(p/f'l{lhcase}_r{rhcase}_d{id_case}.npz',rpm=rpm,eigenvalues=eig);return _save_status(p,'PASS_IMPLEMENTED_SCOPE',lhcase=lhcase,rhcase=rhcase,id_case=id_case)

def run_07_09_01(outdir,smoke=True,case=1):
    p=_out(outdir,'Example_07_09_01');rows=[(1e7,-5e6,-5e6,2e7,1e4,0,0,1e4),(1e7,5e6,-5e6,2e7,1e4,0,0,1e4)];m=_overhung(1,1);m.disks=[Disk.geometric(7,RHO_STD,.04,.25,.025)];m.bearings=[Bearing(5,1,rows[case-1]),Bearing(5,5,rows[case-1])];rpm=np.r_[np.arange(0,121,10 if smoke else 1),np.arange(140,3501,200 if smoke else 40)];eig,_k,_e=_modal_sweep(m,rpm);np.savez(p/f'case{case}.npz',rpm=rpm,eigenvalues=eig);return _save_status(p,'PASS_IMPLEMENTED_SCOPE',case=case)

RUNNERS={
'05_08_03':run_05_08_03,'05_09_01':lambda o,s,**k:_run_509(1,o,s),'05_09_02':lambda o,s,**k:_run_509(2,o,s),'05_09_03':lambda o,s,**k:_run_509(3,o,s),'05_09_04':lambda o,s,**k:_run_509(4,o,s),'05_09_05':lambda o,s,**k:_run_509(5,o,s),'05_09_06':lambda o,s,**k:_run_509(6,o,s),'05_09_07':run_05_09_07,'05_09_09':run_05_09_09,'05_09_10':run_05_09_10,
'06_03_01':run_06_03_01,'06_03_02':run_06_03_02,'06_03_03':run_06_03_03,'06_05_01':run_06_05_01,'06_08_01':run_06_08_01,'06_10_01':run_06_10_01,'06_11_01':run_06_11_01,'07_07_01':run_07_07_01,'07_09_01':run_07_09_01}

def run_named(name,outdir='example_campaign_out',smoke=True,**kwargs):return RUNNERS[name](outdir,smoke,**kwargs)
