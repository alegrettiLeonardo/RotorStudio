"""Compare a regenerated frozen-ROSS A5 candidate to immutable UCS goldens.

ROSS run_modal uses ARPACK, so byte identity of floating JSON is not a valid
reproducibility criterion. Inputs/source hashes remain exact; numerical outputs
use the same pre-closure A5 tolerances as production parity.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np

from verify_reference import verify

WN={"rtol":2e-8,"atol":2e-6}
K={"rtol":2e-12,"atol":1e-6}
BEARING={"rtol":2e-10,"atol":1e-5}
INTK={"rtol":2e-7,"atol":2e-2}
INTS={"rtol":2e-7,"atol":2e-5}
CRIT={"rtol":3e-8,"atol":3e-6}
MATRIX={"rtol":2e-12,"atol":2e-12}


def close(a,b,tol,label):
    np.testing.assert_allclose(
        np.asarray(a,float),np.asarray(b,float),
        rtol=tol["rtol"],atol=tol["atol"],equal_nan=False,err_msg=label
    )


def exact(a,b,label):
    if a!=b:
        raise ValueError(f"{label}: exact metadata/input mismatch: {a!r} != {b!r}")


def compare_case(name,ref,cand):
    exact(ref.get("case"),cand.get("case"),f"{name}:case")
    if "input" in ref:
        exact(ref["input"],cand.get("input"),f"{name}:input")
    exact(ref.get("rotor_wn_shape"),cand.get("rotor_wn_shape"),f"{name}:shape")
    exact(ref.get("coefficients_processed"),cand.get("coefficients_processed"),f"{name}:coefficients")

    if "stiffness_range_effective" in ref:
        exact(ref["stiffness_range_effective"],cand.get("stiffness_range_effective"),f"{name}:effective_range")
    close(ref["stiffness_log"],cand["stiffness_log"],K,f"{name}:stiffness_log")

    # The dedicated logspace golden is a semantic grid sentinel; its modal
    # values are exercised by the other authority cases and not reused here as
    # a second ARPACK tolerance gate.
    if name!="logspace_gate":
        close(ref["rotor_wn"],cand["rotor_wn"],WN,f"{name}:rotor_wn")
        if "bearing_speed_range" in ref:
            close(ref["bearing_speed_range"],cand["bearing_speed_range"],WN,f"{name}:bearing_speed")
        if "bearing_kxx" in ref:
            close(ref["bearing_kxx"],cand["bearing_kxx"],BEARING,f"{name}:kxx")
            close(ref["bearing_kyy"],cand["bearing_kyy"],BEARING,f"{name}:kyy")
        if "intersection_x" in ref:
            close(ref["intersection_x"],cand["intersection_x"],INTK,f"{name}:intersection_x")
            close(ref["intersection_y"],cand["intersection_y"],INTS,f"{name}:intersection_y")

        rc=ref.get("critical_modal",[])
        cc=cand.get("critical_modal",[])
        if len(rc)!=len(cc):
            raise ValueError(f"{name}: critical modal count mismatch")
        for i,(x,y) in enumerate(zip(rc,cc)):
            close(x["wn"],y["wn"],CRIT,f"{name}:critical[{i}].wn")
            close(x["wd"],y["wd"],CRIT,f"{name}:critical[{i}].wd")
            close(x["evalues_real"],y["evalues_real"],CRIT,f"{name}:critical[{i}].evalues_real")
            close(x["evalues_imag"],y["evalues_imag"],CRIT,f"{name}:critical[{i}].evalues_imag")
            close(x["damping_ratio"],y["damping_ratio"],CRIT,f"{name}:critical[{i}].zeta")
            close(x["log_dec"],y["log_dec"],CRIT,f"{name}:critical[{i}].logdec")
            close([x["speed"]],[y["speed"]],INTS,f"{name}:critical[{i}].speed")

        rs=ref.get("matrix_sentinels",[])
        cs=cand.get("matrix_sentinels",[])
        if len(rs)!=len(cs):
            raise ValueError(f"{name}: matrix sentinel count mismatch")
        for i,(x,y) in enumerate(zip(rs,cs)):
            exact(x["index"],y["index"],f"{name}:matrix[{i}].index")
            close([x["stiffness"]],[y["stiffness"]],K,f"{name}:matrix[{i}].stiffness")
            close(x["M"],y["M"],MATRIX,f"{name}:matrix[{i}].M")
            close(x["C"],y["C"],MATRIX,f"{name}:matrix[{i}].C")
            close(x["G"],y["G"],MATRIX,f"{name}:matrix[{i}].G")
            close(x["K"],y["K"],K,f"{name}:matrix[{i}].K")
            close(x["modal_branch"],y["modal_branch"],WN,f"{name}:matrix[{i}].modal_branch")
            close([x["max_abs_C"]],[y["max_abs_C"]],MATRIX,f"{name}:matrix[{i}].max_abs_C")


def compare(reference:Path,candidate:Path):
    ra=verify(reference)
    ca=verify(candidate)
    exact(ra["commit"],ca["commit"],"commit")
    exact(ra["source_sha256"],ca["source_sha256"],"source_sha256")
    exact(set(ra["golden_sha256"]),set(ca["golden_sha256"]),"golden case set")

    for name in sorted(ra["golden_sha256"]):
        a=json.loads((reference/name).read_text())
        b=json.loads((candidate/name).read_text())
        if name=="intersection_sentinels.json":
            exact(set(a),set(b),name)
            for key in a:
                close(a[key]["x"],b[key]["x"],MATRIX,f"{name}:{key}:x")
                close(a[key]["y"],b[key]["y"],MATRIX,f"{name}:{key}:y")
        elif name=="ross_default_no_rated_speed.json":
            exact(a["case"],b["case"],f"{name}:case")
            exact(a["stiffness_range_effective"],b["stiffness_range_effective"],f"{name}:range")
            close(a["stiffness_log"],b["stiffness_log"],K,f"{name}:grid")
            close(a["rotor_wn"],b["rotor_wn"],WN,f"{name}:wn")
        else:
            compare_case(name[:-5],a,b)

    print("PASS: A5 frozen ROSS source/input authority reproduced within frozen numerical tolerances")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("reference",type=Path)
    p.add_argument("candidate",type=Path)
    args=p.parse_args()
    compare(args.reference,args.candidate)
