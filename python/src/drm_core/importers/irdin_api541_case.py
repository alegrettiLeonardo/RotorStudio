"""I16 guarded API 541 lateral AnalysisCase enablement."""
from __future__ import annotations

from copy import deepcopy
import math

from drm_core.stage1 import AnalysisCase
from drm_core.importers.irdin_cases import (
    RPM_TO_RAD_S,
    campbell_speed_grid_rpm,
    response_speed_grid_rpm,
)
from drm_core.importers.irdin_half_coupling import require_half_coupling_declaration


_REQUIRED_COMPONENTS={
    "mass_native_materialization":{"PASS_I7_DISK_MATERIALIZATION","NOT_APPLICABLE"},
    "bearing_extrapolation":{"PASS_I5_LEGACY_POLICY","NOT_APPLICABLE"},
    "support_semantics":{"PASS_I3_DOMAIN_ONLY"},
    "support_native_assembly":{"PASS_I8_GLOBAL_MATRICES"},
    "expanded_solver":{"PASS_I9_NATIVE_MODAL_RESPONSE"},
    "automatic_cases":{"PASS_I10_LEGACY_CASES"},
    "unbalance":{"PASS_I6_LEGACY_UNBALANCE","NOT_APPLICABLE"},
    "probes":{"PASS_I6_RESPONSE_PROBES"},
}


def _require_components(project):
    components=(project.metadata.get("numerical_readiness",{}).get("components",{}))
    for name,allowed in _REQUIRED_COMPONENTS.items():
        value=components.get(name,"NOT_QUALIFIED")
        if value not in allowed:
            raise ValueError(f"I16 requires {name} in {sorted(allowed)}; received {value!r}")


def enable_api541_lateral_analysis(
    project,
    *,
    operating_speed_rpm:float|None=None,
    operating_range_rpm:tuple[float,float]|None=None,
    mode_count:int|None=None,
    excitation_orders=(1.0,),
    required_separation_fraction:float=0.15,
    support_stiffness_factors=(0.5,0.75,1.0,1.25,1.5),
    mode_overrides:dict[int,str]|None=None,
    name:str="API 541 Lateral Dynamics",
):
    if project.metadata.get("source_format")!="iRdin/VB6 INI":
        raise ValueError("I16 requires an imported iRdin project")
    _require_components(project)
    half_coupling_status=require_half_coupling_declaration(project)
    if (operating_speed_rpm is None)==(operating_range_rpm is None):
        raise ValueError("I16 requires exactly one fixed operating speed or operating range")

    if operating_speed_rpm is not None:
        op=float(operating_speed_rpm)
        if not math.isfinite(op) or op<=0.0:
            raise ValueError("I16 operating_speed_rpm must be finite and > 0")
        op_params={"operating_speed_rpm":op}
        op_record={"kind":"FIXED_SPEED","speed_rpm":op}
    else:
        lo,hi=map(float,operating_range_rpm)
        if not math.isfinite(lo) or not math.isfinite(hi) or lo<=0.0 or hi<lo:
            raise ValueError("I16 operating_range_rpm must satisfy 0 < min <= max")
        op_params={"operating_range_rpm":[lo,hi]}
        op_record={"kind":"SPEED_RANGE","min_rpm":lo,"max_rpm":hi}

    camp=campbell_speed_grid_rpm(project.metadata)
    response=response_speed_grid_rpm(project.metadata)
    if mode_count is None:
        mode_count=int(project.metadata.get("legacy_irdin",{}).get("campbell",{}).get("critical_count",0))
    mode_count=int(mode_count)
    if mode_count<1:
        raise ValueError("I16 mode_count must be >= 1")

    orders=tuple(float(x) for x in excitation_orders)
    if not orders or any(not math.isfinite(x) or x<=0.0 for x in orders):
        raise ValueError("I16 excitation_orders must be finite and > 0")
    separation=float(required_separation_fraction)
    if not math.isfinite(separation) or separation<0.0:
        raise ValueError("I16 required_separation_fraction must be finite and >= 0")
    factors=tuple(float(x) for x in support_stiffness_factors)
    if not factors or any(not math.isfinite(x) or x<=0.0 for x in factors):
        raise ValueError("I16 support_stiffness_factors must be finite and > 0")

    parameters={
        "campbell_speeds_rad_s":(camp*RPM_TO_RAD_S).tolist(),
        "response_speeds_rad_s":(response*RPM_TO_RAD_S).tolist(),
        "mode_count":mode_count,
        "excitation_orders":list(orders),
        "required_separation_fraction":separation,
        "support_stiffness_factors":list(factors),
        "mode_overrides":{int(k):str(v) for k,v in dict(mode_overrides or {}).items()},
        **op_params,
    }
    case=AnalysisCase(
        "api541_lateral",
        parameters,
        str(name),
        {
            "source_format":"iRdin/VB6 INI",
            "scope":"API 541 lateral dynamics analysis for the declared imported iRdin scope",
            "api541_edition":"Third Edition 1995",
            "half_coupling_status":half_coupling_status,
            "operating_reference":op_record,
            "full_api541_compliance_claim":False,
        },
    )

    q=deepcopy(project)
    q.analyses=[x for x in q.analyses if x.kind!="api541_lateral"]+[case]
    readiness=q.metadata.setdefault("numerical_readiness",{})
    readiness.setdefault("components",{})["api541_lateral"]="READY_I16_GUARDED_CASE"
    readiness["status"]="API541_LATERAL_READY"
    q.metadata["api541_lateral_enablement"]={
        "status":"API541_LATERAL_READY",
        "analysis_name":case.name,
        "half_coupling_status":half_coupling_status,
        "operating_reference":op_record,
        "full_api541_compliance_claim":False,
        "experimental_correlation_required_for_model_validation":True,
        "torsional_scope_separate":True,
    }
    return q


__all__=["enable_api541_lateral_analysis"]
