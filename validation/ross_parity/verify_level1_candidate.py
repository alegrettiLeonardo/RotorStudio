"""Numerically reproduce the immutable A6 Level 1 ROSS authority.

The authority itself is never rewritten. A regenerated candidate from the exact
frozen ROSS SHA is compared with A6-specific tolerances. Zero-speed repeated
lateral eigenspaces are compared through invariant spectra and Level1Results
rather than arbitrary eigenvector/whirl bases.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"

TOL={
    "matrix":{"rtol":2e-11,"atol":2e-7},
    "eigen":{"rtol":3e-8,"atol":3e-7},
    "logdec":{"rtol":3e-8,"atol":3e-9},
    "selected_logdec":{"rtol":3e-8,"atol":3e-10},
    "q":{"rtol":0.0,"atol":1e-8},
}


def close(a,b,key,label):
    t=TOL[key]
    np.testing.assert_allclose(
        np.asarray(a,dtype=float),np.asarray(b,dtype=float),
        rtol=t["rtol"],atol=t["atol"],equal_nan=False,err_msg=label,
    )


def exact(a,b,label):
    if a!=b:
        raise ValueError(f"{label}: exact mismatch: {a!r} != {b!r}")


def load(path):
    return json.loads(Path(path).read_text())


def compare_point(ref,cand,name,index,zero_speed):
    if zero_speed:
        # ARPACK and DGEEV may choose/order different bases in repeated
        # zero-spin lateral eigenspaces. The physical eigenvalue magnitudes
        # and resulting Level1 curve are invariant.
        ra=np.sort(np.hypot(ref["evalues_real"],ref["evalues_imag"]))
        ca=np.sort(np.hypot(cand["evalues_real"],cand["evalues_imag"]))
        close(ra,ca,"eigen",f"{name}:point[{index}]:zero-speed spectrum")
        close(ref["wn"],cand["wn"],"eigen",f"{name}:point[{index}]:wn")
        close(ref["log_dec"],cand["log_dec"],"logdec",f"{name}:point[{index}]:logdec")
        return

    exact(ref["selected_index"],cand["selected_index"],f"{name}:point[{index}]:selected_index")
    exact(ref["directions"],cand["directions"],f"{name}:point[{index}]:directions")
    close(ref["evalues_real"],cand["evalues_real"],"eigen",f"{name}:point[{index}]:real")
    close(ref["evalues_imag"],cand["evalues_imag"],"eigen",f"{name}:point[{index}]:imag")
    close(ref["wn"],cand["wn"],"eigen",f"{name}:point[{index}]:wn")
    close(ref["wd"],cand["wd"],"eigen",f"{name}:point[{index}]:wd")
    close(ref["damping_ratio"],cand["damping_ratio"],"logdec",f"{name}:point[{index}]:zeta")
    close(ref["log_dec"],cand["log_dec"],"logdec",f"{name}:point[{index}]:logdec")
    close(ref["selected_kappa"],cand["selected_kappa"],"eigen",f"{name}:point[{index}]:kappa")


def compare_case(name,ref,cand):
    exact(ref["case"],cand["case"],f"{name}:case")
    exact(ref["input"],cand["input"],f"{name}:input")
    zero=float(ref["input"]["rated_w_rad_s"])==0.0

    close(ref["ross_level1"]["stiffness_range"],cand["ross_level1"]["stiffness_range"],"q",f"{name}:Q")
    close(ref["ross_level1"]["log_dec"],cand["ross_level1"]["log_dec"],"selected_logdec",f"{name}:ROSS Level1")

    r4=ref["ross_adapted_4dof"];c4=cand["ross_adapted_4dof"]
    close(r4["log_dec"],c4["log_dec"],"selected_logdec",f"{name}:adapted4 curve")
    if not zero:
        exact(r4["selected_index"],c4["selected_index"],f"{name}:selected indices")

    exact(len(r4["points"]),len(c4["points"]),f"{name}:point count")
    for i,(rp,cp) in enumerate(zip(r4["points"],c4["points"])):
        compare_point(rp,cp,name,i,zero)

    exact(len(r4["matrix_sentinels"]),len(c4["matrix_sentinels"]),f"{name}:sentinel count")
    for i,(rs,cs) in enumerate(zip(r4["matrix_sentinels"],c4["matrix_sentinels"])):
        exact(rs["index"],cs["index"],f"{name}:sentinel[{i}]:index")
        close([rs["Q"]],[cs["Q"]],"q",f"{name}:sentinel[{i}]:Q")
        for key in ("M","C","G","K"):
            close(rs[key],cs[key],"matrix",f"{name}:sentinel[{i}]:{key}")

    close(
        [ref["actual_vs_adapted_4dof_max_abs"]],
        [cand["actual_vs_adapted_4dof_max_abs"]],
        "selected_logdec",f"{name}:6dof-vs-4dof delta",
    )


def compare(reference:Path,candidate:Path):
    ra=load(reference/"authority.json")
    ca=load(candidate/"authority.json")
    exact(ra["commit"],ROSS_SHA,"reference commit")
    exact(ca["commit"],ROSS_SHA,"candidate commit")
    exact(ra["source_sha256"],ca["source_sha256"],"source hashes")
    exact(set(ra["golden_sha256"]),set(ca["golden_sha256"]),"golden case set")

    for filename in sorted(ra["golden_sha256"]):
        ref=load(reference/filename);cand=load(candidate/filename)
        if filename=="default_range_audit.json":
            exact(ref["case"],cand["case"],f"{filename}:case")
            exact(ref["integer_log10_k"],cand["integer_log10_k"],f"{filename}:log10")
            close(ref["effective_stiffness_range"],cand["effective_stiffness_range"],"q",f"{filename}:range")
            close(ref["log_dec"],cand["log_dec"],"selected_logdec",f"{filename}:curve")
        else:
            compare_case(filename[:-5],ref,cand)

    print("PASS: A6 frozen ROSS Level 1 authority reproduced within fixed numerical tolerances")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("reference",type=Path)
    p.add_argument("candidate",type=Path)
    args=p.parse_args()
    compare(args.reference,args.candidate)
