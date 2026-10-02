"""B2 frozen-authority helpers. Validation only; no production solver."""
from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
from typing import Any
import numpy as np

ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"
BASE_MAIN="d44ad24590f984e3f0655c427fcbf39be94a6da6"
B1_QUALIFIED_PARENT="35e8f26937aaa60d1ce3ccbb3a523f3c1e6a6d2f"
REPO_ROOT=Path(__file__).resolve().parents[2]
INPUT_PATH="validation/b2/cases.json"
POLICY_PATH="validation/b2/TOLERANCE_POLICY.json"
FROZEN_PATH="validation/ross_parity/6dof_global"
NODE_ORDER=["x","y","z","alpha","beta","theta"]
MANDATORY_SOURCES=[
 "ross/rotor_assembly.py","ross/results.py","ross/bearing_seal_element.py",
 "ross/shaft_element.py","ross/disk_element.py","ross/materials.py",
 "ross/element.py","ross/units.py","ross/new_units.txt",
]

def require(ok:bool,msg:str)->None:
    if not ok: raise ValueError(msg)

def sha256(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def file_hash(path:Path)->str:return sha256(path.read_bytes())
def canonical_bytes(v:Any)->bytes:return (json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()
def write_json(path:Path,v:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical_bytes(v))
def read_json(path:Path)->Any:
    return json.loads(path.read_text(encoding="utf-8"))

def run_bytes(args,cwd=None):
    p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=180)
    if p.returncode:
        raise RuntimeError(p.stdout.decode("utf-8","replace")+p.stderr.decode("utf-8","replace"))
    return p.stdout

def git(root:Path,*args:str)->bytes:return run_bytes(["git","-C",str(root),*args])
def head(root:Path)->str:return git(root,"rev-parse","HEAD").decode().strip()

def check_checkout(root:Path)->None:
    require(head(root)==ROSS_SHA,"wrong ROSS HEAD")
    require(not git(root,"status","--porcelain","--untracked-files=no").strip(),"ROSS checkout dirty")
    require(git(root,"config","--get","core.autocrlf").strip()==b"false","require autocrlf=false")
    require(git(root,"config","--get","core.eol").strip()==b"lf","require eol=lf")

def source_record(root:Path,path:str,role:str,module_paths=None)->dict:
    local=(root/path).resolve();require(local.is_file() and local.is_relative_to(root.resolve()),f"invalid source {path}")
    blob_id=git(root,"rev-parse",f"{ROSS_SHA}:{path}").decode().strip()
    raw=git(root,"cat-file","blob",blob_id);working=local.read_bytes()
    require(raw==working,f"source bytes changed: {path}")
    return {"path":path,"role":role,"git_commit":ROSS_SHA,"git_blob_id":blob_id,
            "git_blob_sha256":sha256(raw),"working_sha256":sha256(working),
            "runtime_paths":sorted(module_paths or [])}

def validate_spec(spec:dict)->None:
    require(spec["ross_sha"]==ROSS_SHA and spec["baseline_main"]==BASE_MAIN,"wrong authority baseline")
    require(spec["b1_qualified_parent"]==B1_QUALIFIED_PARENT,"wrong B1 parent")
    require(spec["node_dof_order"]==NODE_ORDER,"wrong DOF order")
    require(len(spec["matrix_cases"])==11 and len(spec["modal_cases"])==8 and len(spec["campbell_cases"])==4,"wrong case counts")
    for key,rotor in spec["rotors"].items():
        shafts=rotor["shafts"];require(shafts,f"{key}: no shafts")
        ns=sorted(int(s["n"]) for s in shafts)
        require(ns==list(range(len(shafts))),f"{key}: shafts must be consecutive 0-based")
        for s in shafts:
            require(float(s["L"])>0 and 0<=float(s["idl"])<float(s["odl"]) and 0<=float(s["idr"])<float(s["odr"]),f"{key}: invalid shaft")
        for b in rotor["bearings"]:
            for z in ("kzz","czz","mzz"):require(float(b.get(z,0.0))==0.0,f"{key}: B2 axial bearing term must be zero")
            require(b.get("n_link") is None,f"{key}: linked bearing not in scope")
    ids=[x["id"] for k in ("matrix_cases","modal_cases","campbell_cases") for x in spec[k]]
    require(len(ids)==len(set(ids)),"duplicate case id")

def save_array(root:Path,relative:str,value:Any,group:str,allow_nan:bool=False)->dict:
    arr=np.asarray(value)
    require(arr.dtype.kind in "fc",f"invalid array dtype {relative}: {arr.dtype}")
    require(not np.isinf(arr).any(),f"infinite value in {relative}")
    if allow_nan:
        require(group in {"modal_whirl","campbell_whirl"},f"NaN is not permitted for group {group}")
    else:
        require(np.isfinite(arr).all(),f"nonfinite value in {relative}")
    arr=np.array(arr,dtype=np.complex128 if arr.dtype.kind=="c" else np.float64,order="F",copy=True)
    path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
    require(not path.exists(),f"duplicate output {relative}")
    np.save(path,arr,allow_pickle=False)
    raw=path.read_bytes()
    return {"file":relative,"group":group,"shape":list(arr.shape),"dtype":str(arr.dtype),
            "sha256":sha256(raw),"nonzero":int(np.count_nonzero(arr))}

def snapshot(root:Path)->dict[str,str]:
    return {p.relative_to(root).as_posix():file_hash(p) for p in sorted(root.rglob("*")) if p.is_file()}
