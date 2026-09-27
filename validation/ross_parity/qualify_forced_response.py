"""Independent validation only: ROSS goldens, A2 H@F and A3 native solve."""
import argparse,json,sys,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'python/tests_forced'))
from forced_cases import case,NAMES
from test_forced_response import parity,ATOL,test_linearity_scale_phase_zero
from drm_core import run_forced_response,run_general_frf
from drm_core.solver.backend import FortranBackend
from drm_core.solver.general_frf_backend import matrices

def qualify():
    rows=[];cases={};backend=FortranBackend()
    for name in NAMES:
        m,s=case(name);r=run_forced_response(m,s['frequencies'],s['force_real'],s['force_imag'],s['speed']);h=run_general_frf(m,s['frequencies'],s['speed'])
        with np.load(ROOT/f'validation/ross_parity/forced/{name}.npz') as g:
            for attr,key,hkey in [('displacement','q','H_disp'),('velocity','v','H_vel'),('acceleration','a','H_acc')]:
                actual=getattr(r,attr)
                for authority,expected in [('ROSS',g[key]),('A2_HF',np.einsum('ijk,jk->ik',getattr(h,hkey),r.force_complex))]:
                    parity(actual,expected,key)
                    for part in ('real','imag'):rows.append(dict(case=name,authority=authority,quantity=key,part=part,max_abs=float(np.max(abs(getattr(actual,part)-getattr(expected,part)))),status='PASS'))
            points=[]
            for i,(w,omega) in enumerate(zip(r.frequency_rad_s,r.rotor_speed_rad_s)):
                D=matrices(backend,m,w,omega)['D'];np.testing.assert_allclose(D,g['D'][:,:,i],rtol=2e-12,atol=1e-7)
                q=r.displacement[:,i];F=r.force_complex[:,i];den=np.linalg.norm(D,np.inf)*np.linalg.norm(q,np.inf)+np.linalg.norm(F,np.inf)
                residual=float(np.linalg.norm(D@q-F,np.inf)/den)
                assert residual<1e-12 and r.residual[i]<1e-12
                points.append(dict(frequency_rad_s=float(w),rotor_speed_rad_s=float(omega),condition_estimate_1=float(r.condition_estimate[i]),condition_2=float(np.linalg.cond(D)),residual_independent=residual,residual_native=float(r.residual[i])))
            vid=float(np.max(abs(r.velocity-1j*r.frequency_rad_s*r.displacement)));aid=float(np.max(abs(r.acceleration+r.frequency_rad_s**2*r.displacement)))
            assert vid<1e-12 and aid<1e-12
            cases[name]=dict(points=points,velocity_identity=vid,acceleration_identity=aid,status='PASS')
    for name in ['single_x','fixed_speed','map_2d','near_resonance']:test_linearity_scale_phase_zero(name)
    return dict(status='PASS',head_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),ross_sha='6320eab9f890f1b3cc1710d508b446fe063ca68d',rtol=1e-10,atol_translation_rotation=ATOL,comparison_rows=rows,cases=cases,physics=dict(linearity='PASS',complex_scaling='PASS',phase_rotation='PASS',zero_force='PASS'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();result=qualify();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(f'PASS: {len(result["comparison_rows"])} real/imaginary ROSS and A2 comparisons, {len(result["cases"])} cases, independent physics')
