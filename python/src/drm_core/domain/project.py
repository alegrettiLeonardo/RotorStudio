from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any
from .model import RotorModel
from drm_core.provenance import stable_hash

@dataclass(frozen=True)
class AnalysisCase:
    name:str
    analysis_type:str
    options:dict[str,Any]=field(default_factory=dict)
    def analysis_hash(self)->str:
        return stable_hash({'name':self.name,'analysis_type':self.analysis_type,'options':self.options})

@dataclass
class RotorProject:
    name:str
    model:RotorModel
    analyses:list[AnalysisCase]=field(default_factory=list)
    metadata:dict[str,Any]=field(default_factory=dict)
    schema_version:int=1
    def project_hash(self)->str:
        return stable_hash({'schema_version':self.schema_version,'name':self.name,'model':self.model.canonical_dict(),'analyses':[asdict(a) for a in self.analyses],'metadata':self.metadata})
    def get_analysis(self,name:str)->AnalysisCase:
        for a in self.analyses:
            if a.name==name:return a
        raise KeyError(name)
