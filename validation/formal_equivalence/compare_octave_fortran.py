from __future__ import annotations
import argparse,json,os,sys
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from scipy.optimize import linear_sum_assignment

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"python"/"src"))
from drm_core import (RotorModel,Node,ShaftElement,TaperedShaftElement,AsymmetricShaftElement,Disk,Bearing,Force,RotorDefinition,
    run_modal,run_frequency_response,run_auxiliary_frequency_response,run_foundation_frequency_response,
    run_critical_speeds,run_coaxial_modal,run_coaxial_frequency_response,
    run_asymmetric_modal,run_asymmetric_frequency_response,run_foundation_time_response,run_runup)
from drm_core.solver.backend import FortranBackend
from drm_core.post.whirl import whirl

ELEMENT_REL=1e-12;GLOBAL_REL=1e-12;EIG_REL=1e-8;MAC_MIN=.999999
RESPONSE_REL=1e-8;CRITICAL_REL=1e-6;KAPPA_TOL=1e-10

def rel(a,b):
    a=np.asarray(a);b=np.asarray(b);return float(np.linalg.norm((a-b).ravel())/max(np.linalg.norm(b.ravel()),1e-300))
def max_abs(a,b):return float(np.max(np.abs(np.asarray(a)-np.asarray(b))))
def eig_match(ref,got):
    ref=np.asarray(ref).reshape(-1);got=np.asarray(got).reshape(-1)
    cost=np.abs(got[:,None]-ref[None,:])/np.maximum(1.,np.abs(ref)[None,:])
    r,c=linear_sum_assignment(cost);order=np.empty(len(ref),int);order[c]=r
    return got[order],order,float(cost[r,c].max())
def mac(a,b):
    a=np.asarray(a).reshape(-1);b=np.asarray(b).reshape(-1)
    den=np.vdot(a,a).real*np.vdot(b,b).real
    return float(abs(np.vdot(a,b))**2/den) if den else 1.
def standard_model():
    E=211e9;G=81.2e9;rho=7810.;nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[ShaftElement(2,i,i+1,.05,0,rho,E,G,0) for i in range(1,7)]
    disks=[Disk.geometric(3,rho,.07,.28,.05),Disk.geometric(5,rho,.07,.35,.05)]
    return RotorModel(nodes,shafts,disks,[Bearing(3,1,(1e6,1e6,100.,100.)),Bearing(3,7,(1e6,1e6,100.,100.))])
def fluid_model():
    m=standard_model();m.bearings=[Bearing(7,1,(525.,.1,.03,1e-4,.1,0.)),Bearing(7,7,(525.,.1,.03,1e-4,.1,0.))];return m
def coaxial_model():
    E=2.07e11;G=E/(2*(1+.3));rho=8300.;z=[0,.076,.159,.254,.324,.406,.457,.508,.152,.203,.279,.356,.406]
    nodes=[Node(i+1,x) for i,x in enumerate(z)];shafts=[]
    for i in range(1,8):shafts.append(ShaftElement(2,i,i+1,.030,0,rho,E,G,0))
    for i in range(9,13):shafts.append(ShaftElement(2,i,i+1,.060,.050,rho,E,G,0))
    disks=[Disk.inertial(2,10.5,.043,.086),Disk.inertial(7,7,.034,.068),Disk.inertial(10,7,.021,.042),Disk.inertial(12,3.5,.013,.026)]
    bears=[Bearing(3,1,(26e6,52e6,20,20)),Bearing(3,8,(18e6,36e6,20,20)),Bearing(3,9,(18e6,36e6,20,20)),Bearing(20,6,(13,9e6,9e6,20,20))]
    return RotorModel(nodes,shafts,disks,bears,rotors=[RotorDefinition(1,8,1),RotorDefinition(9,13,1.5)])
def asym_model():
    E=211e9;rho=7810.;A=.002;Ix=4.2043e-7;Iy=2.4112e-7;rhoA=rho*A;rhoI=rho*(Ix+Iy)/2
    nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[AsymmetricShaftElement(11,i,i+1,E*Ix,E*Iy,0,0,rhoA,rhoI,0) for i in range(1,7)]
    od=2*np.sqrt(A/np.pi);disks=[Disk.geometric(3,rho,.07,.28,od),Disk.geometric(5,rho,.07,.35,od)]
    bears=[Bearing(3,1,(1e6,1e6,5e3,5e3)),Bearing(3,7,(1e6,1e6,5e3,5e3))]
    return RotorModel(nodes,shafts,disks,bears)
