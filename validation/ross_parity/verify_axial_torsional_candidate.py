"""Verify B3 axial/torsional authority candidates or frozen authority."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
from validation.b3.authority_common import *

def load(root:Path):
    root=root.resolve();a=read_json(root/"authority.json")
    require(a["ross_sha"]==ROSS_SHA,"wrong ROSS SHA")
    require(a["input_sha256"]==file_hash(root/"cases.json"),"B3 case hash mismatch")
    require(a["policy_sha256"]==file_hash(root/"tolerances.json"),"B3 policy hash mismatch")
    require(a["rotor_spec_sha256"]==file_hash(root/"rotor_specification.json"),"B3 rotor spec hash mismatch")
    require(a["case_counts"]=={"modal":6,"sweep":2},"B3 case count mismatch")
    arrays={}
    for rec in a["arrays"]:
        p=root/rec["file"];require(p.is_file(),f"missing {rec['file']}")
        require(file_hash(p)==rec["sha256"],f"hash mismatch {rec['file']}")
        x=np.load(p,allow_pickle=False)
        require(list(x.shape)==rec["shape"] and str(x.dtype)==rec["dtype"],f"descriptor mismatch {rec['file']}")
        require(np.isfinite(x).all(),f"nonfinite {rec['file']}")
        arrays[rec["file"]]=x
    for rel,h in a.get("metadata_files",{}).items():
        require(file_hash(root/rel)==h,f"metadata hash mismatch {rel}")
    return a,arrays

def close(x,y,rtol,atol):
    if x.shape!=y.shape:return False,{"shape":False}
    d=np.abs(x-y);ok=bool(np.all(d<=atol+rtol*np.abs(x)))
    return ok,{"max_abs":float(d.max(initial=0.0))}

def mac(u,v):
    den=float(np.vdot(u,u).real*np.vdot(v,v).real)
    return float(abs(np.vdot(u,v))**2/den) if den>0 else 0.0

def compare(reference:Path,candidate:Path,report:Path|None=None):
    ar,R=load(reference);ac,C=load(candidate)
    require(ar["input_sha256"]==ac["input_sha256"],"B3 cases differ")
    require(ar["policy_sha256"]==ac["policy_sha256"],"B3 policy differs")
    require(ar["rotor_spec_sha256"]==ac["rotor_spec_sha256"],"B3 rotor model source differs")
    require(set(R)==set(C),"B3 array inventory differs")
    p=read_json(reference/"tolerances.json");rows=[];overall=True
    for rec in ar["arrays"]:
        name=rec["file"];group=rec["group"];x=R[name];y=C[name];ok=True;detail={}
        if "_matrix_" in group:
            key=group.rsplit("_",1)[1];t=p["matrix"][key];ok,detail=close(x,y,t["rtol"],t["atol"])
        elif group.endswith("_modal_eigen"):
            tr=p["modal"]["eigenvalue_real"];ti=p["modal"]["eigenvalue_imag"]
            a,dr=close(x.real,y.real,tr["rtol"],tr["atol"]);b,di=close(x.imag,y.imag,ti["rtol"],ti["atol"])
            ok=a and b;detail={"real":dr,"imag":di}
        elif group.endswith("_modal_evec") or group.endswith("_modal_evec_normalized"):
            require(x.shape==y.shape,f"evec shape mismatch {name}")
            scores=[mac(x[:,j],y[:,j]) for j in range(x.shape[1])]
            score=min(scores,default=1.0);ok=score>=p["modal"]["eigenvector_mac_min"];detail={"min_mac":score}
        elif group.endswith("_modal_residual"):
            m=max(float(np.max(x,initial=0.0)),float(np.max(y,initial=0.0)))
            ok=m<=p["modal"]["residual_max"];detail={"max":m}
        elif group.endswith("_modal_indices") or group.endswith("_sweep_speed"):
            ok=bool(np.array_equal(x,y))
        elif group.endswith("_modal_wn") or group.endswith("_modal_wd"):
            key="wn" if group.endswith("_wn") else "wd";t=p["modal"][key];ok,detail=close(x,y,t["rtol"],t["atol"])
        elif group.endswith("_modal_damping") or group.endswith("_modal_logdec"):
            key="damping_ratio" if group.endswith("_damping") else "log_dec";t=p["modal"][key];ok,detail=close(x,y,t["rtol"],t["atol"])
        elif group.endswith("_sweep_wn") or group.endswith("_sweep_wd"):
            key="wn" if group.endswith("_wn") else "wd";t=p["sweep"][key];ok,detail=close(x,y,t["rtol"],t["atol"])
        elif group.endswith("_sweep_damping") or group.endswith("_sweep_logdec"):
            key="damping_ratio" if group.endswith("_damping") else "log_dec";t=p["sweep"][key];ok,detail=close(x,y,t["rtol"],t["atol"])
        else:
            raise ValueError("unhandled B3 authority group "+group)
        rows.append({"file":name,"group":group,"status":"PASS" if ok else "FAIL",**detail});overall &= ok
    result={"status":"PASS" if overall else "FAIL","reference_head":ar["generator_head"],
            "candidate_head":ac["generator_head"],"array_count":len(rows),"rows":rows}
    if report:write_json(report,result)
    require(overall,"B3 candidate comparison failed")
    return result

def self_check(root:Path):
    a,arrays=load(root);p=read_json(root/"tolerances.json")
    residual=[float(np.max(v,initial=0.0)) for k,v in arrays.items() if k.endswith("_residual.npy")]
    require(max(residual,default=0.0)<=p["modal"]["residual_max"],"B3 residual gate failed")
    require(float(a["max_decoupling_ratio"])<=p["decoupling"]["relative_frobenius_max"],"B3 decoupling gate failed")
    return {"status":"PASS","arrays":len(arrays),"max_modal_residual":max(residual,default=0.0),
            "max_decoupling_ratio":float(a["max_decoupling_ratio"]),"data_bundle_sha256":a["data_bundle_sha256"]}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--reference",type=Path)
    p.add_argument("--candidate",type=Path,required=True)
    p.add_argument("--report",type=Path)
    a=p.parse_args()
    result=self_check(a.candidate) if a.reference is None else compare(a.reference,a.candidate,a.report)
    print("B3_AUTHORITY_VERIFY",json.dumps(result,sort_keys=True))
