from __future__ import annotations
from dataclasses import dataclass,field,asdict,is_dataclass,replace
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
import hashlib,json,os,platform,sys
import numpy as np
from .domain.model import RotorModel
from .analysis.modal import run_modal
from .analysis.frequency_response import run_frequency_response,run_auxiliary_frequency_response,run_foundation_frequency_response
from .analysis.critical_speed import run_critical_speeds
from .analysis.coaxial import run_coaxial_modal,run_coaxial_frequency_response
from .analysis.asymmetric import run_asymmetric_modal,run_asymmetric_frequency_response
from .analysis.transient import run_foundation_time_response,run_runup

def _canonical(v:Any):
    if isinstance(v,dict): return {str(k):_canonical(v[k]) for k in sorted(v)}
    if isinstance(v,(list,tuple)): return [_canonical(x) for x in v]
    if hasattr(v,"tolist"): return _canonical(v.tolist())
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    return repr(v)

@dataclass(frozen=True)
class AnalysisCase:
    kind:str
    parameters:dict[str,Any]=field(default_factory=dict)
    name:str=""
    options:dict[str,Any]=field(default_factory=dict)
    def canonical_dict(self): return {"kind":self.kind,"name":self.name,"parameters":_canonical(self.parameters),"options":_canonical(self.options)}

@dataclass
class RotorProject:
    name:str
    model:RotorModel
    analyses:list[AnalysisCase]=field(default_factory=list)
    metadata:dict[str,Any]=field(default_factory=dict)
    created_utc:str=field(default_factory=lambda:datetime.now(timezone.utc).isoformat())
    def add_analysis(self,case): self.analyses.append(case)
    def canonical_dict(self): return {"name":self.name,"model":self.model.canonical_dict(),"analyses":[a.canonical_dict() for a in self.analyses],"metadata":_canonical(self.metadata)}
    def project_hash(self):
        return hashlib.sha256(json.dumps(self.canonical_dict(),sort_keys=True,separators=(",",":"),default=list).encode()).hexdigest()

def collect_build_metadata(library_path=None,options=None):
    lib=Path(library_path or os.environ.get("DRMROTOR_LIB","")) if (library_path or os.environ.get("DRMROTOR_LIB")) else None
    meta={"python":sys.version.split()[0],"platform":platform.platform(),"machine":platform.machine(),"backend":"Fortran2018/ctypes","options":dict(options or {})}
    try:
        from importlib.metadata import version
        meta["drm_core_version"]=version("drm-core")
    except Exception: meta["drm_core_version"]="unknown"
    if lib:
        meta["library_path"]=str(lib)
        if lib.is_file(): meta["library_sha256"]=hashlib.sha256(lib.read_bytes()).hexdigest()
    for key in ("FC","FFLAGS","CMAKE_BUILD_TYPE","BLA_VENDOR"):
        if os.environ.get(key):meta[key.lower()]=os.environ[key]
    return meta

def analysis_hash(model:RotorModel,case:AnalysisCase,build_options=None):
    payload={"model":model.canonical_dict(),"analysis":case.canonical_dict(),"build_options":_canonical(build_options or {})}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),default=list).encode()).hexdigest()

@dataclass(frozen=True)
class AnalysisExecution:
    case:AnalysisCase
    result:Any
    analysis_hash:str
    build_metadata:dict

