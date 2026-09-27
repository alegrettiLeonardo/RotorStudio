"""Offline ROSS authority runner. Never imported by production RotorStudio."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys

ROSS_SHA = '6320eab9f890f1b3cc1710d508b446fe063ca68d'

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()

def verify_checkout(root):
    root = Path(root).resolve()
    if git(root, 'rev-parse', 'HEAD') != ROSS_SHA:
        raise ValueError('ROSS authority SHA mismatch')
    if git(root, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('ROSS authority checkout must be clean, including untracked files')
    return root

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def json_write(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')

def cases(rs):
    # All dimensions SI. Nonuniform sections and asymmetric disk placement
    # exercise nodal loads and internal diagram station ordering.
    specifications = [
        ('uniform', [.25]*6, [.05]*6, [(2, 12.3), (4, 9.7)], [0, 6]),
        ('stepped_overhung', [.13,.21,.17,.29,.11,.19], [.04,.06,.05,.07,.045,.04], [(1, 7.1),(5, 15.3)], [1,4]),
        ('three_supports', [.25]*6, [.05]*6, [(2,12.3),(4,9.7)], [0,3,6]),
    ]
    for name, lengths, diameters, disks, supports in specifications:
        spec = dict(lengths_m=lengths, outer_diameters_m=diameters,
                    inner_diameter_m=0., rho_kg_m3=7810., E_Pa=211e9,
                    G_Pa=81.2e9, disks=[dict(node=n,mass_kg=m,Id_kg_m2=.04,Ip_kg_m2=.08) for n,m in disks],
                    supports=supports, shear_effects=False, rotary_inertia=False,
                    gyroscopic=False, gravity_m_s2=-9.8065,
                    dof_order=['x','y','alpha','beta'])
        material = rs.Material(name='a0_sentinel', rho=7810., E=211e9, G_s=81.2e9)
        shafts = [rs.ShaftElement(L=L, idl=0., odl=d, material=material,
                    shear_effects=False, rotary_inertia=False, gyroscopic=False)
                  for L,d in zip(lengths,diameters,strict=True)]
        rotor = rs.Rotor(shafts, [rs.DiskElement(n=n,m=m,Id=.04,Ip=.08) for n,m in disks],
                         [rs.BearingElement(n=n,kxx=1e6,cxx=0) for n in supports])
        yield name, spec, rotor

def generate(root, out):
    root = verify_checkout(root)
    out = Path(out)
    if out.exists():
        raise FileExistsError('Output must be a new directory; golden overwrite is forbidden')
    if 'ross' in sys.modules:
        raise RuntimeError('Run generation in a fresh Python process')
    sys.path.insert(0, str(root))
    import ross as rs
    import numpy as np
    import scipy
    if Path(rs.__file__).resolve() != root/'ross/__init__.py':
        raise ValueError('Imported ROSS is outside authority checkout')
    source_paths = git(root,'ls-files','ross','LICENSE.md','pyproject.toml','requirements.txt').splitlines()
    hashes = {p:digest(root/p) for p in source_paths if (root/p).is_file()}
    records = []
    for name,spec,rotor in cases(rs):
        result=rotor.run_static()
        arrays={key:np.asarray(value,dtype=float) for key,value in {
            'displacement_y_m':result.deformation,'shear_force_N':result.Vx,
            'bending_moment_Nm':result.Bm,'x_m':result.Vx_axis,
            'nodes_x_m':result.nodes_pos,'shaft_weight_N':[result.w_shaft],
            'bearing_nodes':spec['supports'],
            'bearing_reactions_N':[result.bearing_forces[f'node_{n}'] for n in spec['supports']],
            'disk_nodes':[d['node'] for d in spec['disks']],
            'disk_weight_N':[d['mass_kg']*9.8065 for d in spec['disks']],
        }.items()}
        if not all(np.isfinite(a).all() for a in arrays.values()):
            raise ValueError(f'Nonfinite authority output: {name}')
        records.append((name,spec,arrays))
    # Collect metadata only after successful solves; never label A1 parity PASS.
    out.mkdir(parents=True)
    manifest={}
    for name,spec,arrays in records:
        np.savez(out/f'{name}.npz',**arrays)
        json_write(out/f'{name}.json',spec)
        for suffix in ('npz','json'):
            p=out/f'{name}.{suffix}'; manifest[p.name]=digest(p)
    json_write(out/'authority.json',dict(repository='petrobras/ross',commit=ROSS_SHA,
        python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
        ross=rs.__version__,platform=platform.platform(),
        generated_utc=datetime.now(timezone.utc).isoformat(),source_sha256=hashes,
        files_sha256=manifest,qualification='REFERENCE_GENERATED_NOT_FORTRAN_PARITY'))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--ross-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    generate(args.ross_root,args.out)
