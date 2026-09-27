"""Independent validation/evidence only. Production integration is exclusively Fortran."""
import argparse,json,sys,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'python/tests_time'))
from time_cases import case,NAMES
from matrix_probe import matrices
from test_matrices import test_elements,test_gradient_nonuniform_signed_and_invalid,test_matrix_authority
from test_time_response import run,RTOL,ATOL,test_ross_time_and_physics,test_force_scaling_and_gyro_ksdt_sentinels,test_dt_convergence,test_mass_policy_and_nonconvergence
from drm_core.solver.backend import FortranBackend

def qualify():
    test_elements();test_gradient_nonuniform_signed_and_invalid();test_force_scaling_and_gyro_ksdt_sentinels();test_mass_policy_and_nonconvergence()
    records={}
    for name in NAMES:
        test_matrix_authority(name);test_ross_time_and_physics(name)
        m,s=case(name);r=run(m,s);ma=matrices(FortranBackend(),m,s)
        with np.load(ROOT/f'validation/ross_parity/time_response/{name}.npz') as g:
            errors={}
            for k,a in ma.items():
                e=g[k]
                if a.ndim==3 and e.ndim==2:e=e[:,:,None]
                if k=='Fg':e=e[:,None]
                errors[k]=float(np.max(abs(a-e)))
            errors['q']=float(np.max(abs(r.displacement-g['q'])))
        records[name]=dict(status='PASS',max_abs_errors=errors,max_scaled_equation_residual=float(max(r.residual[1:])),max_absolute_equation_residual=float(max(r.absolute_residual[1:])),initial_residual=float(r.absolute_residual[0]),max_iterations=int(max(r.iterations)),max_condition_estimate_J=float(max(r.condition_estimate)),samples=len(r.time_s),q_peak=float(np.max(abs(r.displacement))),q_rms=float(np.sqrt(np.mean(r.displacement**2))))
    convergence={}
    for variable in (False,True):
        test_dt_convergence(variable);m,s=case('harmonic');out=[];metrics=[]
        for nt in (321,641,1281):
            t=np.linspace(0,.04,nt);F=np.zeros((16,nt));F[4]=137*np.sin(317*t)
            q=run(m,s,time_s=t,force_real=F,speed=183+900*t/.04 if variable else 183.).displacement
            out.append(q);metrics.append(dict(dt=float(t[1]-t[0]),peak=float(np.max(abs(q))),rms=float(np.sqrt(np.mean(q*q))),selected_q_samples=q[4,::(nt-1)//8].tolist()))
        a,b,c=out[0],out[1][:,::2],out[2][:,::4];e1=float(np.linalg.norm(a-b));e2=float(np.linalg.norm(b-c))
        convergence['variable' if variable else 'constant']=dict(status='PASS',histories=metrics,difference_coarse_medium=e1,difference_medium_fine=e2,ratio=e1/e2)
    return dict(status='PASS',head_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),ross_sha='6320eab9f890f1b3cc1710d508b446fe063ca68d',method='simple Newmark',rtol=RTOL,q_atol_xy_alpha_beta=ATOL.tolist(),cases=records,dt_convergence=convergence,physics=dict(Kst_Kdt_Ksdt='PASS',gradient='PASS',effective_matrices='PASS',equation='PASS',Newmark_identities='PASS',gyro_missing_wrong_double='PASS',Ksdt_omission_vs_zero_legacy_K1='PASS',nonconvergence_fail_closed='PASS',variable_mass_rejection='PASS'),initial_state='q0=v0=a0=0; initial force need not satisfy equilibrium')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);args=p.parse_args();r=qualify();args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print('PASS: 16 ROSS time histories, element/effective matrix parity, native gradient, physics and dt refinement')
