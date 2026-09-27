"""A3 goldens generated exclusively by the immutable 4-DOF ROSS authority."""
import argparse,json,sys,copy,platform
from pathlib import Path
from datetime import datetime,timezone
from generate_reference import verify_checkout,ROSS_SHA,digest,json_write,git

def generate(root,out):
    root=verify_checkout(root);out=Path(out)
    if out.exists():raise FileExistsError(out)
    sys.path.insert(0,str(root))
    import ross as rs
    import numpy as np
    import scipy
    from scipy.linalg import eigh
    from ross.utils import convert_6dof_to_4dof
    assert Path(rs.__file__).resolve()==root/'ross/__init__.py'
    mapping={'single_x':'synchronous','quadrature_xy':'synchronous','fixed_speed':'fixed_speed','pure_moment':'fixed_speed','multiple_nodes':'fixed_speed','multiple_dofs':'fixed_speed','cross_coupled':'cross_coupled','anisotropic':'anisotropic','speed_axis':'speed_axis','frequency_axis':'frequency_axis','map_2d':'map_2d','phase_sentinel':'fixed_speed','near_resonance':'synchronous'}
    records={};specs={}
    for name,source in mapping.items():
        s=json.loads((Path(__file__).parent/'frf'/f'{source}.json').read_text());s.pop('free_free')
        mat=rs.Material(name='a3',rho=s['rho'],E=s['E'],G_s=s['G'])
        shafts=[rs.ShaftElement(L=L,idl=s['inner'],odl=d,material=mat,shear_effects=True,rotary_inertia=True,gyroscopic=True) for L,d in zip(s['lengths'],s['diameters'])]
        x=s['disk'];disks=[rs.DiskElement(n=x['node'],m=x['mass'],Id=x['Id'],Ip=x['Ip'])]
        bearings=[rs.BearingElement(n=b['node'],**{k:v for k,v in b.items() if k!='node'}) for b in s['bearings']]
        rotor=convert_6dof_to_4dof(rs.Rotor(shafts,disks,bearings))
        if name=='near_resonance':
            natural=float(np.sqrt(eigh(rotor.K(0,0),rotor.M(0,0),eigvals_only=True)[0]))
            # Freeze the sampled axis; platform-specific eigensolver roundoff must not change the input contract.
            s['frequencies']=[329.75614625359367, 330.0862324860797, 330.4163187185658];s['speed']=183.
            assert abs(s['frequencies'][1]/natural-1)<1e-10
        nf=len(s['frequencies']);F=np.zeros((rotor.ndof,nf),complex);t=np.arange(nf)
        if name=='single_x':F[4]=137+41j
        elif name=='quadrature_xy':F[4]=137;F[5]=-137j
        elif name=='pure_moment':F[6]=17-31j
        elif name=='multiple_nodes':F[0]=137+41j;F[12]=-23+89j
        else:
            # Nonproportional arbitrary spectrum: not an omega-squared unbalance.
            F[4]=137+11*t+1j*(41-7*t*t)
            F[9]=-23+3*t*t+1j*(89+13*t)
            F[6]=17-2*t+1j*(-31+5*t)
            F[15]=-11+7*t+1j*(-7-3*t*t)
        if name=='phase_sentinel':F*=np.exp(.731j)
        result=rotor.run_forced_response(force=F,speed_range=s['frequencies'],speed=s['speed'])
        s['force_real']=F.real.tolist();s['force_imag']=F.imag.tolist()
        D=np.stack([rotor.K(w,w if s['speed'] is None else s['speed'])-w*w*rotor.M(w,w if s['speed'] is None else s['speed'])+1j*w*(rotor.C(w,w if s['speed'] is None else s['speed'])+(w if s['speed'] is None else s['speed'])*rotor.G()) for w in s['frequencies']],axis=2)
        a=dict(force=F,q=result.forced_resp,v=result.velc_resp,a=result.accl_resp,D=D)
        assert all(np.isfinite(v).all() for v in a.values());records[name]=a;specs[name]=s
    out.mkdir(parents=True)
    for name,s in specs.items():json_write(out/f'{name}.json',s);np.savez(out/f'{name}.npz',**records[name])
    json_write(out/'authority.json',dict(repository='petrobras/ross',commit=ROSS_SHA,python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,generated_utc=datetime.now(timezone.utc).isoformat(),dof_mapping='explicit convert_6dof_to_4dof before run_forced_response; [x,y,alpha,beta]',source_sha256={p:digest(root/p) for p in git(root,'ls-files','ross','LICENSE.md').splitlines() if (root/p).is_file()},files_sha256={p.name:digest(p) for p in out.iterdir()}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ross-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();generate(a.ross_root,a.out)
