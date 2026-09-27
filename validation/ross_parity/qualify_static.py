"""Numerical evidence, including independent constrained-system conditioning study."""
import argparse,json,sys
from pathlib import Path
import numpy as np
from static_abi import call_native

def qualify(out):
    root=Path(__file__).parent;rows=[];physics=[]
    for folder,names in [('static',['uniform','stepped_overhung','three_supports']),('static_extended',['timoshenko_hollow','rotary_eb','no_disk','seal_excluded','mass_disk'])]:
        for name in names:
            spec=json.loads((root/folder/f'{name}.json').read_text());native=call_native(spec)
            with np.load(root/folder/f'{name}.npz') as ref:
                for key,value,atol in [('displacement_y_m',native['q'][1::4],1e-13),('bearing_reactions_N',native['reactions'][spec['supports']],1e-8),('shaft_weight_N',[sum(native['shaft_weights'])],1e-8),('disk_weight_N',native['disk_weights'],1e-8),('shear_force_N',native['shear'],1e-8),('bending_moment_Nm',native['bending'],1e-8),('x_m',native['stations'],1e-14)]:
                    a=np.asarray(value).ravel();b=ref[key].ravel();err=abs(a-b)
                    np.testing.assert_allclose(a,b,rtol=1e-8,atol=atol)
                    idx=int(np.argmax(err)) if len(err) else None
                    rows.append(dict(case=name,quantity=key,ross=float(b[idx]) if idx is not None else None,fortran=float(a[idx]) if idx is not None else None,max_abs_error=float(max(err,default=0)),max_relative_error=float(max(err/np.maximum(abs(b),atol),default=0)),rtol=1e-8,atol=atol,status='PASS'))
                record=dict(case=name,force_residual_N=float(native['diagnostics'][0]),moment_residual_Nm=float(native['diagnostics'][1]),scaled_residual=float(native['diagnostics'][2]))
                assert max(abs(native['diagnostics'][:2]))<1e-8 and native['diagnostics'][2]<1e-14
                if 'K' in ref:
                    K=ref['K'];F=ref['Fg'];kp=K.copy();fixed=np.array([4*n+j for n in spec['supports'] for j in (0,1)])
                    kp[fixed,fixed]+=1e20;free=np.setdiff1d(np.arange(len(K)),fixed)
                    eliminated=np.zeros(len(K));eliminated[free]=np.linalg.solve(K[np.ix_(free,free)],F[free])
                    record.update(penalty_condition_2=float(np.linalg.cond(kp)),eliminated_condition_2=float(np.linalg.cond(K[np.ix_(free,free)])),penalty_vs_eliminated_max_abs_m=float(np.max(abs(native['q'][1::4]-eliminated[1::4]))))
                    np.testing.assert_allclose(native['q'][1::4],eliminated[1::4],rtol=1e-8,atol=1e-13)
                physics.append(record)
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    Path(out).write_text(json.dumps(dict(status='PASS',parity=rows,physics=physics),indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);qualify(p.parse_args().out)
