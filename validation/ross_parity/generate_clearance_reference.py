"""Freeze A8 API 617 close-clearance authority from exact ROSS.

Validation-only. Production A8 physics remains native Fortran.
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


def base_rotor(rs,np,*,map_backed=False):
    base=rs.rotor_example()
    if not map_backed:
        bearings=[
            rs.BearingElement(n=0,kxx=1e6,kyy=.8e6,cxx=1e3,cyy=1e3,radial_clearance=100e-6,tag="DE"),
            rs.BearingElement(n=6,kxx=1e6,kyy=.8e6,cxx=1e3,cyy=1e3,radial_clearance=120e-6,tag="NDE"),
            rs.SealElement(n=3,kxx=0,cxx=0,radial_clearance=250e-6,tag="eye"),
            rs.SealElement(n=2,kxx=0,cxx=0,tag="no_clearance"),
        ]
    else:
        sp=np.array([0.,300.,600.,900.,1200.])
        fr=sp.copy()
        gx=np.array([
            [.75e6,.78e6,.82e6,.86e6,.90e6],
            [.88e6,.92e6,.97e6,1.02e6,1.08e6],
            [1.02e6,1.07e6,1.13e6,1.20e6,1.28e6],
            [1.18e6,1.24e6,1.31e6,1.39e6,1.48e6],
            [1.36e6,1.43e6,1.51e6,1.60e6,1.70e6],
        ])
        gy=.83*gx+8e4
        gc=np.array([
            [1150.,1120.,1090.,1060.,1030.],
            [1100.,1070.,1040.,1010.,980.],
            [1050.,1020.,990.,960.,930.],
            [1000.,970.,940.,910.,880.],
            [950.,920.,890.,860.,830.],
        ])
        bearings=[
            rs.BearingElement(n=0,kxx=gx,kyy=gy,cxx=gc,cyy=.92*gc,speed=sp,frequency=fr,radial_clearance=100e-6,tag="DE"),
            rs.BearingElement(n=6,kxx=1.03*gx,kyy=1.02*gy,cxx=.97*gc,cyy=.95*gc,speed=sp,frequency=fr,radial_clearance=120e-6,tag="NDE"),
            rs.SealElement(n=3,kxx=0,cxx=0,radial_clearance=250e-6,tag="eye"),
        ]
    return rs.Rotor(copy.deepcopy(base.shaft_elements),copy.deepcopy(base.disk_elements),bearings)


def probes(rs):
    return [
        rs.Probe(0,np.deg2rad(45.),tag="DE-45"),
        rs.Probe(6,np.deg2rad(-45.),tag="NDE-45"),
        rs.Probe(3,direction="axial",tag="axial"),
    ]


def result_payload(result):
    return {
        "speed_range":result.speed_range,
        "minimum_allowable_speed":result.minimum_allowable_speed,
        "maximum_continuous_speed":result.maximum_continuous_speed,
        "unbalance_node":result.unbalance_node,
        "unbalance_magnitude":result.unbalance_magnitude,
        "unbalance_phase":result.unbalance_phase,
        "probe_tags":result.probe_tags,
        "probe_nodes":result.probe_nodes,
        "probe_angles":result.probe_angles,
        "probe_response":result.probe_response,
        "vibration_limit":result.vibration_limit,
        "max_probe_amplitude":result.max_probe_amplitude,
        "scale_factor":result.scale_factor,
        "clearance_tags":result.clearance_tags,
        "clearance_nodes":result.clearance_nodes,
        "clearance_positions":result.clearance_positions,
        "diametral_clearance":result.diametral_clearance,
        "clearance_limit":result.clearance_limit,
        "clearance_response":result.clearance_response,
        "max_clearance_response":result.max_clearance_response,
        "speed_at_max_response":result.speed_at_max_response,
        "passed":result.passed,
        "scale_factor_cap":result.scale_factor_cap,
        "mode":result.mode,
        "mode_index":result.mode_index,
        "mode_frequency":result.mode_frequency,
    }


def run_case(rs,np,convert,case):
    rotor=base_rotor(rs,np,map_backed=case.get("map_backed",False))
    adapted=convert(rotor)
    kwargs=dict(
        speed_range=np.asarray(case["speed_range"],float),
        minimum_allowable_speed=float(case["nma"]),
        maximum_continuous_speed=float(case["nmc"]),
        probes=probes(rs),
        mode=int(case.get("mode",0)),
        scale_factor_cap=case.get("cap"),
        num_modes=int(case.get("num_modes",12)),
    )
    if "explicit" in case:
        e=case["explicit"]
        kwargs.update(node=e["node"],unbalance_magnitude=e["magnitude"],unbalance_phase=e["phase"])
    return {
        "input":{
            "speed_range_rad_s":case["speed_range"],
            "minimum_allowable_speed_rad_s":case["nma"],
            "maximum_continuous_speed_rad_s":case["nmc"],
            "probe_nodes_zero_based":[0,6],
            "probe_nodes_one_based":[1,7],
            "probe_angles_rad":[float(np.deg2rad(45.)),float(np.deg2rad(-45.))],
            "clearance_nodes_zero_based":[0,3,6],
            "clearance_nodes_one_based":[1,4,7],
            "radial_clearance_m":[100e-6,250e-6,120e-6],
            "clearance_tags":["DE","eye","NDE"],
            "mode":case.get("mode",0),
            "scale_factor_cap":case.get("cap"),
            "num_modes":case.get("num_modes",12),
            "explicit_unbalance":case.get("explicit"),
        },
        "ross_6dof":result_payload(rotor.run_clearance_analysis(**kwargs)),
        "ross_adapted_4dof":result_payload(adapted.run_clearance_analysis(**kwargs)),
    }


def generate(ross_root:Path,out:Path):
    root=ross_root.resolve()
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
    if head!=ROSS_SHA:raise RuntimeError(f"ROSS authority mismatch: {head}")
    if out.exists():raise FileExistsError(f"refusing overwrite: {out}")
    sys.path.insert(0,str(root))
    import numpy as np
    import scipy
    import ross as rs
    from ross.units import Q_
    from ross.utils import convert_6dof_to_4dof
    if Path(rs.__file__).resolve()!=root/"ross"/"__init__.py":
        raise RuntimeError("wrong ROSS checkout")
    rpm=lambda x:Q_(x,"RPM").to("rad/s").m
    cases={
        "baseline_mode0":{
            "speed_range":np.linspace(0,rpm(10000),101),"nma":rpm(7000),"nmc":rpm(9000),
        },
        "conical_mode1":{
            "speed_range":np.linspace(0,rpm(10000),101),"nma":rpm(7000),"nmc":rpm(9000),"mode":1,
        },
        "high_speed_limit":{
            "speed_range":np.linspace(rpm(1000),rpm(25000),25),"nma":rpm(15000),"nmc":rpm(20000),
        },
        "cap_6":{
            "speed_range":np.linspace(0,rpm(10000),51),"nma":rpm(7000),"nmc":rpm(9000),"cap":6.0,
        },
        "operating_speed_insertion":{
            "speed_range":np.linspace(0,rpm(10000),11),"nma":rpm(6500),"nmc":rpm(8500),
        },
        "explicit_20_gmm":{
            "speed_range":np.linspace(0,rpm(10000),51),"nma":rpm(7000),"nmc":rpm(9000),
            "explicit":{"node":[3],"magnitude":[20e-6],"phase":[0.0]},
        },
        "explicit_80_gmm":{
            "speed_range":np.linspace(0,rpm(10000),51),"nma":rpm(7000),"nmc":rpm(9000),
            "explicit":{"node":[3],"magnitude":[80e-6],"phase":[0.0]},
        },
        "map_2d":{
            "speed_range":np.linspace(0,rpm(10000),61),"nma":rpm(7000),"nmc":rpm(9000),"map_backed":True,
        },
    }
    out.mkdir(parents=True);manifest={}
    for name,case in cases.items():
        payload={"case":name,**run_case(rs,np,convert_6dof_to_4dof,case)}
        path=out/f"{name}.json";write(path,payload);manifest[path.name]=digest(path)

    authority_files=[
        "ross/rotor_assembly.py","ross/results.py","ross/bearing_seal_element.py",
        "ross/probe.py","ross/utils.py","ross/tests/test_results.py",
        "ross/agent_skills/ross/clearance_analysis.md",
    ]
    authority={
        "repository":"petrobras/ross","commit":ROSS_SHA,
        "generated_utc":datetime.now(timezone.utc).isoformat(),
        "python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__,
        "scope":"A8 API 617 clearance immutable authority; actual ROSS plus declared 4-DOF adaptation",
        "source_sha256":{name:digest(root/name) for name in authority_files},
        "golden_sha256":manifest,
    }
    write(out/"authority.json",authority)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--ross-root",type=Path,required=True);p.add_argument("--out",type=Path,required=True)
    a=p.parse_args();generate(a.ross_root,a.out)
