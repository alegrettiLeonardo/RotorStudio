"""Freeze A6 Level 1 authority from exact ROSS.

Validation-only.  Production Level 1 physics must remain native Fortran.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"


def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def jsonable(value):
    import numpy as np
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,complex):return {"real":float(value.real),"imag":float(value.imag)}
    if isinstance(value,dict):return {str(k):jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [jsonable(v) for v in value]
    return value


def write(path:Path,payload):
    path.write_text(json.dumps(jsonable(payload),indent=2,sort_keys=True)+"\n")


def rotor_from_bearings(rs,np,bearings,rated_w):
    material=rs.Material(name="a6",rho=7810.0,E=211e9,G_s=81.2e9)
    shafts=[
        rs.ShaftElement(
            L=0.25,idl=0.0,odl=0.05,material=material,
            shear_effects=True,rotary_inertia=True,gyroscopic=True,
        )
        for _ in range(6)
    ]
    disks=[
        rs.DiskElement.from_geometry(
            n=2,material=material,width=0.07,i_d=0.05,o_d=0.28
        ),
        rs.DiskElement.from_geometry(
            n=4,material=material,width=0.06,i_d=0.05,o_d=0.24
        ),
    ]
    copied=[copy.deepcopy(b) for b in bearings]
    return rs.Rotor(shafts,disks,copied,rated_w=float(rated_w))


def base_bearings(rs):
    return [
        rs.BearingElement(0,kxx=1.0e6,kyy=0.8e6,cxx=180.0,cyy=140.0),
        rs.BearingElement(6,kxx=1.0e6,kyy=0.8e6,cxx=180.0,cyy=140.0),
    ]


def bearing_cases(rs,np):
    speed=np.array([0.0,200.0,400.0,600.0,800.0])
    kx=np.array([0.90e6,1.02e6,1.16e6,1.33e6,1.53e6])
    ky=np.array([0.72e6,0.82e6,0.94e6,1.09e6,1.26e6])
    cx=np.array([220.0,205.0,190.0,176.0,165.0])
    cy=np.array([180.0,169.0,158.0,148.0,139.0])

    fr=np.array([100.0,250.0,400.0,550.0,700.0])
    sp=np.array([100.0,250.0,400.0,550.0,700.0])
    gx=np.array([
        [0.72e6,0.76e6,0.80e6,0.84e6,0.88e6],
        [0.86e6,0.91e6,0.96e6,1.01e6,1.07e6],
        [1.02e6,1.08e6,1.15e6,1.22e6,1.30e6],
        [1.20e6,1.27e6,1.35e6,1.44e6,1.54e6],
        [1.40e6,1.48e6,1.57e6,1.67e6,1.78e6],
    ])
    gy=0.79*gx+7.5e4
    gcx=np.array([
        [240.,230.,220.,210.,200.],
        [230.,220.,210.,200.,190.],
        [220.,210.,200.,190.,180.],
        [210.,200.,190.,180.,170.],
        [200.,190.,180.,170.,160.],
    ])
    gcy=0.82*gcx+15.0

    return {
        "zero_speed_fixture":{
            "bearings":[
                rs.BearingElement(0,kxx=1e6,kyy=.8e6,cxx=0.0),
                rs.BearingElement(6,kxx=1e6,kyy=.8e6,cxx=0.0),
            ],
            "rated_w":0.0,"node":0,"q_range":(1e6,1e11),"num":5,
        },
        "rated_speed_midspan":{
            "bearings":base_bearings(rs),
            "rated_w":377.0,"node":3,"q_range":(0.0,2.5e6),"num":7,
        },
        "application_at_support":{
            "bearings":base_bearings(rs),
            "rated_w":377.0,"node":0,"q_range":(0.0,2.5e6),"num":7,
        },
        "anisotropic_damped":{
            "bearings":[
                rs.BearingElement(0,kxx=1.3e6,kyy=.7e6,cxx=420.,cyy=250.),
                rs.BearingElement(6,kxx=1.1e6,kyy=.9e6,cxx=360.,cyy=290.),
            ],
            "rated_w":420.0,"node":3,"q_range":(0.0,3.0e6),"num":7,
        },
        "speed_dependent":{
            "bearings":[
                rs.BearingElement(0,kxx=kx,kyy=ky,cxx=cx,cyy=cy,speed=speed),
                rs.BearingElement(6,kxx=1.08*kx,kyy=1.05*ky,cxx=.95*cx,cyy=1.03*cy,speed=speed),
            ],
            "rated_w":400.0,"node":3,"q_range":(0.0,4.0e6),"num":7,
        },
        "map_2d":{
            "bearings":[
                rs.BearingElement(0,kxx=gx,kyy=gy,cxx=gcx,cyy=gcy,speed=sp,frequency=fr),
                rs.BearingElement(6,kxx=1.05*gx,kyy=1.03*gy,cxx=.97*gcx,cyy=1.02*gcy,speed=sp,frequency=fr),
            ],
            "rated_w":400.0,"node":3,"q_range":(0.0,4.0e6),"num":7,
        },
    }


def modal_summary(np,modal):
    directions=np.asarray(modal.whirl_direction(),dtype=str)
    non_backward=directions!="Backward"
    selected=np.flatnonzero(non_backward)
    if not len(selected):
        raise RuntimeError("frozen ROSS Level 1 produced no non-backward mode")
    idx=int(selected[0])
    return {
        "selected_index":idx,
        "selected_log_dec":float(modal.log_dec[idx]),
        "directions":directions.tolist(),
        "evalues_real":np.asarray(modal.evalues).real,
        "evalues_imag":np.asarray(modal.evalues).imag,
        "wn":np.asarray(modal.wn),
        "wd":np.asarray(modal.wd),
        "damping_ratio":np.asarray(modal.damping_ratio),
        "log_dec":np.asarray(modal.log_dec),
        "selected_kappa":[float(x) for x in modal.kappa_mode(idx)],
    }


def explicit_case(rs,np,convert_6dof_to_4dof,spec):
    rotor=rotor_from_bearings(rs,np,spec["bearings"],spec["rated_w"])
    q=np.linspace(spec["q_range"][0],spec["q_range"][1],spec["num"])
    actual=rotor.run_level1(
        n=spec["node"],stiffness_range=spec["q_range"],num=spec["num"]
    )
    if not np.array_equal(np.asarray(actual.stiffness_range),q):
        raise RuntimeError("run_level1 explicit range is not np.linspace authority")

    full6=[]
    adapted4=[]
    sentinels=[]
    for i,Q in enumerate(q):
        bearings=[copy.copy(b) for b in rotor.bearing_elements]
        bearings.append(
            rs.BearingElement(
                n=spec["node"],kxx=0.0,cxx=0.0,kxy=float(Q),kyx=-float(Q)
            )
        )
        temp=rs.Rotor(
            rotor.shaft_elements,rotor.disk_elements,bearings,rotor.point_mass_elements
        )
        modal6=temp.run_modal(speed=spec["rated_w"])
        full6.append(modal_summary(np,modal6))

        temp4=convert_6dof_to_4dof(temp)
        modal4=temp4.run_modal(speed=spec["rated_w"])
        adapted4.append(modal_summary(np,modal4))

        if i in {0,len(q)//2,len(q)-1}:
            M=np.asarray(temp4.M(spec["rated_w"],spec["rated_w"]),float)
            C=np.asarray(temp4.C(spec["rated_w"],spec["rated_w"]),float)
            G=np.asarray(temp4.G(),float)
            K=np.asarray(temp4.K(spec["rated_w"],spec["rated_w"]),float)
            sentinels.append({
                "index":i,"Q":float(Q),"M":M,"C":C,"G":G,"K":K,
                "modal":adapted4[-1],
            })

    manual6=np.asarray([x["selected_log_dec"] for x in full6])
    if not np.allclose(manual6,np.asarray(actual.log_dec),rtol=0.0,atol=0.0):
        raise RuntimeError("manual frozen run_level1 reconstruction does not match method")

    return {
        "input":{
            "rated_w_rad_s":float(spec["rated_w"]),
            "ross_cross_coupling_node_zero_based":int(spec["node"]),
            "rotorstudio_node_one_based":int(spec["node"])+1,
            "stiffness_range_n_m":[float(x) for x in spec["q_range"]],
            "num":int(spec["num"]),
        },
        "ross_level1":{
            "stiffness_range":np.asarray(actual.stiffness_range,float),
            "log_dec":np.asarray(actual.log_dec,float),
        },
        "ross_manual_6dof":full6,
        "ross_adapted_4dof":{
            "log_dec":np.asarray([x["selected_log_dec"] for x in adapted4],float),
            "selected_index":np.asarray([x["selected_index"] for x in adapted4],int),
            "points":adapted4,
            "matrix_sentinels":sentinels,
        },
        "actual_vs_adapted_4dof_max_abs":float(
            np.max(np.abs(np.asarray(actual.log_dec)-np.asarray([x["selected_log_dec"] for x in adapted4])))
        ),
    }


def default_range_audit(rs,np):
    bearings=base_bearings(rs)
    rotor=rotor_from_bearings(rs,np,bearings,400.0)
    result=rotor.run_level1(n=3,stiffness_range=None,num=5)
    k=float(bearings[0].kxx_interpolated(400.0))
    p=int(np.log10(k))
    expected=np.linspace(p-3,p+3,5)
    if not np.array_equal(np.asarray(result.stiffness_range),expected):
        raise RuntimeError("frozen default Level 1 range behavior changed")
    return {
        "case":"default_range_audit_only",
        "rated_w_rad_s":400.0,
        "first_bearing_kxx_n_m":k,
        "integer_log10_k":p,
        "effective_stiffness_range":np.asarray(result.stiffness_range,float),
        "log_dec":np.asarray(result.log_dec,float),
        "note":"audit-only frozen behavior; RotorStudio A6 requires explicit physical Q range",
    }


def generate(ross_root:Path,out:Path):
    root=ross_root.resolve()
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    if head!=ROSS_SHA:
        raise RuntimeError(f"ROSS authority mismatch: expected {ROSS_SHA}, got {head}")
    if out.exists():
        raise FileExistsError(f"refusing to overwrite immutable A6 authority: {out}")

    sys.path.insert(0,str(root))
    import numpy as np
    import scipy
    import ross as rs
    from ross.utils import convert_6dof_to_4dof

    if Path(rs.__file__).resolve()!=root/"ross"/"__init__.py":
        raise RuntimeError("imported ROSS is not the frozen checkout")

    out.mkdir(parents=True)
    manifest={}
    for name,spec in bearing_cases(rs,np).items():
        payload={"case":name,**explicit_case(rs,np,convert_6dof_to_4dof,spec)}
        path=out/f"{name}.json"
        write(path,payload);manifest[path.name]=digest(path)

    path=out/"default_range_audit.json"
    write(path,default_range_audit(rs,np));manifest[path.name]=digest(path)

    authority_files=[
        "ross/rotor_assembly.py",
        "ross/results.py",
        "ross/bearing_seal_element.py",
        "ross/utils.py",
        "ross/tests/test_plot_results.py",
        "ross/agent_skills/ross/ucs_and_level1.md",
    ]
    authority={
        "repository":"petrobras/ross",
        "commit":ROSS_SHA,
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "python":platform.python_version(),
        "numpy":np.__version__,
        "scipy":scipy.__version__,
        "scope":"A6 Level 1 immutable authority; actual run_level1 plus declared 4-DOF adaptation",
        "source_sha256":{name:digest(root/name) for name in authority_files},
        "golden_sha256":manifest,
    }
    write(out/"authority.json",authority)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--ross-root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    generate(args.ross_root,args.out)
