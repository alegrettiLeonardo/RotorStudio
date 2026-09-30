"""One-time additive freeze from the exact, unmodified ROSS authority only."""
from __future__ import annotations
import argparse,hashlib,json,platform,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
from ucs_bearing_order_cases import ROSS_SHA,specifications,ross_rotor
from generate_ucs_reference import _jsonable,_temp_rotor


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def generate(root,out):
    root=root.resolve();out=out.resolve()
    if out.exists():raise RuntimeError('Refusing to overwrite existing authority/candidate directory')
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()!=ROSS_SHA:
        raise RuntimeError('Wrong ROSS SHA')
    if subprocess.check_output(['git','diff','--name-only','HEAD'],cwd=root,text=True).strip():
        raise RuntimeError('ROSS tracked sources are modified')
    sys.path.insert(0,str(root))
    import ross as rs
    import numpy as np
    from ross.utils import convert_6dof_to_4dof,intersection
    if not Path(rs.__file__).resolve().is_relative_to(root):raise RuntimeError('Wrong imported ROSS checkout')
    files=['ross/rotor_assembly.py','ross/utils.py','ross/results.py','ross/bearing_seal_element.py']
    hashes={p:digest(root/p) for p in files}
    historical=json.loads((Path(__file__).parent/'ucs'/'authority.json').read_text())
    # The explicit commit/import/clean-tree gates remain authoritative; compare
    # source hashes to the historical manifest wherever that manifest exposes them.
    out.mkdir(parents=True)
    for name,spec in specifications().items():
        np.random.seed(1729)
        rotor=ross_rotor(rs,spec)
        result=rotor.run_ucs(stiffness_range=(6,10),num=7,num_modes=16,
            bearing_speed_range=spec['bearing_speed_range'],synchronous=spec['synchronous'])
        physical=[b for b in rotor.bearing_elements if not isinstance(b,rs.SealElement)]
        assert result.bearing is physical[0]
        b=result.bearing; axis=np.asarray(result.bearing_speed_range,float)
        kxx=np.asarray(b.kxx_interpolated(axis),float);kyy=np.asarray(b.kyy_interpolated(axis),float)
        families=['kxx'] if np.array_equal(b.kxx,b.kyy) else ['kxx','kyy']
        ix=[];iy=[];im=[];ic=[]
        for mode,wn in enumerate(result.wn):
            for coefficient in families:
                xx,yy=intersection(result.stiffness_log,wn,kxx if coefficient=='kxx' else kyy,axis)
                ix.extend(xx);iy.extend(yy);im.extend([mode]*len(xx));ic.extend([coefficient]*len(xx))
        np.testing.assert_allclose(ix,result.intersection_points['x'],rtol=0,atol=0)
        np.testing.assert_allclose(iy,result.intersection_points['y'],rtol=0,atol=0)
        def modal_array(attr):
            if not result.critical_points_modal:return np.empty((6,0))
            return np.column_stack([np.asarray(getattr(m,attr))[:6] for m in result.critical_points_modal])
        lam=modal_array('evalues')
        policy=('explicit_30_point_linspace' if spec['bearing_speed_range'] is not None else
            'bearing_speed_axis' if b.speed is not None else
            'bearing_frequency_axis' if b.frequency is not None else 'constant_10_point_rotor_wn_margin')
        arrays=dict(stiffness_log_n_m=result.stiffness_log,natural_frequency_rad_s=result.wn,
            bearing_speed_rad_s=axis,bearing_kxx_n_m=kxx,bearing_kyy_n_m=kyy,
            intersection_stiffness_n_m=ix,intersection_speed_rad_s=iy,
            intersection_mode_index=im,intersection_coefficient=ic,
            critical_eigenvalue_real=lam.real,critical_eigenvalue_imag=lam.imag,
            critical_wn_rad_s=modal_array('wn'),critical_wd_rad_s=modal_array('wd'),
            critical_damping_ratio=modal_array('damping_ratio'),critical_log_dec=modal_array('log_dec'),
            coefficient_families=families,bearing_speed_policy=policy)
        sentinels=[]
        for j in [0,3,6]:
            k=float(result.stiffness_log[j]);temp=_temp_rotor(rs,convert_6dof_to_4dof,rotor,k)
            sentinels.append(dict(stiffness_n_m=k,M=temp.M(0,synchronous=spec['synchronous']),
                C=temp.C(0),G=temp.G(),K=temp.K(0)))
        payload=dict(case=name,ross_sha=ROSS_SHA,specification=spec,
            input_insertion_order=[b['node'] for b in spec['supports']],
            effective_ross_order=[x.n+1 for x in rotor.bearing_elements],
            effective_ross_tags=[x.tag for x in rotor.bearing_elements],
            selected_bearing_node=b.n+1,selected_bearing_tag=b.tag,
            result=arrays,matrix_sentinels=sentinels)
        (out/f'{name}.json').write_text(json.dumps(_jsonable(payload),indent=2,sort_keys=True)+'\n',encoding='utf-8')
        print(name,'selected',b.n+1,b.tag,'intersections',len(ix))
    manifest=dict(ross_sha=ROSS_SHA,created_utc=datetime.now(timezone.utc).isoformat(),
        python=platform.python_version(),numpy=np.__version__,source_sha256=hashes,
        generator_sha256=digest(Path(__file__)),cases_sha256=digest(Path(__file__).with_name('ucs_bearing_order_cases.py')),
        files={p.name:digest(p) for p in sorted(out.glob('*.json'))},
        policy='Additive immutable ROSS authority; historical ucs/ is not rewritten')
    (out/'authority.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ross-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();generate(a.ross_root,a.out)