class AnalysisService:
    """Application dispatcher. Numerical physics stays in the existing Fortran-backed API."""
    def __init__(self,library_path=None,build_options=None):
        self.library_path=library_path;self.build_options=dict(build_options or {})
    def execute(self,model:RotorModel|RotorProject,case:AnalysisCase):
        project=model if isinstance(model,RotorProject) else None
        model=project.model if project is not None else model
        p=dict(case.parameters);k=case.kind.strip().lower();lib=self.library_path
        if k=="modal": result=run_modal(model,library_path=lib,**p)
        elif k=="modal_sweep":
            speeds=np.asarray(p.pop("speeds_rad_s"),float)
            result=[run_modal(model,float(w),library_path=lib,**p) for w in speeds]
        elif k=="frequency_response": result=run_frequency_response(model,library_path=lib,**p)
        elif k=="auxiliary_frequency_response": result=run_auxiliary_frequency_response(model,library_path=lib,**p)
        elif k=="foundation_frequency_response": result=run_foundation_frequency_response(model,library_path=lib,**p)
        elif k=="critical_speeds": result=run_critical_speeds(model,library_path=lib,**p)
        elif k=="coaxial_modal": result=run_coaxial_modal(model,library_path=lib,**p)
        elif k=="coaxial_frequency_response": result=run_coaxial_frequency_response(model,library_path=lib,**p)
        elif k=="asymmetric_modal": result=run_asymmetric_modal(model,library_path=lib,**p)
        elif k=="asymmetric_frequency_response": result=run_asymmetric_frequency_response(model,library_path=lib,**p)
        elif k=="foundation_time_response": result=run_foundation_time_response(model,library_path=lib,**p)
        elif k=="runup": result=run_runup(model,library_path=lib,**p)
        elif k=="bearing_matrices":
            from .solver.facade import SolverFacade
            result=SolverFacade(lib).bearings(model,**p)
        else: raise ValueError(f"unsupported AnalysisCase.kind={case.kind!r}")
        effective_options={**self.build_options,**case.options}
        ah=analysis_hash(model,case,effective_options)
        meta=collect_build_metadata(lib,effective_options)
        meta["model_hash"]=model.model_hash()
        meta["analysis_hash"]=ah
        if project is not None:
            meta["project_hash"]=project.project_hash()
        def attach(value):
            if is_dataclass(value) and hasattr(value,"metadata"):
                merged=dict(getattr(value,"metadata") or {})
                merged.update({"analysis_hash":ah,"build":meta,"options":effective_options})
                return replace(value,metadata=merged)
            return value
        if isinstance(result,list):
            result=[attach(x) for x in result]
        else:
            result=attach(result)
        return AnalysisExecution(case,result,ah,meta)

def _legacy_payload(m:RotorModel):
    return {"node":[[n.number,n.z_m] for n in m.nodes],"shaft":[s.legacy_row() for s in m.shafts],
            "disc":[[d.disk_type,d.node,d.p3,d.p4,d.p5,d.p6] for d in m.disks],
            "bearing":[[b.bearing_type,b.node,*b.properties] for b in m.bearings],
            "force":[f.legacy_row() for f in m.forces],"bend":[[b.node,b.x_m,b.y_m] for b in m.bend],
            "rotors":[r.legacy_row() for r in m.rotors]}

def save_project(project:RotorProject,path):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps({"schema_version":1,"name":project.name,"created_utc":project.created_utc,"metadata":project.metadata,
                             "model":_legacy_payload(project.model),"analyses":[a.canonical_dict() for a in project.analyses]},indent=2,sort_keys=True))
    return p

def load_project(path):
    d=json.loads(Path(path).read_text());m=d["model"]
    model=RotorModel.from_legacy_arrays(m["node"],m["shaft"],m.get("disc",[]),m.get("bearing",[]),m.get("force",[]),m.get("bend",[]),m.get("rotors",[]))
    cases=[AnalysisCase(x["kind"],x.get("parameters",{}),x.get("name",""),x.get("options",{})) for x in d.get("analyses",[])]
    return RotorProject(d.get("name","Rotor project"),model,cases,d.get("metadata",{}),d.get("created_utc",""))

def _summary(v):
    if isinstance(v,np.ndarray):return {"shape":list(v.shape),"dtype":str(v.dtype)}
    if is_dataclass(v):return {k:_summary(x) for k,x in asdict(v).items()}
    if isinstance(v,dict):return {str(k):_summary(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [_summary(x) for x in v]
    return v if isinstance(v,(str,int,float,bool)) or v is None else repr(v)

def write_analysis_report(execution:AnalysisExecution,outdir,stem=None):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True);stem=stem or (execution.case.name or execution.case.kind)
    payload={"analysis_hash":execution.analysis_hash,"case":execution.case.canonical_dict(),"build_metadata":execution.build_metadata,"result":_summary(execution.result)}
    jp=out/f"{stem}.json";jp.write_text(json.dumps(payload,indent=2,sort_keys=True))
    mp=out/f"{stem}.md";mp.write_text("# Analysis report — "+stem+"\n\n- analysis hash: `"+execution.analysis_hash+"`\n- kind: `"+execution.case.kind+"`\n\n## Build/options metadata\n```json\n"+json.dumps(execution.build_metadata,indent=2,sort_keys=True)+"\n```\n")
    return {"json":jp,"markdown":mp}
