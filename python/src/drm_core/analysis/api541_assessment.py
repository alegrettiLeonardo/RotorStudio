"""I13 composed API 541 lateral assessment and engineering report.

This stage combines the qualified I11 lateral core and I12 analytical-unbalance
gate. It deliberately reports a declared lateral-analysis scope, not whole
standard compliance.
"""
from __future__ import annotations

from dataclasses import asdict,dataclass,is_dataclass
import json
from pathlib import Path
from typing import Mapping

import numpy as np

from drm_core.analysis.api541_lateral import (
    API541LateralCoreResult,
    RPM_TO_RAD_S,
    run_api541_lateral_core,
)
from drm_core.analysis.api541_analytical_unbalance import (
    API541AnalyticalUnbalanceResult,
    run_api541_analytical_unbalance,
)


@dataclass(frozen=True)
class API541LateralAssessmentResult:
    core:API541LateralCoreResult
    analytical_unbalance:tuple[API541AnalyticalUnbalanceResult,...]
    metadata:dict


def run_api541_lateral_assessment(
    project,
    *,
    campbell_speeds_rad_s,
    response_speeds_rad_s,
    mode_count:int=9,
    excitation_orders=(1.0,),
    required_separation_fraction:float=0.15,
    operating_speed_rpm:float|None=None,
    operating_range_rpm:tuple[float,float]|None=None,
    support_stiffness_factors=(0.5,0.75,1.0,1.25,1.5),
    mode_overrides:Mapping[int,str]|None=None,
    library_path:str|Path|None=None,
)->API541LateralAssessmentResult:
    if (operating_speed_rpm is None)==(operating_range_rpm is None):
        raise ValueError("I13 requires exactly one operating speed reference")
    if operating_speed_rpm is not None:
        op_speed=float(operating_speed_rpm)*RPM_TO_RAD_S
        op_range=None
    else:
        lo,hi=map(float,operating_range_rpm)
        op_speed=None
        op_range=(lo*RPM_TO_RAD_S,hi*RPM_TO_RAD_S)

    core=run_api541_lateral_core(
        project,
        campbell_speeds_rad_s=campbell_speeds_rad_s,
        response_speeds_rad_s=response_speeds_rad_s,
        mode_count=int(mode_count),
        excitation_orders=tuple(float(x) for x in excitation_orders),
        required_separation_fraction=float(required_separation_fraction),
        operating_speed_rad_s=op_speed,
        operating_range_rad_s=op_range,
        support_stiffness_factors=tuple(float(x) for x in support_stiffness_factors),
        library_path=library_path,
    )
    analytical=run_api541_analytical_unbalance(
        project,
        core.critical_speeds,
        operating_speed_rpm=operating_speed_rpm,
        operating_range_rpm=operating_range_rpm,
        mode_overrides=mode_overrides,
        library_path=library_path,
    )
    return API541LateralAssessmentResult(
        core,
        analytical,
        {
            "status":"PASS_I13_API541_LATERAL_ASSESSMENT",
            "scope":"API 541 lateral dynamics analysis for the declared imported iRdin scope",
            "source_edition":"API 541 Third Edition 1995",
            "critical_count":len(core.critical_speeds),
            "analytical_unbalance_case_count":len(analytical),
            "legacy_response_included":True,
            "analytical_unbalance_included":True,
            "support_sensitivity_included":True,
            "experimental_correlation_included":False,
            "torsional_analysis_included":False,
            "full_api541_compliance_claim":False,
        },
    )


def _jsonable(value):
    if isinstance(value,np.ndarray):
        if np.iscomplexobj(value):
            return {
                "shape":list(value.shape),
                "real":np.asarray(value.real).tolist(),
                "imag":np.asarray(value.imag).tolist(),
            }
        return value.tolist()
    if isinstance(value,np.generic):
        return value.item()
    if is_dataclass(value):
        return {k:_jsonable(v) for k,v in asdict(value).items()}
    if isinstance(value,dict):
        return {str(k):_jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value,complex):
        return {"real":float(value.real),"imag":float(value.imag)}
    return value


def write_api541_lateral_report(
    result:API541LateralAssessmentResult,
    outdir:str|Path,
    stem:str="api541_lateral",
):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    payload=_jsonable(result)
    json_path=out/f"{stem}.json"
    json_path.write_text(json.dumps(payload,indent=2,sort_keys=True),encoding="utf-8")

    lines=[
        "# API 541 lateral dynamics assessment",
        "",
        f"- status: `{result.metadata['status']}`",
        f"- scope: {result.metadata['scope']}",
        "- whole-standard compliance claim: **NO**",
        "- experimental correlation included: **NO**",
        "- torsional analysis included: **NO**",
        "",
        "## Critical speeds and separation",
        "",
        "| Branch | Order | Critical rpm | Damping ratio | Separation | Required | Result |",
        "|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    checks={(x.branch,x.excitation_order,round(x.critical_speed_rpm,9)):x
            for x in result.core.separation_checks}
    for c in result.core.critical_speeds:
        key=(c.branch,c.excitation_order,round(c.speed_rpm,9))
        check=checks.get(key)
        if check is None:
            lines.append(
                f"| {c.branch} | {c.excitation_order:g} | {c.speed_rpm:.6g} | "
                f"{c.damping_ratio:.6g} | n/a | n/a | n/a |"
            )
        else:
            lines.append(
                f"| {c.branch} | {c.excitation_order:g} | {c.speed_rpm:.6g} | "
                f"{c.damping_ratio:.6g} | {check.separation_fraction:.6g} | "
                f"{check.required_fraction:.6g} | {'PASS' if check.passed else 'FAIL'} |"
            )

    lines += ["","## API 541 analytical unbalance",""]
    if not result.analytical_unbalance:
        lines.append("No critical crossing in the declared sweep produced an analytical-unbalance case.")
    for case in result.analytical_unbalance:
        lines += [
            f"### Branch {case.critical.branch} — {case.critical.speed_rpm:.6g} rpm",
            "",
            f"- mode kind: `{case.mode_kind}`",
            f"- reference operating speed: {case.reference_speed_rpm:.6g} rpm",
            f"- vibration limit: {case.vibration_limit_pp_m*1e6:.6g} µm p-p",
            f"- response after scaling: {case.max_probe_pp_m*1e6:.6g} µm p-p",
            f"- common scale factor: {case.scale_factor:.6g}",
            "",
            "| Node | z [m] | Journal load [kg] | Minimum U [g·mm] | Applied U [g·mm] | Phase [deg] |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
        for p in case.planes:
            lines.append(
                f"| {p.node} | {p.z_m:.9g} | {p.journal_load_kg:.9g} | "
                f"{p.minimum_unbalance_g_mm:.9g} | {p.applied_unbalance_g_mm:.9g} | "
                f"{np.degrees(p.phase_rad):.9g} |"
            )

    lines += [
        "",
        "## Limitations",
        "",
        "- This report covers the declared lateral-dynamics scope only.",
        "- It does not establish complete API 541 compliance.",
        "- Experimental correlation is a subsequent gate.",
        "- Torsional analysis is a separate subsequent scope.",
        "- Overhung-load substitution is not inferred unless that mode/source condition is explicitly qualified.",
        "",
    ]
    md_path=out/f"{stem}.md"
    md_path.write_text("\n".join(lines),encoding="utf-8")
    return {"json":json_path,"markdown":md_path}


__all__=[
    "API541LateralAssessmentResult",
    "run_api541_lateral_assessment",
    "write_api541_lateral_report",
]
