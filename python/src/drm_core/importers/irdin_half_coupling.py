"""I14 explicit half-coupling declaration for imported API 541 lateral work."""
from __future__ import annotations

from copy import deepcopy
import math

from drm_core.domain.model import HalfCoupling


I14_EXPLICIT="PASS_I14_EXPLICIT_HALF_COUPLING"
I14_NOT_APPLICABLE="NOT_APPLICABLE_I14_EXPLICIT"
I14_NOT_DECLARED="NOT_DECLARED"


def _project(project):
    if project.metadata.get("source_format")!="iRdin/VB6 INI":
        raise ValueError("I14 half-coupling declaration requires an imported iRdin project")
    return deepcopy(project)


def _component(q,value,record):
    readiness=q.metadata.setdefault("numerical_readiness",{})
    readiness.setdefault("components",{})["half_coupling"]=value
    q.metadata["api541_half_coupling_declaration"]=record
    return q


def declare_half_coupling(
    project,
    *,
    node:int,
    mass_kg:float,
    diametral_inertia_kgm2:float,
    polar_inertia_kgm2:float,
    tag:str="Motor half coupling",
    provenance:dict|None=None,
):
    q=_project(project)
    node=int(node)
    existing={int(n.number) for n in q.model.nodes}
    values=(float(mass_kg),float(diametral_inertia_kgm2),float(polar_inertia_kgm2))
    if node not in existing:
        raise ValueError(f"I14 half-coupling node {node} does not exist")
    if not all(math.isfinite(v) for v in values):
        raise ValueError("I14 half-coupling mass/inertias must be finite")
    if values[0]<=0.0 or values[1]<0.0 or values[2]<0.0:
        raise ValueError("I14 requires mass>0 and nonnegative Id/Ip")
    if q.model.half_couplings:
        raise ValueError("I14 initial declared scope permits exactly one motor half coupling")
    source=dict(provenance or {})
    source.setdefault("declaration","EXPLICIT_USER_OR_ENGINEERING_INPUT")
    source.setdefault("api541_role","MOTOR_HALF_COUPLING")
    q.model.half_couplings=[HalfCoupling(
        node=node,
        mass_kg=values[0],
        diametral_inertia_kgm2=values[1],
        polar_inertia_kgm2=values[2],
        tag=str(tag),
        provenance=source,
    )]
    return _component(q,I14_EXPLICIT,{
        "status":I14_EXPLICIT,
        "applicable":True,
        "node":node,
        "mass_kg":values[0],
        "diametral_inertia_kgm2":values[1],
        "polar_inertia_kgm2":values[2],
        "tag":str(tag),
        "provenance":source,
    })


def declare_half_coupling_not_applicable(project,*,reason:str):
    q=_project(project)
    reason=str(reason).strip()
    if not reason:
        raise ValueError("I14 NOT_APPLICABLE declaration requires a nonempty engineering reason")
    if q.model.half_couplings:
        raise ValueError("cannot declare half coupling NOT_APPLICABLE while a coupling entity exists")
    return _component(q,I14_NOT_APPLICABLE,{
        "status":I14_NOT_APPLICABLE,
        "applicable":False,
        "reason":reason,
    })


def require_half_coupling_declaration(project):
    value=(project.metadata.get("numerical_readiness",{})
           .get("components",{}).get("half_coupling",I14_NOT_DECLARED))
    if value not in {I14_EXPLICIT,I14_NOT_APPLICABLE}:
        raise ValueError(
            "API 541 lateral assessment requires an explicit I14 half-coupling "
            "declaration (entity or NOT_APPLICABLE with justification)"
        )
    if value==I14_EXPLICIT and len(project.model.half_couplings)!=1:
        raise ValueError("I14 explicit half-coupling readiness does not match the model entity")
    if value==I14_NOT_APPLICABLE and project.model.half_couplings:
        raise ValueError("I14 NOT_APPLICABLE readiness conflicts with a model entity")
    return value


__all__=[
    "I14_EXPLICIT","I14_NOT_APPLICABLE","I14_NOT_DECLARED",
    "declare_half_coupling","declare_half_coupling_not_applicable",
    "require_half_coupling_declaration",
]
