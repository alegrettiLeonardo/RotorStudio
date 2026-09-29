"""Freeze A7 API 617 unbalance placement authority from exact ROSS.

Validation-only. Production API 617 placement physics must remain native.
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
    if isinstance(value,np.ndarray):return jsonable(value.tolist())
    if isinstance(value,np.generic):return jsonable(value.item())
    if isinstance(value,complex):return {"real":float(value.real),"imag":float(value.imag)}
    if isinstance(value,dict):return {str(k):jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [jsonable(v) for v in value]
    return value


def write(path:Path,payload):
    path.write_text(json.dumps(jsonable(payload),indent=2,sort_keys=True)+"\n")


def standard_rotor(rs):
    base=rs.rotor_example()
    bearings=[
        rs.BearingElement(n=0,kxx=1e6,cxx=1e3,radial_clearance=100e-6,tag="DE"),
        rs.BearingElement(n=6,kxx=1e6,cxx=1e3,radial_clearance=120e-6,tag="NDE"),
    ]
    return rs.Rotor(
        copy.deepcopy(base.shaft_elements),
        copy.deepcopy(base.disk_elements),
        bearings,
        copy.deepcopy(base.point_mass_elements),
    )


def speed_dependent_rotor(rs,np):
    base=rs.rotor_example()
    speed=np.array([0.0,300.0,600.0,900.0,1200.0])
    kx=np.array([.8e6,.95e6,1.12e6,1.32e6,1.55e6])
    ky=np.array([.70e6,.82e6,.96e6,1.12e6,1.30e6])
    cx=np.array([1100.,1050.,1000.,950.,900.])
    cy=np.array([1000.,960.,920.,880.,840.])
    bearings=[
        rs.BearingElement(n=0,kxx=kx,kyy=ky,cxx=cx,cyy=cy,speed=speed),
        rs.BearingElement(n=6,kxx=1.04*kx,kyy=1.02*ky,cxx=.98*cx,cyy=1.01*cy,speed=speed),
    ]
    return rs.Rotor(copy.deepcopy(base.shaft_elements),copy.deepcopy(base.disk_elements),bearings)


def map2d_rotor(rs,np):
    base=rs.rotor_example()
    speed=np.array([0.0,300.0,600.0,900.0,1200.0])
    frequency=np.array([0.0,300.0,600.0,900.0,1200.0])
    gx=np.array([
        [.75e6,.78e6,.82e6,.86e6,.90e6],
        [.88e6,.92e6,.97e6,1.02e6,1.08e6],
        [1.02e6,1.07e6,1.13e6,1.20e6,1.28e6],
        [1.18e6,1.24e6,1.31e6,1.39e6,1.48e6],
        [1.36e6,1.43e6,1.51e6,1.60e6,1.70e6],
    ])
    gy=.83*gx+8.0e4
    gc=np.array([
        [1150.,1120.,1090.,1060.,1030.],
        [1100.,1070.,1040.,1010.,980.],
        [1050.,1020.,990.,960.,930.],
        [1000.,970.,940.,910.,880.],
        [950.,920.,890.,860.,830.],
    ])
    bearings=[
        rs.BearingElement(n=0,kxx=gx,kyy=gy,cxx=gc,cyy=.92*gc,speed=speed,frequency=frequency),
        rs.BearingElement(n=6,kxx=1.03*gx,kyy=1.02*gy,cxx=.97*gc,cyy=.95*gc,speed=speed,frequency=frequency),
    ]
    return rs.Rotor(copy.deepcopy(base.shaft_elements),copy.deepcopy(base.disk_elements),bearings)


def overhung_rotor(rs):
    shaft=[
        rs.ShaftElement(L=0.25,idl=0,odl=0.05,material=rs.steel)
        for _ in range(6)
    ]
    disk=rs.DiskElement.from_geometry(
        n=6,material=rs.steel,width=0.07,i_d=0.05,o_d=0.28
    )
    bearings=[
        rs.BearingElement(n=0,kxx=1e7,cxx=1e3,radial_clearance=100e-6),
        rs.BearingElement(n=2,kxx=1e7,cxx=1e3,radial_clearance=100e-6),
    ]
    return rs.Rotor(shaft,[disk],bearings)


def mode_evidence(rotor,speed,mode_index,num_modes=12):
    import numpy as np
    modal=rotor.run_modal(speed=speed,num_modes=num_modes)
    ratios=[
        rotor._whirl_ratio(shape) if shape.mode_type=="Lateral" else 0.0
        for shape in modal.shapes
    ]
    shape=modal.shapes[mode_index]
    amplitude=np.asarray([orbit.major_axis for orbit in shape.orbits],float)
    reference=int(np.argmax(amplitude))
    theta=float(shape.orbits[reference].major_angle)
    projection=np.asarray([
        orbit.ru_e*np.cos(theta)+orbit.rv_e*np.sin(theta)
        for orbit in shape.orbits
    ],dtype=np.complex128)
    sign=np.sign(np.real(projection*np.conj(projection[reference])))
    sign[sign==0]=1.0
    return {
        "evalues_real":np.asarray(modal.evalues).real,
        "evalues_imag":np.asarray(modal.evalues).imag,
        "wn":np.asarray(modal.wn),
        "wd":np.asarray(modal.wd),
        "damping_ratio":np.asarray(modal.damping_ratio),
        "log_dec":np.asarray(modal.log_dec),
        "whirl_ratio":np.asarray(ratios,float),
        "mode_index":int(mode_index),
        "mode_frequency":float(modal.wd[mode_index]),
        "amplitude":amplitude,
        "reference_node":reference,
        "reference_major_angle":theta,
        "projection":projection,
        "sign":sign,
        "orbits":[{
            "major_axis":float(o.major_axis),
            "minor_axis":float(o.minor_axis),
            "kappa":float(o.kappa),
            "major_angle":float(o.major_angle),
            "ru_e":complex(o.ru_e),
            "rv_e":complex(o.rv_e),
        } for o in shape.orbits],
    }


def one_result(rotor,mode,speed,num_modes=12):
    result=rotor.api617_unbalance(
        mode=mode,maximum_continuous_speed=speed,num_modes=num_modes
    )
    return {
        "result":result,
        "journal_loads":rotor._journal_bearing_loads(),
        "rotor_mass":float(rotor.m),
        "nodes_pos":list(map(float,rotor.nodes_pos)),
        "modal":mode_evidence(rotor,speed,int(result["mode_index"]),num_modes),
    }


def explicit_case(rs,convert_6dof_to_4dof,rotor,mode,speed,num_modes=12):
    actual=one_result(rotor,mode,speed,num_modes)
    adapted=one_result(convert_6dof_to_4dof(rotor),mode,speed,num_modes)
    return {
        "input":{
            "mode":int(mode),
            "maximum_continuous_speed_rad_s":float(speed),
            "num_modes":int(num_modes),
        },
        "ross_6dof":actual,
        "ross_adapted_4dof":adapted,
    }


def generate(ross_root:Path,out:Path):
    root=ross_root.resolve()
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    if head!=ROSS_SHA:
        raise RuntimeError(f"ROSS authority mismatch: expected {ROSS_SHA}, got {head}")
    if out.exists():
        raise FileExistsError(f"refusing to overwrite immutable A7 authority: {out}")

    sys.path.insert(0,str(root))
    import numpy as np
    import scipy
    import ross as rs
    from ross.units import Q_
    from ross.utils import convert_6dof_to_4dof

    if Path(rs.__file__).resolve()!=root/"ross"/"__init__.py":
        raise RuntimeError("imported ROSS is not the frozen checkout")

    out.mkdir(parents=True)
    manifest={}

    std=standard_rotor(rs)
    cases=[
        ("first_mode_9000rpm",std,0,Q_(9000,"RPM").to("rad/s").m),
        ("conical_mode_9000rpm",std,1,Q_(9000,"RPM").to("rad/s").m),
        ("below_boundary_24999rpm",std,0,Q_(24999,"RPM").to("rad/s").m),
        ("high_speed_25000rpm",std,0,Q_(25000,"RPM").to("rad/s").m),
        ("high_speed_30000rpm",std,0,Q_(30000,"RPM").to("rad/s").m),
        ("overhung_6000rpm",overhung_rotor(rs),0,Q_(6000,"RPM").to("rad/s").m),
        ("speed_dependent_9000rpm",speed_dependent_rotor(rs,np),0,Q_(9000,"RPM").to("rad/s").m),
        ("map_2d_9000rpm",map2d_rotor(rs,np),0,Q_(9000,"RPM").to("rad/s").m),
    ]
    for name,rotor,mode,speed in cases:
        payload={"case":name,**explicit_case(rs,convert_6dof_to_4dof,rotor,mode,speed)}
        path=out/f"{name}.json";write(path,payload);manifest[path.name]=digest(path)

    error={}
    for label,rotor in (
        ("six_dof",std),
        ("adapted_4dof",convert_6dof_to_4dof(std)),
    ):
        try:
            rotor.api617_unbalance(
                mode=20,maximum_continuous_speed=Q_(9000,"RPM"),num_modes=12
            )
        except Exception as exc:
            error[label]={"type":type(exc).__name__,"message":str(exc)}
        else:
            raise RuntimeError("mode=20 unexpectedly succeeded")
    path=out/"mode_not_available.json"
    write(path,{"case":"mode_not_available","error":error})
    manifest[path.name]=digest(path)

    authority_files=[
        "ross/rotor_assembly.py",
        "ross/results.py",
        "ross/utils.py",
        "ross/tests/test_results.py",
        "ross/agent_skills/ross/unbalance_response.md",
        "ross/agent_skills/ross/clearance_analysis.md",
    ]
    authority={
        "repository":"petrobras/ross",
        "commit":ROSS_SHA,
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "python":platform.python_version(),
        "numpy":np.__version__,
        "scipy":scipy.__version__,
        "scope":"A7 API 617 unbalance placement immutable authority; actual ROSS plus declared 4-DOF adaptation",
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
