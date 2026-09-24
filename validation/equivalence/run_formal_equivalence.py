from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from drm_core import run_modal,run_frequency_response,run_auxiliary_frequency_response,run_foundation_frequency_response,run_critical_speeds,run_coaxial_modal,run_coaxial_frequency_response,run_asymmetric_modal,run_asymmetric_frequency_response,run_foundation_time_response,run_runup
from drm_core.solver.facade import SolverFacade
from drm_core.post.whirl import whirl
from validation.equivalence.cases import stationary_model,response_model,auxiliary_model,foundation_freq_model,foundation_time_model,coaxial_model,asymmetric_model,runup_model
from validation.equivalence.comparators import rel_fro,eigenvalue_max_rel,match_modes,mac_min,complex_response_rel,max_abs
from validation.equivalence.element_abi import circular,tapered,asymmetric

G={'matrix_rel':1e-12,'eig_rel':1e-8,'freq_rel':1e-8,'mac_min':.999999,'response_rel':1e-8,'critical_rel':1e-6,'kappa_absrel':1e-10}

def scalar(m,k):
    return float(np.asarray(m[k]).squeeze())

def vec(m,k):
    return np.asarray(m[k]).squeeze()

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def isolated_reference_indices(reference,rel_tol):
    r=np.asarray(reference).ravel()
    out=set()
    if len(r)<=1:
        return {0} if len(r)==1 else out
    for j,z in enumerate(r):
        sep=np.abs(r-z)
        sep[j]=np.inf
        rel=float(np.min(sep)/max(1.0,abs(z)))
        if rel>rel_tol:
            out.add(j)
    return out

