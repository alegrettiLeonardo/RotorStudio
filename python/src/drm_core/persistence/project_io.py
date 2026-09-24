from __future__ import annotations
from dataclasses import asdict
import json
from pathlib import Path
from drm_core.domain.model import Node,ShaftElement,TaperedShaftElement,AsymmetricShaftElement,Disk,Bearing,Seal,Force,BendPoint,RotorDefinition,RotorModel
from drm_core.domain.project import RotorProject,AnalysisCase

def _model_to_dict(m:RotorModel):
    def tagged(x): return {'type':type(x).__name__,'data':asdict(x)}
    return {k:[tagged(x) for x in getattr(m,k)] for k in ('nodes','shafts','disks','bearings','forces','bend','rotors')}

_CLASSES={c.__name__:c for c in (Node,ShaftElement,TaperedShaftElement,AsymmetricShaftElement,Disk,Bearing,Seal,Force,BendPoint,RotorDefinition)}
def _model_from_dict(d):
    vals={}
    for k,items in d.items(): vals[k]=[_CLASSES[item['type']](**item['data']) for item in items]
    return RotorModel(**vals)

def save_project(project:RotorProject,path):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    data={'schema_version':project.schema_version,'name':project.name,'model':_model_to_dict(project.model),'analyses':[asdict(a) for a in project.analyses],'metadata':project.metadata}
    p.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding='utf-8');return p

def load_project(path)->RotorProject:
    d=json.loads(Path(path).read_text(encoding='utf-8'))
    return RotorProject(d['name'],_model_from_dict(d['model']),[AnalysisCase(**a) for a in d.get('analyses',[])],d.get('metadata',{}),d.get('schema_version',1))
