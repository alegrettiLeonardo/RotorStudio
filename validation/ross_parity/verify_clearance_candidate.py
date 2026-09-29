"""Numerically reproduce immutable A8 close-clearance authority.

A candidate is regenerated from the exact frozen ROSS SHA. The immutable A8
authority is not overwritten. Comparisons use A8-specific response tolerances;
global modal phase is removed from unbalance-phase comparison.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np

ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"


def load(path):return json.loads(Path(path).read_text())


def close(a,b,rtol,atol,label):
    np.testing.assert_allclose(
        np.asarray(a,dtype=float),np.asarray(b,dtype=float),
        rtol=rtol,atol=atol,equal_nan=False,err_msg=label,
    )


def relphase(v):
    a=np.asarray(v,dtype=float)
    return a if not a.size else np.mod(a-a[0],2*np.pi)


def compare_result(name,side,a,b):
    exact_keys=[
        "unbalance_node","probe_tags","probe_nodes","clearance_tags",
        "clearance_nodes","passed","scale_factor_cap","mode","mode_index",
    ]
    for key in exact_keys:
        if a[key]!=b[key]:
            raise AssertionError(f"{name}:{side}:{key} changed")

    close(a["speed_range"],b["speed_range"],0,2e-12,f"{name}:{side}:speed")
    close(a["unbalance_magnitude"],b["unbalance_magnitude"],2e-9,2e-13,f"{name}:{side}:U")
    close(relphase(a["unbalance_phase"]),relphase(b["unbalance_phase"]),0,2e-10,f"{name}:{side}:phase")
    close(a["probe_angles"],b["probe_angles"],0,2e-15,f"{name}:{side}:probe angle")
    close(a["probe_response"],b["probe_response"],5e-7,5e-11,f"{name}:{side}:probe response")
    close([a["vibration_limit"]],[b["vibration_limit"]],2e-12,2e-15,f"{name}:{side}:Avl")
    close([a["max_probe_amplitude"]],[b["max_probe_amplitude"]],5e-7,5e-11,f"{name}:{side}:Amax")
    close([a["scale_factor"]],[b["scale_factor"]],5e-7,5e-9,f"{name}:{side}:Scc")
    close(a["clearance_positions"],b["clearance_positions"],0,2e-15,f"{name}:{side}:position")
    close(a["diametral_clearance"],b["diametral_clearance"],2e-12,2e-15,f"{name}:{side}:diameter")
    close(a["clearance_limit"],b["clearance_limit"],2e-12,2e-15,f"{name}:{side}:limit")
    close(a["clearance_response"],b["clearance_response"],5e-7,5e-11,f"{name}:{side}:clearance response")
    close(a["max_clearance_response"],b["max_clearance_response"],5e-7,5e-11,f"{name}:{side}:max clearance")
    close(a["speed_at_max_response"],b["speed_at_max_response"],0,2e-12,f"{name}:{side}:speed at max")
    if a["mode_frequency"] is not None:
        close([a["mode_frequency"]],[b["mode_frequency"]],3e-8,3e-7,f"{name}:{side}:mode frequency")


def compare(reference:Path,candidate:Path):
    ra=load(reference/"authority.json");ca=load(candidate/"authority.json")
    if ra["commit"]!=ROSS_SHA or ca["commit"]!=ROSS_SHA:
        raise AssertionError("A8 frozen ROSS SHA mismatch")
    if ra["source_sha256"]!=ca["source_sha256"]:
        raise AssertionError("A8 frozen source hashes changed")
    if set(ra["golden_sha256"])!=set(ca["golden_sha256"]):
        raise AssertionError("A8 authority case set changed")

    for filename in sorted(ra["golden_sha256"]):
        a=load(reference/filename);b=load(candidate/filename)
        if a["case"]!=b["case"] or a["input"]!=b["input"]:
            raise AssertionError(f"{filename}: case/input changed")
        compare_result(filename,"ross_6dof",a["ross_6dof"],b["ross_6dof"])
        compare_result(filename,"ross_adapted_4dof",a["ross_adapted_4dof"],b["ross_adapted_4dof"])
    print("PASS: A8 frozen ROSS clearance authority reproduced within fixed physical tolerances")


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("reference",type=Path);p.add_argument("candidate",type=Path)
    a=p.parse_args();compare(a.reference,a.candidate)