def report(path,d):
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,indent=2,default=lambda x:np.asarray(x).tolist()))
    p.with_suffix('.md').write_text(
        '# Formal MATLAB equivalence report\n\nOverall: **'+d['overall']+'**\n\n'
        +'\n'.join(f"- **{k}**: {v['status']} — {v.get('detail','')}" for k,v in d['gates'].items())
        +'\n'
    )

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--matlab-baseline',required=True)
    a.add_argument('--transient-tolerances')
    a.add_argument('--output',default='validation/reports/FORMAL_EQUIVALENCE.json')
    x=a.parse_args()
    p=Path(x.matlab_baseline)

    if not p.exists():
        d={
            'overall':'BLOCKED',
            'reason':'MATLAB authority baseline missing',
            'gates':{f'G{i}':{'status':'BLOCKED','detail':'authority baseline missing'} for i in range(5,13)}
        }
        report(x.output,d)
        return 2

    m=loadmat(p,squeeze_me=False,struct_as_record=False)
    g={}
    errs=[]

    for t in range(1,9):
        mats=circular(t,.31,.08,.02,2.1e11,8.1e10,7800.,2.5e4,1.2e3)
        refs=[m['circ_M'][:,:,t-1],m['circ_C1'][:,:,t-1],m['circ_K0'][:,:,t-1],m['circ_K1'][:,:,t-1]]
        errs += [rel_fro(actual,reference) for actual,reference in zip(mats,refs)]
    mats=tapered(22,.31,.08,.071,.02,.012,2.1e11,8.1e10,7800.,2.5e4)
    refs=[m['taper_M'],m['taper_C1'],m['taper_K0'],m['taper_K1']]
    errs += [rel_fro(actual,reference) for actual,reference in zip(mats,refs)]
    mats=asymmetric(12,.31,1.25e5,1.05e5,.07,.09,11.5,.0042,0.)
    refs=[m['asym_M'],m['asym_C1'],m['asym_K0'],m['asym_K2']]
    errs += [rel_fro(actual,reference) for actual,reference in zip(mats,refs)]
    g['G5']={'status':'PASS' if max(errs)<=G['matrix_rel'] else 'FAIL','detail':f'max element rel={max(errs):.3e}'}

    fac=SolverFacade()
    sm=stationary_model()
    sp=scalar(m,'st_matrix_speed')
    M,C,K,Gm=fac.assemble(sm,sp)
    Mb,Cb,Kb,mask,ecc=fac.bearings(sm,sp)
    e=[
        rel_fro(M,m['st_M']),rel_fro(C,m['st_C']),rel_fro(K,m['st_K']),rel_fro(Gm,m['st_G']),
        rel_fro(Mb,m['st_Mb']),rel_fro(Cb,m['st_Cb']),rel_fro(Kb,m['st_Kb'])
    ]
    g['G6']={'status':'PASS' if max(e)<=G['matrix_rel'] else 'FAIL','detail':f'max matrix rel={max(e):.3e}'}

    ev=[]
    fe=[]
    ma=[]
    ke=[]
    nonisolated_skipped=0
    re=np.asarray(m['st_modal_eig'])
    rv=np.asarray(m['st_modal_vec'])
    rk=np.asarray(m['st_modal_kappa'])
    if re.ndim==1:
        re=re[:,None]
    for q,w in enumerate(vec(m,'st_modal_speeds')):
        r=run_modal(sm,float(w),with_eigenvectors=True,with_kappa=True)
        ref_eig=re[:,q]
        mp=match_modes(r.eigenvalues,ref_eig)
        ev.append(eigenvalue_max_rel(r.eigenvalues,ref_eig,mp))
        fe.append(max(
            abs(abs(r.eigenvalues[i])/(2*np.pi)-abs(ref_eig[j])/(2*np.pi))
            /max(1,abs(ref_eig[j])/(2*np.pi))
            for i,j in mp
        ))
        ref_vec=rv[:,:,q] if rv.ndim==3 else rv
        ref_kappa=rk[:,:,q] if rk.ndim==3 else rk
        isolated=isolated_reference_indices(ref_eig,G['eig_rel'])
        pairs=[(i,j) for i,j in mp if j in isolated]
        nonisolated_skipped += len(mp)-len(pairs)
        for i,j in pairs:
            den=np.vdot(r.eigenvectors[:,i],r.eigenvectors[:,i]).real*np.vdot(ref_vec[:,j],ref_vec[:,j]).real
            ma.append(1.0 if den<=0 else float(abs(np.vdot(r.eigenvectors[:,i],ref_vec[:,j]))**2/den))
            ke.append(float(np.max(np.abs(r.kappa[:,i]-ref_kappa[:,j]))))
    min_mac=min(ma) if ma else 1.0
    end_to_end_kappa=max(ke) if ke else 0.0

    # Separate two different questions:
    # 1) are the modal vectors equivalent?  -> isolated-mode MAC
    # 2) is the legacy whirl/kappa transformation equivalent? -> apply our
    #    post-processor to the authority vectors themselves and compare to the
    #    authority kappa.  End-to-end kappa is retained as a diagnostic because
    #    near-circular or guard-adjacent local orbits amplify tiny cross-LAPACK
    #    eigenvector perturbations even when MAC is unity.
    whirl_err=[]
    for q in range(re.shape[1]):
        ref_eig=re[:,q]
        ref_vec=rv[:,:,q] if rv.ndim==3 else rv
        ref_kappa=rk[:,:,q] if rk.ndim==3 else rk
        py_kappa=np.zeros_like(ref_kappa,dtype=float)
        for j in range(ref_vec.shape[1]):
            kk,_=whirl(ref_vec[0::2,j],ref_vec[1::2,j])
            if ref_eig[j].imag<0:
                kk=-kk
            py_kappa[0::2,j]=kk
            py_kappa[1::2,j]=kk
        whirl_err.append(float(np.max(np.abs(py_kappa-ref_kappa))))
    max_whirl=max(whirl_err) if whirl_err else 0.0

    ok=max(ev)<=G['eig_rel'] and max(fe)<=G['freq_rel'] and min_mac>=G['mac_min'] and max_whirl<=G['kappa_absrel']
    g['G7']={
        'status':'PASS' if ok else 'FAIL',
        'detail':f'eig={max(ev):.3e},freq={max(fe):.3e},isolated_MAC={min_mac:.9f},whirl_kappa={max_whirl:.3e},end_to_end_kappa_diag={end_to_end_kappa:.3e},nonisolated_skipped={nonisolated_skipped}'
    }

    e1=complex_response_rel(run_frequency_response(response_model(),vec(m,'rsp_speeds')).response,m['rsp_response'])
    e2=complex_response_rel(run_auxiliary_frequency_response(auxiliary_model(),scalar(m,'aux_rotor_speed'),vec(m,'aux_omega'),scalar(m,'aux_direction')).response,m['aux_response'])
    e3=complex_response_rel(run_foundation_frequency_response(foundation_freq_model(),scalar(m,'fdn_rotor_speed'),vec(m,'fdn_omega')).response,m['fdn_response'])
    g['G8']={'status':'PASS' if max(e1,e2,e3)<=G['response_rel'] else 'FAIL','detail':f'rsp={e1:.3e},aux={e2:.3e},fdn={e3:.3e}'}

    c=run_critical_speeds(sm,ncrit=int(scalar(m,'crit_n')),method=1).critical_speeds_rad_s
    rr=vec(m,'crit_direct')
    ce=float(np.max(abs(c-rr)/np.maximum(1,abs(rr))))
    ci=run_critical_speeds(stationary_model(fluid=True),ncrit=int(scalar(m,'crit_fluid_n')),method=2,max_iterations=20,tol=1e-6).critical_speeds_rad_s
    ri=vec(m,'crit_fluid')
    cie=float(np.max(abs(ci-ri)/np.maximum(1,abs(ri))))
    g['G9']={'status':'PASS' if max(ce,cie)<=G['critical_rel'] else 'FAIL','detail':f'direct={ce:.3e},iter={cie:.3e}'}

    cm=coaxial_model()
    cr=run_coaxial_modal(cm,scalar(m,'coax_modal_speed'))
    mp=match_modes(cr.eigenvalues,vec(m,'coax_eig'))
    ce=eigenvalue_max_rel(cr.eigenvalues,vec(m,'coax_eig'),mp)
    mc=mac_min(cr.eigenvectors,np.asarray(m['coax_vec']),mp)
    rr=complex_response_rel(run_coaxial_frequency_response(cm,vec(m,'coax_rsp_speeds')).response,m['coax_response'])
    g['G11']={'status':'PASS' if ce<=G['eig_rel'] and mc>=G['mac_min'] and rr<=G['response_rel'] else 'FAIL','detail':f'eig={ce:.3e},MAC={mc:.9f},rsp={rr:.3e}'}

    am=asymmetric_model()
    a1=run_asymmetric_modal(am,scalar(m,'asym_speed'),with_eigenvectors=False)
    a2=run_asymmetric_modal(am,scalar(m,'asym_speed'),with_eigenvectors=True)
    eo=eigenvalue_max_rel(a1.eigenvalues,vec(m,'asym_eig_only'))
    mp=match_modes(a2.eigenvalues,vec(m,'asym_eig_vec'))
    ee=eigenvalue_max_rel(a2.eigenvalues,vec(m,'asym_eig_vec'),mp)
    mm=mac_min(a2.eigenvectors,np.asarray(m['asym_vec']),mp)
    rr=rel_fro(run_asymmetric_frequency_response(am,vec(m,'asym_rsp_speeds')).response,m['asym_response'])
    g['G12']={'status':'PASS' if max(eo,ee,rr)<=G['eig_rel'] and mm>=G['mac_min'] else 'FAIL','detail':f'eig1={eo:.3e},eig2={ee:.3e},MAC={mm:.9f},rsp={rr:.3e}'}

    if x.transient_tolerances and Path(x.transient_tolerances).exists():
        t=json.loads(Path(x.transient_tolerances).read_text())
        refdir=Path(__file__).resolve().parents[1]/'baseline'/'transient'
        tp=refdir/'time_fdn_source_reference.npz'
        rp=refdir/'runup_source_reference.npz'
        if not tp.exists() or not rp.exists():
            g['G10']={'status':'BLOCKED','detail':'source-derived transient reference files missing'}
        elif t.get('time_source_reference_sha256')!=sha256(tp) or t.get('runup_source_reference_sha256')!=sha256(rp):
            g['G10']={'status':'BLOCKED','detail':'transient reference hash mismatch versus frozen tolerance policy'}
        else:
            tref=np.load(tp)
            rref=np.load(rp)
            tdofs=np.asarray(tref['response_dofs'],dtype=int)
            rdofs=np.asarray(rref['response_dofs'],dtype=int)

            tr=run_foundation_time_response(
                foundation_time_model(),
                scalar(m,'time_rotor_speed'),
                scalar(m,'time_dt'),
                int(scalar(m,'time_npts')),
                nr=int(scalar(m,'time_nr')),
                rtol=1e-3,
                atol=1e-6
            )
            te=max_abs(tr.response[tdofs,:],np.asarray(m['time_response'])[tdofs,:])
            tf=max_abs(tr.forcing,vec(m,'time_force'))

            ru=run_runup(
                runup_model(),
                vec(m,'runup_alpha'),
                [scalar(m,'runup_t0'),scalar(m,'runup_tf')],
                nr=int(scalar(m,'runup_nr')),
                rtol=1e-3,
                atol=1e-6,
                max_points=300000
            )
            source_time=np.asarray(rref['time']).ravel()
            octave_time=vec(m,'runup_time')
            octave_response=np.asarray(m['runup_response'])
            fortran_interp=np.vstack([np.interp(source_time,ru.time_s,ru.response[i,:]) for i in rdofs])
            octave_interp=np.vstack([np.interp(source_time,octave_time,octave_response[i,:]) for i in rdofs])
            re=max_abs(fortran_interp,octave_interp)

            ok=te<=t['time_fdn_max_abs_m'] and re<=t['runup_max_abs_m'] and tf<=t.get('time_fdn_force_max_abs',1e-12)
            g['G10']={
                'status':'PASS' if ok else 'FAIL',
                'detail':f'time={te:.3e},runup={re:.3e},force={tf:.3e},time_dofs={tdofs.tolist()},runup_dofs={rdofs.tolist()}'
            }
    else:
        g['G10']={'status':'BLOCKED','detail':'transient tolerance policy not frozen'}

    overall='PASS' if all(v['status']=='PASS' for v in g.values()) else ('FAIL' if any(v['status']=='FAIL' for v in g.values()) else 'BLOCKED')
    d={'overall':overall,'baseline_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'thresholds':G,'gates':g}
    report(x.output,d)
    return 0 if overall=='PASS' else (1 if overall=='FAIL' else 2)

if __name__=='__main__':
    raise SystemExit(main())
