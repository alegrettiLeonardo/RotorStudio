"""Verify B2 ROSS authority candidates or frozen authority without regenerating."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
from validation.b2.authority_common import *

def load(root:Path):
    root=root.resolve();a=read_json(root/"authority.json")
    require(a["ross_sha"]==ROSS_SHA,"wrong ROSS SHA")
    require(a["input_sha256"]==file_hash(root/"input_specification.json"),"input hash mismatch")
    require(a["policy_sha256"]==file_hash(root/"tolerances.json"),"policy hash mismatch")
    require(a["case_counts"]=={"global":11,"modal":8,"campbell":4},"case count mismatch")
    arrays={}
    for rec in a["arrays"]:
        p=root/rec["file"];require(p.is_file(),f"missing {rec['file']}");require(file_hash(p)==rec["sha256"],f"hash mismatch {rec['file']}")
        x=np.load(p,allow_pickle=False);require(list(x.shape)==rec["shape"] and str(x.dtype)==rec["dtype"],f"descriptor mismatch {rec['file']}")
        require(np.isfinite(x).all(),f"nonfinite {rec['file']}");arrays[rec["file"]]=x
    for rel,h in a.get("metadata_files",{}).items():
        require(file_hash(root/rel)==h,f"metadata hash mismatch {rel}")
    return a,arrays

def closeness(x,y,rtol,atol,zero=False):
    if x.shape!=y.shape:return False,{"shape":False}
    if zero and not np.array_equal(x==0,y==0):return False,{"zero_pattern":False}
    d=np.abs(x-y);tol=atol+rtol*np.abs(x)
    ok=bool(np.all(d<=tol))
    return ok,{"max_abs":float(d.max(initial=0.0)),"max_rel":float(np.max(np.divide(d,np.abs(x),out=np.zeros_like(d,dtype=float),where=np.abs(x)>0),initial=0.0))}

def mac(u,v):
    den=float(np.vdot(u,u).real*np.vdot(v,v).real)
    return float(abs(np.vdot(u,v))**2/den) if den>0 else 0.0

def compare(reference:Path,candidate:Path,report:Path|None=None):
    ar,R=load(reference);ac,C=load(candidate)
    require(ar["input_sha256"]==ac["input_sha256"] and ar["policy_sha256"]==ac["policy_sha256"],"candidate spec/policy differs")
    require(set(R)==set(C),"array inventory differs")
    policy=read_json(reference/"tolerances.json");rows=[];overall=True
    for rec in ar["arrays"]:
        name=rec["file"];g=rec["group"];x=R[name];y=C[name];ok=True;detail={}
        if g.startswith("matrix_"):
            key=g.split("_",1)[1];p=policy["matrix"][key];ok,detail=closeness(x,y,p["rtol"],p["atol"],p.get("exact_zero_pattern",False))
        elif g=="modal_eigen":
            pr=policy["modal"]["eigenvalue_real"];pi=policy["modal"]["eigenvalue_imag"]
            okr,dr=closeness(x.real,y.real,pr["rtol"],pr["atol"]);oki,di=closeness(x.imag,y.imag,pi["rtol"],pi["atol"]);ok=okr and oki;detail={"real":dr,"imag":di}
        elif g=="modal_evec":
            require(x.shape==y.shape,f"evec shape {name}");vals=[mac(x[:,j],y[:,j]) for j in range(x.shape[1])];m=min(vals,default=1.0)
            ok=m>=policy["modal"]["eigenvector_mac_min"];detail={"min_mac":m}
        elif g in ("modal_wn","modal_wd","modal_damping","modal_logdec"):
            k={"modal_wn":"wn","modal_wd":"wd","modal_damping":"damping_ratio","modal_logdec":"log_dec"}[g];p=policy["modal"][k];ok,detail=closeness(x,y,p["rtol"],p["atol"])
        elif g=="modal_residual":
            m=max(float(np.max(x,initial=0)),float(np.max(y,initial=0)));ok=m<=policy["modal"]["residual_max"];detail={"max":m}
        elif g=="modal_whirl" or g=="campbell_whirl":
            ok=bool(np.array_equal(np.isnan(x),np.isnan(y)) and np.allclose(x,y,rtol=0,atol=0,equal_nan=True))
        elif g.startswith("campbell_") and g not in ("campbell_tracking_mac","campbell_tracking_assignment"):
            k=g.split("_",1)[1]
            if k=="speed":ok=bool(np.array_equal(x,y));detail={}
            else:p=policy["campbell"][k];ok,detail=closeness(x,y,p["rtol"],p["atol"])
        elif g=="campbell_tracking_mac":
            ok,detail=closeness(x,y,1e-8,1e-10)
        elif g=="campbell_tracking_assignment":
            ok=bool(np.array_equal(x,y));detail={}
        else:raise ValueError("unhandled group "+g)
        rows.append({"file":name,"group":g,"status":"PASS" if ok else "FAIL",**detail});overall &= ok
    # non-array mode/tracking metadata must match except environment/provenance files.
    for pattern in ("modal/*_mode_types.json","campbell/*_mode_types.json","campbell/*_tracking.json"):
        for p in reference.glob(pattern):
            q=candidate/p.relative_to(reference);require(q.is_file(),f"missing {q}")
            if read_json(p)!=read_json(q):overall=False;rows.append({"file":p.relative_to(reference).as_posix(),"status":"FAIL","metadata_equal":False})
    result={"status":"PASS" if overall else "FAIL","reference_head":ar["generator_head"],"candidate_head":ac["generator_head"],
            "array_count":len(rows),"rows":rows}
    if report:write_json(report,result)
    require(overall,"B2 candidate comparison failed")
    return result

def self_check(root:Path):
    a,arrays=load(root);policy=read_json(root/"tolerances.json")
    residual=[np.max(x,initial=0) for n,x in arrays.items() if any(r["file"]==n and r["group"]=="modal_residual" for r in a["arrays"])]
    require(max(residual,default=0)<=policy["modal"]["residual_max"],"modal residual gate failed")
    tracks=[]
    for p in root.glob("campbell/*_tracking.json"):
        for station in read_json(p):tracks.extend(station["assignment_mac"])
    require(min(tracks,default=1.0)>=policy["campbell"]["tracking_mac_min"],"Campbell tracking MAC below frozen threshold")
    return {"status":"PASS","arrays":len(arrays),"max_modal_residual":max(residual,default=0),"min_tracking_assignment_mac":min(tracks,default=1.0),
            "data_bundle_sha256":a["data_bundle_sha256"]}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--reference",type=Path);p.add_argument("--candidate",type=Path,required=True);p.add_argument("--report",type=Path)
    a=p.parse_args()
    result=self_check(a.candidate) if a.reference is None else compare(a.reference,a.candidate,a.report)
    print("B2_AUTHORITY_VERIFY",json.dumps(result,sort_keys=True))