def runup_model():
    E=211e9;G=E/(2*(1+.3));rho=7810.;nodes=[Node(i+1,.25*i) for i in range(7)]
    shafts=[ShaftElement(2,i,i+1,.025,0,rho,E,G,0) for i in range(1,7)]
    return RotorModel(nodes,shafts,[Disk.geometric(7,rho,.04,.25,0)],[Bearing(3,1,(1e7,2e7,4e5,4e5)),Bearing(3,5,(1e7,2e7,4e5,4e5))],[Force(1,(7,1e-3,0))])

class Q:
    def __init__(self):self.rows=[]
    def add(self,gate,name,value,limit,passed):
        self.rows.append(dict(gate=gate,name=name,value=float(value),limit=limit,passed=bool(passed)))
    def gate(self,g):return all(r["passed"] for r in self.rows if r["gate"]==g)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--baseline",required=True);ap.add_argument("--report-dir",required=True)
    ap.add_argument("--measure-transient",action="store_true");ap.add_argument("--transient-thresholds");a=ap.parse_args()
    mat=loadmat(a.baseline,squeeze_me=True,struct_as_record=False);q=Q();b=FortranBackend(os.environ["DRMROTOR_LIB"])
    checks=np.asarray(mat["semantic_checks"]).reshape(-1)
    q.add("G0","ode45_available",checks[6],1,checks[6]==1);q.add("G0","roots_available",checks[7],1,checks[7]==1)
    q.add("G0","basic_semantics_max_error",np.max(checks[:6]),1e-12,np.max(checks[:6])<=1e-12)

    E=2.07e11;G=7.95e10;rho=7830.;L=.23;do=.067;di=.013;axial=12000.;torque=350.
    for t in range(1,9):
        m=RotorModel([Node(1,0),Node(2,L)],[ShaftElement(t,1,2,do,di,rho,E,G,1.,axial,torque)],[],[])
        M,C0,K0,C1=b.assemble_matrices(m,0.);_,_,Kp,_=b.assemble_matrices(m,1.);K1=Kp-K0
        for n,x,key in [("M",M,"elem_circular_M"),("C1",C1,"elem_circular_C1"),("K0",K0,"elem_circular_K0"),("K1",K1,"elem_circular_K1")]:
            v=rel(x,mat[key][:,:,t-1]);q.add("G5",f"circular_t{t}_{n}",v,ELEMENT_REL,v<=ELEMENT_REL)
    Lt=.31;doj=.080;dok=.065;dij=.020;dik=.014;axial_t=8000.
    for k,t in enumerate(range(21,29)):
        m=RotorModel([Node(1,0),Node(2,Lt)],[TaperedShaftElement(t,1,2,doj,dok,dij,dik,rho,E,G,axial_t)],[],[])
        M,C0,K0,C1=b.assemble_matrices(m,0.);_,_,Kp,_=b.assemble_matrices(m,1.);K1=Kp-K0
        for n,x,key in [("M",M,"elem_taper_M"),("C1",C1,"elem_taper_C1"),("K0",K0,"elem_taper_K0"),("K1",K1,"elem_taper_K1")]:
            v=rel(x,mat[key][:,:,k]);q.add("G5",f"taper_t{t}_{n}",v,ELEMENT_REL,v<=ELEMENT_REL)
    EIx=1.31e5;EIy=1.07e5;Phix=.08;Phiy=.11;rhoA=12.2;rhoI=.0046
    for k,t in enumerate(range(11,19)):
        m=RotorModel([Node(1,0),Node(2,L)],[AsymmetricShaftElement(t,1,2,EIx,EIy,Phix,Phiy,rhoA,rhoI,0,0)],[],[])
        M,C0,C1,K0,K1,K2=b.asymmetric_assemble(m)
        for n,x,key in [("M",M,"elem_asym_M"),("C1",C1,"elem_asym_C1"),("K0",K0,"elem_asym_K0"),("K2",K2,"elem_asym_K2")]:
            v=rel(x,mat[key][:,:,k]);q.add("G5",f"asym_t{t}_{n}",v,ELEMENT_REL,v<=ELEMENT_REL)

    nodes=[Node(1,0),Node(2,.20),Node(3,.45),Node(4,.75)]
    shafts=[ShaftElement(2,1,2,.060,.010,rho,E,G,2e-5,5000,120),TaperedShaftElement(22,2,3,.060,.052,.010,.006,rho,E,G,3000),ShaftElement(2,3,4,.052,.006,rho,E,G,1e-5,-2000,-80)]
    gm=RotorModel(nodes,shafts,[Disk.geometric(2,rho,.04,.22,.06),Disk.inertial(3,7.5,.025,.047)],[])
    M,C0,K0,C1=b.assemble_matrices(gm,0.);_,_,Kp,_=b.assemble_matrices(gm,1.);K1=Kp-K0
    for n,x,key in [("M0",M,"global_M0"),("C0",C0,"global_C0"),("C1",C1,"global_C1"),("K0",K0,"global_K0"),("K1",K1,"global_K1")]:
        v=rel(x,mat[key]);q.add("G6",f"global_{n}",v,GLOBAL_REL,v<=GLOBAL_REL)

    nodes=[Node(i+1,float(i)) for i in range(8)]
    bears=[Bearing(1,1),Bearing(2,2),Bearing(3,3,(11e6,12e6,101,102)),Bearing(4,4,(21e6,22e6,31e3,32e3,201,202,301,302)),Bearing(5,5,(41e6,4.2e6,-4.3e6,44e6,401,402,-403,404)),Bearing(6,6,tuple(np.r_[np.arange(1,17)*1e5,np.arange(101,117)*10])),Bearing(7,7,(1200,.06,.025,60e-6,.018,0)),Bearing(8,8,(2.1e5,.04,.08,.00025,12,.08))]
    bm=RotorModel(nodes,[],[],bears);Mb,Cb,Kb,mask,ecc=b.bearings_matrices(bm,320.)
    for n,x,key in [("M",Mb,"bear_M"),("C",Cb,"bear_C"),("K",Kb,"bear_K")]:
        v=rel(x,mat[key]);q.add("G6",f"bearing_{n}",v,GLOBAL_REL,v<=GLOBAL_REL)
    v=max_abs(mask.astype(float),np.asarray(mat["bear_zero_mask"]).reshape(-1));q.add("G6","bearing_zero_mask_abs",v,0,v==0)
    v=max_abs(ecc,np.asarray(mat["bear_ecc"]).reshape(-1));q.add("G6","bearing_ecc_abs",v,1e-10,v<=1e-10)

    sm=standard_model();rm=run_modal(sm,float(mat["modal_speed"]),with_eigenvectors=True,with_kappa=True)
    eref=np.asarray(mat["modal_eig"]).reshape(-1);_,order,v=eig_match(eref,rm.eigenvalues);q.add("G7","stationary_eigenvalues_max_rel",v,EIG_REL,v<=EIG_REL)
    vref=np.asarray(mat["modal_vec"]);vgot=rm.eigenvectors[:,order];macs=np.array([mac(vref[:,i],vgot[:,i]) for i in range(vref.shape[1])]);q.add("G7","stationary_MAC_min",macs.min(),MAC_MIN,macs.min()>=MAC_MIN)
    # Qualify the legacy whirl/kappa transformation on the same V2 eigenvectors.
    # End-to-end kappa is additionally recorded, but near-circular orbits are
    # ill-conditioned with respect to tiny cross-LAPACK eigenvector perturbations.
    ref_kappa=np.asarray(mat["modal_kappa"]);py_kappa=np.zeros_like(ref_kappa,dtype=float)
    for jj in range(vref.shape[1]):
        kk,_=whirl(vref[0::2,jj],vref[1::2,jj])
        if eref[jj].imag<0: kk=-kk
        py_kappa[0::2,jj]=kk;py_kappa[1::2,jj]=kk
    v=max_abs(py_kappa,ref_kappa);q.add("G7","whirl_algorithm_kappa_max_abs",v,KAPPA_TOL,v<=KAPPA_TOL)
    v=max_abs(rm.kappa[:,order],ref_kappa);q.add("G7","stationary_kappa_end_to_end_max_abs",v,None,True)
    v=max_abs(rm.bearing_eccentricity,np.asarray(mat["modal_ecc"]).reshape(-1));q.add("G7","stationary_ecc_max_abs",v,1e-12,v<=1e-12)
    fm=fluid_model();rf=run_modal(fm,float(mat["fluid_modal_speed"]),with_eigenvectors=True,with_kappa=True);_,_,v=eig_match(np.asarray(mat["fluid_modal_eig"]).reshape(-1),rf.eigenvalues);q.add("G7","fluid_eigenvalues_max_rel",v,EIG_REL,v<=EIG_REL)
    v=max_abs(rf.bearing_eccentricity,np.asarray(mat["fluid_modal_ecc"]).reshape(-1));q.add("G7","fluid_ecc_max_abs",v,1e-10,v<=1e-10)

    fr=standard_model();fr.forces=[Force(1,(3,1.7e-4,.31)),Force(2,(5,2.4e-5,-.22))]
    v=rel(run_frequency_response(fr,np.asarray(mat["fr_speeds"]).reshape(-1)).response,mat["fr_rsp"]);q.add("G8","freq_rsp_rel",v,RESPONSE_REL,v<=RESPONSE_REL)
    aux=standard_model();aux.forces=[Force(6,(4,1e-4,.27))]
    v=rel(run_auxiliary_frequency_response(aux,float(mat["aux_rotor_speed"]),np.asarray(mat["aux_omega"]).reshape(-1),1).response,mat["aux_rsp"]);q.add("G8","freq_aux_rel",v,RESPONSE_REL,v<=RESPONSE_REL)
    fdn=standard_model();fdn.forces=[Force(4,(0,1e-5,0,1.5e-5))]
    v=rel(run_foundation_frequency_response(fdn,float(mat["fdn_rotor_speed"]),np.asarray(mat["fdn_omega"]).reshape(-1)).response,mat["fdn_rsp"]);q.add("G8","freq_fdn_rel",v,RESPONSE_REL,v<=RESPONSE_REL)

    cd=run_critical_speeds(sm,ncrit=4,NX=1,damped=True,method=1).critical_speeds_rad_s
    v=rel(cd,np.asarray(mat["crit_direct"]).reshape(-1));q.add("G9","critical_direct_rel",v,CRITICAL_REL,v<=CRITICAL_REL)
    ci=run_critical_speeds(fm,ncrit=2,NX=1,damped=True,max_iterations=30,tol=1e-8,method=2,with_mode_shapes=True)
    v=rel(ci.critical_speeds_rad_s,np.asarray(mat["crit_iter"]).reshape(-1));q.add("G9","critical_iter_rel",v,CRITICAL_REL,v<=CRITICAL_REL)
    vm=np.asarray(mat["crit_iter_modes"]);macs=np.array([mac(vm[:,i],ci.mode_shapes[:,i]) for i in range(vm.shape[1])]);q.add("G9","critical_iter_MAC_min",macs.min(),MAC_MIN,macs.min()>=MAC_MIN)
    ci3=run_critical_speeds(sm,ncrit=2,NX=1,damped=True,max_iterations=30,tol=1e-9,method=3,initial_estimates=np.array([80.,350.])).critical_speeds_rad_s
    v=rel(ci3,np.asarray(mat["crit_initial"]).reshape(-1));q.add("G9","critical_initial_rel",v,CRITICAL_REL,v<=CRITICAL_REL)

    cm=coaxial_model();rc=run_coaxial_modal(cm,float(mat["coax_speed"]));eref=np.asarray(mat["coax_eig"]).reshape(-1);_,order,v=eig_match(eref,rc.eigenvalues);q.add("G11","coax_eigenvalues_max_rel",v,EIG_REL,v<=EIG_REL)
    vv=np.asarray(mat["coax_vec"]);macs=np.array([mac(vv[:,i],rc.eigenvectors[:,order[i]]) for i in range(len(eref))]);q.add("G11","coax_MAC_min",macs.min(),MAC_MIN,macs.min()>=MAC_MIN)
    cm.forces=[Force(1,(2,1e-4,0))];v=rel(run_coaxial_frequency_response(cm,np.asarray(mat["coax_rsp_speeds"]).reshape(-1)).response,mat["coax_rsp"]);q.add("G11","coax_response_rel",v,RESPONSE_REL,v<=RESPONSE_REL)

    am=asym_model();ra=run_asymmetric_modal(am,float(mat["asym_speed"]),with_eigenvectors=False);_,_,v=eig_match(np.asarray(mat["asym_eig_only"]).reshape(-1),ra.eigenvalues);q.add("G12","asym_eig_only_max_rel",v,EIG_REL,v<=EIG_REL)
    rav=run_asymmetric_modal(am,float(mat["asym_speed"]),with_eigenvectors=True);_,order,v=eig_match(np.asarray(mat["asym_eig_vec"]).reshape(-1),rav.eigenvalues);q.add("G12","asym_eig_vectors_path_max_rel",v,EIG_REL,v<=EIG_REL)
    vv=np.asarray(mat["asym_vec"]);macs=np.array([mac(vv[:,i],rav.eigenvectors[:,order[i]]) for i in range(len(order))]);q.add("G12","asym_MAC_min",macs.min(),MAC_MIN,macs.min()>=MAC_MIN)
    aa=b.asymmetric_assemble(am)
    for x,key in zip(aa,["asym_M0","asym_C0","asym_C1","asym_K0","asym_K1","asym_K2"]):
        v=rel(x,mat[key]);q.add("G12",f"{key}_rel",v,GLOBAL_REL,v<=GLOBAL_REL)
    Cb,Kb,K1b,mask=b.asymmetric_bearings(am)
    for x,key in [(Cb,"asym_Cb"),(Kb,"asym_Kb"),(K1b,"asym_K1b")]:
        v=rel(x,mat[key]);q.add("G12",f"{key}_rel",v,GLOBAL_REL,v<=GLOBAL_REL)
    am.forces=[Force(1,(3,.001,np.pi/6))]
    v=rel(run_asymmetric_frequency_response(am,np.asarray(mat["asym_rsp_speeds"]).reshape(-1)).response,mat["asym_rsp"]);q.add("G12","asym_response_rel",v,RESPONSE_REL,v<=RESPONSE_REL)

    tm=standard_model();tm.forces=[Force(5,(0,1e-3,0,1e-3,.025))]
    tr=run_foundation_time_response(tm,float(mat["transient_rotor_speed"]),float(mat["transient_dt"]),int(mat["transient_npts"]),nr=int(mat["transient_nr"]),rtol=1e-3,atol=1e-6)
    ref=np.asarray(mat["time_fdn_rsp"]);peak=max(np.max(np.abs(ref)),1e-300);mx=max_abs(tr.response,ref);rms=float(np.sqrt(np.mean(np.abs(tr.response-ref)**2)))
    q.add("G10","time_fdn_max_abs_over_ref_peak",mx/peak,None,True);q.add("G10","time_fdn_rms_over_ref_peak",rms/peak,None,True)
    q.add("G10","time_fdn_force_max_abs",max_abs(tr.forcing,np.asarray(mat["time_fdn_force"]).reshape(-1)),None,True)
    rum=runup_model();alpha=np.asarray(mat["runup_alpha"]).reshape(-1)
    rr=run_runup(rum,alpha,np.asarray(mat["runup_tspan"]).reshape(-1),nr=int(mat["runup_nr"]),rtol=1e-3,atol=1e-6,max_points=200000)
    tref=np.asarray(mat["runup_time"]).reshape(-1);rref=np.asarray(mat["runup_rsp"]);interp=np.vstack([np.interp(tref,rr.time_s,rr.response[i,:]) for i in range(rr.response.shape[0])])
    peak=max(np.max(np.abs(rref)),1e-300);mx=max_abs(interp,rref);rms=float(np.sqrt(np.mean((interp-rref)**2)))
    q.add("G10","runup_max_abs_over_ref_peak",mx/peak,None,True);q.add("G10","runup_rms_over_ref_peak",rms/peak,None,True)
    q.add("G10","runup_speed_max_abs",max_abs(np.interp(tref,rr.time_s,rr.speed_rad_s),np.asarray(mat["runup_speed"]).reshape(-1)),None,True)
    if not a.measure_transient:
        th=json.loads(Path(a.transient_thresholds).read_text())
        for row in q.rows:
            if row["gate"]=="G10":row["limit"]=th[row["name"]];row["passed"]=row["value"]<=row["limit"]

    out=Path(a.report_dir);out.mkdir(parents=True,exist_ok=True);engine=str(mat.get("engine_name","")).strip()
    gates={g:q.gate(g) for g in sorted(set(r["gate"] for r in q.rows))}
    report={"engine":engine,"baseline":str(a.baseline),"measure_transient":a.measure_transient,"gates":gates,"metrics":q.rows}
    (out/"formal_equivalence.json").write_text(json.dumps(report,indent=2))
    lines=["# Formal equivalence report","",f"Engine: {engine}","",'| Gate | Metric | Value | Limit | PASS |','|---|---|---:|---:|:---:|']
    for r in q.rows:lines.append(f"| {r['gate']} | {r['name']} | {r['value']:.12e} | {'' if r['limit'] is None else r['limit']} | {'PASS' if r['passed'] else 'FAIL'} |")
    lines+=["","## Gate summary",""]+[f"- {g}: {'PASS' if v else 'FAIL'}" for g,v in gates.items()]
    (out/"formal_equivalence.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({"engine":engine,"gates":gates,"transient":[r for r in q.rows if r["gate"]=="G10"]},indent=2))
    hard=[r for r in q.rows if r["gate"]!="G10" and not r["passed"]]
    if not a.measure_transient:hard += [r for r in q.rows if r["gate"]=="G10" and not r["passed"]]
    raise SystemExit(1 if hard else 0)
if __name__=="__main__":main()
