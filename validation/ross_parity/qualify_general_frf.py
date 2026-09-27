"""Validation only: full-entry errors, conditioning and independent identities."""
import sys,json,argparse
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'python/tests_frf'))
from cases import case,NAMES
from drm_core import AnalysisService,AnalysisCase
from drm_core.solver.backend import FortranBackend
from drm_core.solver.general_frf_backend import matrices

def qualify(out):
    rows=[];physics=[]
    for name in NAMES:
        m,s=case(name);v=AnalysisService().execute(m,AnalysisCase('general_frf',dict(frequency_rad_s=s['frequencies'],speed=s['speed'],free_free=s['free_free']))).result
        with np.load(ROOT/f'validation/ross_parity/frf/{name}.npz') as r:
            for i,(w,omega) in enumerate(zip(v.frequency_rad_s,v.rotor_speed_rad_s)):
                native=matrices(FortranBackend(),m,w,omega)
                for k in ['H_disp','H_vel','H_acc']:native[k]=getattr(v,k)[:,:,i]
                for k,a in native.items():
                    atol={'H_disp':1e-13,'H_vel':1e-10,'H_acc':1e-7,'D':1e-7,'K':1e-7,'Kb':1e-7}.get(k,1e-11);rtol=1e-9 if k.startswith('H_') else 2e-12
                    for part in (['real','imag'] if np.iscomplexobj(a) else ['real']):
                        x=getattr(a,part);y=getattr(r[k][:,:,i],part);err=abs(x-y);idx=np.unravel_index(err.argmax(),err.shape)
                        np.testing.assert_allclose(x,y,rtol=rtol,atol=atol)
                        rows.append(dict(case=name,omega=float(omega),frequency=float(w),quantity=k+'.'+part,ross=float(y[idx]),fortran=float(x[idx]),max_abs_error=float(err.max()),max_relative_error=float((err/np.maximum(abs(y),atol)).max()),rtol=rtol,atol=atol,status='PASS'))
                D=native['D'];H=native['H_disp'];identity=np.eye(len(D));res=float(np.linalg.norm(D@H-identity,np.inf)/(np.linalg.norm(D,np.inf)*np.linalg.norm(H,np.inf)+1))
                hv=float(np.max(abs(native['H_vel']-1j*w*H)));ha=float(np.max(abs(native['H_acc']+w*w*H)))
                assert res<1e-12 and hv<1e-12 and ha<1e-12
                # Phase is meaningful only for components above the displacement absolute floor.
                ref=r['H_disp'][:,:,i];mask=abs(ref)>1e-11
                phase=float(np.max(abs(np.angle(H[mask]/ref[mask])))) if np.any(mask) else 0.
                magnitude=float(np.max(abs(abs(H)-abs(ref))))
                assert phase<1e-8
                np.testing.assert_allclose(abs(H),abs(ref),rtol=1e-9,atol=1e-13)
                physics.append(dict(case=name,frequency=float(w),rotor_speed=float(omega),condition_D=float(np.linalg.cond(D)),DH_scaled_residual=res,velocity_identity=hv,acceleration_identity=ha,phase_error_rad=phase,magnitude_error=magnitude))
    # Deliberate near-resonance validation from frozen primitive matrices.
    # This independent Python solve is validation only and cannot enter production.
    from scipy.linalg import eigh
    m,_=case('synchronous');resonance=[]
    with np.load(ROOT/'validation/ross_parity/frf/synchronous.npz') as r:
        M,C,G,K=[r[k][:,:,0] for k in ['M','C','G','K']]
        natural=float(np.sqrt(eigh(K,M,eigvals_only=True)[0]));frequencies=natural*np.array([.999,1.,1.001])
        v=AnalysisService().execute(m,AnalysisCase('general_frf',dict(frequency_rad_s=frequencies,speed=183.))).result
        for i,w in enumerate(frequencies):
            D=K-w*w*M+1j*w*(C+183.*G);reference=np.linalg.solve(D,np.eye(len(D)))
            np.testing.assert_allclose(v.H_disp[:,:,i],reference,rtol=1e-9,atol=1e-13)
            resonance.append(dict(frequency=float(w),condition_D=float(np.linalg.cond(D)),max_abs_error=float(np.max(abs(v.H_disp[:,:,i]-reference))),residual=float(v.residual[i])))
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(dict(status='PASS',parity=rows,physics=physics,resonance_study=resonance),indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);qualify(p.parse_args().out)
