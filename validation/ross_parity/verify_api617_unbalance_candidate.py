"""Reproduce immutable A7 API 617 unbalance authority numerically.

The frozen authority is never rewritten. A candidate is regenerated from the
exact ROSS SHA and compared using A7-specific physical invariants. Global modal
phase and the reference end of a symmetric conical mode are intentionally not
treated as observables.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np

ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"


def load(path):
    return json.loads(Path(path).read_text())


def close(a,b,*,rtol=3e-8,atol=3e-9,label=""):
    np.testing.assert_allclose(
        np.asarray(a,dtype=float),np.asarray(b,dtype=float),
        rtol=rtol,atol=atol,equal_nan=False,err_msg=label,
    )


def phase_invariant(values):
    a=np.asarray(values,dtype=float)
    if not a.size:return a
    return np.mod(a-a[0],2*np.pi)


def compare_side(name,side,ref,cand):
    rr=ref["result"];cr=cand["result"]
    if rr["node"]!=cr["node"]:
        raise AssertionError(f"{name}:{side}: placement nodes differ")
    if int(rr["mode_index"])!=int(cr["mode_index"]):
        raise AssertionError(f"{name}:{side}: raw mode index differs")

    close(rr["unbalance_magnitude"],cr["unbalance_magnitude"],rtol=2e-9,atol=2e-13,label=f"{name}:{side}:magnitude")
    close(rr["static_load"],cr["static_load"],rtol=2e-9,atol=2e-9,label=f"{name}:{side}:static load")
    close([rr["mode_frequency"]],[cr["mode_frequency"]],rtol=3e-8,atol=3e-7,label=f"{name}:{side}:mode frequency")
    close(phase_invariant(rr["unbalance_phase"]),phase_invariant(cr["unbalance_phase"]),rtol=0,atol=2e-10,label=f"{name}:{side}:relative phase")

    if set(ref["journal_loads"])!=set(cand["journal_loads"]):
        raise AssertionError(f"{name}:{side}: journal support set differs")
    for key in ref["journal_loads"]:
        close([ref["journal_loads"][key]],[cand["journal_loads"][key]],rtol=2e-9,atol=2e-9,label=f"{name}:{side}:journal {key}")
    close([ref["rotor_mass"]],[cand["rotor_mass"]],rtol=2e-12,atol=2e-10,label=f"{name}:{side}:rotor mass")

    rm=ref["modal"];cm=cand["modal"]
    close(rm["evalues_real"],cm["evalues_real"],rtol=3e-8,atol=3e-7,label=f"{name}:{side}:eig real")
    close(rm["evalues_imag"],cm["evalues_imag"],rtol=3e-8,atol=3e-7,label=f"{name}:{side}:eig imag")
    close(rm["wd"],cm["wd"],rtol=3e-8,atol=3e-7,label=f"{name}:{side}:wd")
    close(rm["whirl_ratio"],cm["whirl_ratio"],rtol=3e-7,atol=3e-8,label=f"{name}:{side}:whirl ratio")

    ra=np.asarray(rm["amplitude"],dtype=float);ca=np.asarray(cm["amplitude"],dtype=float)
    if ra.max()>0:ra=ra/ra.max()
    if ca.max()>0:ca=ca/ca.max()
    close(ra,ca,rtol=4e-7,atol=4e-8,label=f"{name}:{side}:normalized major axis")


def compare_case(name,ref,cand):
    if ref["case"]!=cand["case"] or ref["input"]!=cand["input"]:
        raise AssertionError(f"{name}: case/input changed")
    compare_side(name,"ross_6dof",ref["ross_6dof"],cand["ross_6dof"])
    compare_side(name,"ross_adapted_4dof",ref["ross_adapted_4dof"],cand["ross_adapted_4dof"])


def compare(reference:Path,candidate:Path):
    ra=load(reference/"authority.json");ca=load(candidate/"authority.json")
    if ra["commit"]!=ROSS_SHA or ca["commit"]!=ROSS_SHA:
        raise AssertionError("A7 frozen ROSS SHA mismatch")
    if ra["source_sha256"]!=ca["source_sha256"]:
        raise AssertionError("A7 frozen ROSS source hashes changed")
    if set(ra["golden_sha256"])!=set(ca["golden_sha256"]):
        raise AssertionError("A7 authority case set changed")

    for filename in sorted(ra["golden_sha256"]):
        ref=load(reference/filename);cand=load(candidate/filename)
        if filename=="mode_not_available.json":
            if set(ref["error"])!=set(cand["error"]):
                raise AssertionError("A7 unavailable-mode authority sides changed")
            for side in ref["error"]:
                if ref["error"][side]["type"]!=cand["error"][side]["type"]:
                    raise AssertionError(f"A7 unavailable-mode exception type changed: {side}")
                if "forward modes" not in cand["error"][side]["message"]:
                    raise AssertionError(f"A7 unavailable-mode message lost physical guidance: {side}")
        else:
            compare_case(filename[:-5],ref,cand)

    print("PASS: A7 frozen ROSS API 617 unbalance authority reproduced within fixed physical tolerances")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("reference",type=Path)
    p.add_argument("candidate",type=Path)
    args=p.parse_args()
    compare(args.reference,args.candidate)
