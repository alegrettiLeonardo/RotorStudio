from __future__ import annotations

from pathlib import Path

import numpy as np

from drm_core import load_irdin_project
from drm_core.analysis.api541_lateral import RPM_TO_RAD_S
from drm_core.analysis.api541_assessment import (
    run_api541_lateral_assessment,
    write_api541_lateral_report,
)
from validation.irdin.i0_authority import CASE_PATH


def test_i13_st41_composed_assessment_executes_without_mutating_source(tmp_path):
    p=load_irdin_project(CASE_PATH)
    before_hash=p.model.model_hash()
    before_forces=tuple(p.model.forces)
    before_supports=tuple(p.model.supports)
    result=run_api541_lateral_assessment(
        p,
        campbell_speeds_rad_s=np.array([0.,1000.,2000.,3000.])*RPM_TO_RAD_S,
        response_speeds_rad_s=np.array([500.,1800.])*RPM_TO_RAD_S,
        mode_count=3,
        excitation_orders=(1.0,),
        required_separation_fraction=0.15,
        operating_speed_rpm=1800.0,
        support_stiffness_factors=(1.0,),
        mode_overrides={1:"TRANSLATORY",2:"TRANSLATORY",3:"TRANSLATORY"},
    )
    assert result.metadata["status"]=="PASS_I13_API541_LATERAL_ASSESSMENT"
    assert result.metadata["full_api541_compliance_claim"] is False
    assert result.metadata["experimental_correlation_included"] is False
    assert result.metadata["torsional_analysis_included"] is False
    assert result.metadata["critical_count"]==len(result.core.critical_speeds)
    assert result.metadata["analytical_unbalance_case_count"]==len(result.analytical_unbalance)
    assert p.model.model_hash()==before_hash
    assert tuple(p.model.forces)==before_forces
    assert tuple(p.model.supports)==before_supports

    paths=write_api541_lateral_report(result,tmp_path)
    assert paths["json"].is_file()
    assert paths["markdown"].is_file()
    text=paths["markdown"].read_text(encoding="utf-8")
    assert "whole-standard compliance claim: **NO**" in text
    assert "Experimental correlation is a subsequent gate." in text
    assert "Torsional analysis is a separate subsequent scope." in text


def test_i13_requires_exactly_one_operating_reference():
    p=load_irdin_project(CASE_PATH)
    try:
        run_api541_lateral_assessment(
            p,
            campbell_speeds_rad_s=[0.0,100.0],
            response_speeds_rad_s=[100.0],
            operating_speed_rpm=1800.0,
            operating_range_rpm=(1500.0,2100.0),
        )
    except ValueError as exc:
        assert "exactly one" in str(exc)
    else:
        raise AssertionError("expected operating-reference validation error")
