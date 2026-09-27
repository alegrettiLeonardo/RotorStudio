"""Additional A1 authorities. Never rewrites A0 references or uses RotorStudio."""
import argparse
import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import platform
import sys
from generate_reference import verify_checkout,ROSS_SHA,digest,json_write,git

def generate(root,out):
    root=verify_checkout(root);out=Path(out)
    if out.exists():raise FileExistsError('Immutable reference output already exists')
    sys.path.insert(0,str(root))
    import ross as rs
    import numpy as np
    import scipy
    from ross.utils import remove_dofs
    if Path(rs.__file__).resolve()!=root/'ross/__init__.py':raise ValueError('wrong imported authority')
    matrices={};sentinels=[]
    for t in range(1,9):
        for j,(L,do,di) in enumerate([(.173,.061,.017),(.52,.083,0.),(.081,.044,.031)]):
            material=rs.Material(name='sentinel',rho=7987.,E=203e9,G_s=78e9)
            sh=rs.ShaftElement(L=L,idl=di,odl=do,material=material,
                shear_effects=t not in (1,5,7,8),rotary_inertia=t not in (1,4,6,8),gyroscopic=t not in (3,6,7,8))
            prefix=f't{t}_{j}'
            sentinels.append(dict(key=prefix,shaft_type=t,L=L,do=do,di=di,rho=7987.,E=203e9,G=78e9))
            matrices[prefix+'_M']=remove_dofs(sh.M());matrices[prefix+'_K']=remove_dofs(sh.K())
    base=json.loads((Path(__file__).parent/'static/stepped_overhung.json').read_text())
    specs={}
    for name,t,rot in [('timoshenko_hollow',2,True),('rotary_eb',5,True),('no_disk',2,True),('seal_excluded',2,True),('mass_disk',2,True)]:
        spec=copy.deepcopy(base);spec.update(shaft_type=t,shear_effects=t==2,rotary_inertia=rot,inner_diameter_m=.012)
        if name=='no_disk':spec['disks']=[]
        if name=='seal_excluded':spec['seal_nodes']=[2]
        if name=='mass_disk':spec['disks'].append(dict(node=3,mass_kg=4.6,Id_kg_m2=0.,Ip_kg_m2=0.))
        specs[name]=spec
    records={}
    for name,spec in specs.items():
        mat=rs.Material(name='a1_static',rho=spec['rho_kg_m3'],E=spec['E_Pa'],G_s=spec['G_Pa'])
        shafts=[rs.ShaftElement(L=L,idl=spec['inner_diameter_m'],odl=d,material=mat,
            shear_effects=spec['shear_effects'],rotary_inertia=True) for L,d in zip(spec['lengths_m'],spec['outer_diameters_m'],strict=True)]
        disks=[rs.DiskElement(n=d['node'],m=d['mass_kg'],Id=d['Id_kg_m2'],Ip=d['Ip_kg_m2']) for d in spec['disks'] if not d.get('point_mass')]
        points=[rs.PointMass(n=d['node'],m=d['mass_kg']) for d in spec['disks'] if d.get('point_mass')]
        bearings=[rs.BearingElement(n=n,kxx=1e6,cxx=0) for n in spec['supports']]
        bearings += [rs.SealElement(n=n,kxx=1e12,cxx=0) for n in spec.get('seal_nodes',[])]
        rotor=rs.Rotor(shafts,disks,bearings,point_mass_elements=points)
        print('Generating',name,flush=True)
        result=rotor.run_static()
        bare=rs.Rotor(shafts,disks,[rs.BearingElement(n=n,kxx=0,cxx=0) for n in spec['supports']],point_mass_elements=points)
        arrays={
            'M':remove_dofs(bare.M(0)), 'K':remove_dofs(bare.K(0)),
            'displacement_y_m':result.deformation,'shear_force_N':result.Vx,
            'bending_moment_Nm':result.Bm,'x_m':result.Vx_axis,
            'nodes_x_m':result.nodes_pos,'shaft_weight_N':[result.w_shaft],
            'bearing_reactions_N':[result.bearing_forces[f'node_{n}'] for n in spec['supports']],
            'disk_weight_N':[d['mass_kg']*9.8065 for d in spec['disks']],
        }
        arrays={k:np.asarray(v,dtype=float) for k,v in arrays.items()}
        gravity=np.zeros(arrays['M'].shape[0]);gravity[1::4]=-9.8065
        arrays['Fg']=arrays['M']@gravity
        if any(not np.isfinite(a).all() for a in arrays.values()):raise ValueError('nonfinite reference')
        records[name]=arrays
    out.mkdir(parents=True)
    json_write(out/'elements.json',sentinels);np.savez(out/'elements.npz',**matrices)
    for name,spec in specs.items():
        json_write(out/f'{name}.json',spec);np.savez(out/f'{name}.npz',**records[name])
    manifest=dict(repository='petrobras/ross',commit=ROSS_SHA,python=platform.python_version(),
        numpy=np.__version__,scipy=scipy.__version__,ross=rs.__version__,platform=platform.platform(),
        generated_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256={p:digest(root/p) for p in git(root,'ls-files','ross','LICENSE.md','pyproject.toml','requirements.txt').splitlines() if (root/p).is_file()},
        files_sha256={p.name:digest(p) for p in out.iterdir()},
        purpose='A1 circular M/K and extended static authority; A0 untouched')
    json_write(out/'authority.json',manifest)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ross-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();generate(a.ross_root,a.out)
