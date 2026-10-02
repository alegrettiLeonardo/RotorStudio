"""B3 axial/torsional frozen-authority helpers. Validation only."""
from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
from typing import Any
import numpy as np

ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"
BASE_MAIN="c23a5e515480fa28fb6dd770fca235b73dd0198a"
B2_QUALIFIED_HEAD="491ae024beeb05a7e08f31ff48ef13c829da88d2"
REPO_ROOT=Path(__file__).resolve().parents[2]
INPUT_PATH="validation/b3/cases.json"
POLICY_PATH="validation/b3/TOLERANCE_POLICY.json"
ROTOR_SPEC_PATH="validation/ross_parity/6dof_global/input_specification.json"
FROZEN_PATH="validation/ross_parity/axial_torsional"
NODE_ORDER=["x","y","z","alpha","beta","theta"]
MANDATORY_SOURCES=[
 "ross/rotor_assembly.py","ross/results.py","ross/utils.py",
 "ross/bearing_seal_element.py","ross/shaft_element.py","ross/disk_element.py",
 "ross/materials.py","ross/element.py","ross/units.py","ross/new_units.txt",
]

def require(ok:bool,msg:str)->None:
    if not ok: raise ValueError(msg)

def sha256(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def file_hash(path:Path)->str:return sha256(path.read_bytes())
def canonical_bytes(v:Any)->bytes:return (json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()
def write_json(path:Path,v:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical_bytes(v))
def read_json(path:Path)->Any:return json.loads(path.read_text(encoding="utf-8"))

def run_bytes(args,cwd=None):
    p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=240)
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
    require(spec["ross_sha"]==ROSS_SHA,"wrong ROSS SHA")
    require(spec["baseline_main"]==BASE_MAIN,"wrong B3 baseline")
    require(spec["b2_qualified_head"]==B2_QUALIFIED_HEAD,"wrong B2 qualified head")
    require(spec["node_dof_order"]==NODE_ORDER,"wrong DOF order")
    require(spec["rotor_specification"]==ROTOR_SPEC_PATH,"wrong rotor authority path")
    require(len(spec["modal_cases"])==6 and len(spec["sweep_cases"])==2,"wrong B3 case counts")
    ids=[c["id"] for c in spec["modal_cases"]+spec["sweep_cases"]]
    require(len(ids)==len(set(ids)),"duplicate B3 case id")
    for c in spec["modal_cases"]+spec["sweep_cases"]:
        require(c["family"] in {"Axial","Torsional"},f"{c['id']}: invalid family")
        require(int(c["expected_modes"])>=1,f"{c['id']}: invalid expected mode count")
    for c in spec["sweep_cases"]:
        s=np.asarray(c["speed_range_rad_s"],float)
        require(s.ndim==1 and len(s)>=2 and np.isfinite(s).all() and np.all(np.diff(s)>0),
                f"{c['id']}: invalid speed grid")

def family_dofs(ndof:int,family:str)->np.ndarray:
    offset={"Axial":2,"Torsional":5}[family]
    return np.arange(offset,ndof,6,dtype=int)

def complement(ndof:int,selected:np.ndarray)->np.ndarray:
    mask=np.ones(ndof,dtype=bool);mask[selected]=False
    return np.flatnonzero(mask)

def decoupling_ratio(A:np.ndarray,selected:np.ndarray)->float:
    other=complement(A.shape[0],selected)
    if not len(other):return 0.0
    cross=np.linalg.norm(A[np.ix_(selected,other)],ord="fro")+np.linalg.norm(A[np.ix_(other,selected)],ord="fro")
    scale=max(1.0,float(np.linalg.norm(A,ord="fro")))
    return float(cross/scale)

def save_array(root:Path,relative:str,value:Any,group:str)->dict:
    arr=np.asarray(value)
    require(arr.dtype.kind in "fc",f"invalid array dtype {relative}: {arr.dtype}")
    require(np.isfinite(arr).all(),f"nonfinite value in {relative}")
    arr=np.array(arr,dtype=np.complex128 if arr.dtype.kind=="c" else np.float64,order="F",copy=True)
    path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
    require(not path.exists(),f"duplicate output {relative}")
    np.save(path,arr,allow_pickle=False)
    return {"file":relative,"group":group,"shape":list(arr.shape),"dtype":str(arr.dtype),
            "sha256":sha256(path.read_bytes()),"nonzero":int(np.count_nonzero(arr))}
