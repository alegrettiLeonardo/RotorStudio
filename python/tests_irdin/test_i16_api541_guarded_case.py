from __future__ import annotations

import numpy as np
import pytest

from drm_core import AnalysisCase,AnalysisService,load_irdin_project
from drm_core.importers.irdin_half_coupling import declare_half_coupling_not_applicable
from drm_core.importers.irdin_api541_case import enable_api541_lateral_analysis
from validation.irdin.i0_authority import CASE_PATH


def test_i16_import_remains_legacy_ready_and_cannot_run_api541_without_declaration():
    p=load_irdin_project(CASE_PATH)
    assert p.metadata["numerical_readiness"]["status"]=="LEGACY_NUMERIC_READY"
    assert p.metadata["numerical_readiness"]["components"]["api541_lateral"]=="NOT_READY_I16_REQUIRES_EXPLICIT_DECLARATIONS"
    with pytest.raises(ValueError,match="LEGACY_NUMERIC_READY"):
        AnalysisService().execute(
            p,AnalysisCase("api541_lateral",{},"must remain blocked")
        )


def test_i16_explicit_not_applicable_declaration_enables_guarded_case():
    p=load_irdin_project(CASE_PATH)
    p=declare_half_coupling_not_applicable(
        p,reason="Qualified configuration has no separate motor half coupling in assessed lateral scope"
    )
    q=enable_api541_lateral_analysis(
        p,
        operating_speed_rpm=1800.0,
        mode_count=4,
        support_stiffness_factors=(0.75,1.0,1.25),
        mode_overrides={1:"TRANSLATORY",2:"TRANSLATORY",3:"TRANSLATORY",4:"TRANSLATORY"},
    )
    assert p.metadata["numerical_readiness"]["status"]=="LEGACY_NUMERIC_READY"
    assert q.metadata["numerical_readiness"]["status"]=="API541_LATERAL_READY"
    assert q.metadata["numerical_readiness"]["components"]["api541_lateral"]=="READY_I16_GUARDED_CASE"
    api=[x for x in q.analyses if x.kind=="api541_lateral"]
    assert len(api)==1
    assert api[0].parameters["operating_speed_rpm"]==1800.0
    assert api[0].options["full_api541_compliance_claim"] is False


def test_i16_analysis_service_runs_only_guarded_api541_path():
    p=declare_half_coupling_not_applicable(
        load_irdin_project(CASE_PATH),
        reason="No separate half coupling for this test configuration",
    )
    q=enable_api541_lateral_analysis(
        p,
        operating_speed_rpm=1800.0,
        mode_count=3,
        support_stiffness_factors=(1.0,),
        mode_overrides={1:"TRANSLATORY",2:"TRANSLATORY",3:"TRANSLATORY"},
    )
    # Use a compact sentinel case while exercising the exact same I13 dispatch.
    case=AnalysisCase(
        "api541_lateral",
        {
            "campbell_speeds_rad_s":(np.array([0.,1000.,2000.,3000.])*2*np.pi/60).tolist(),
            "response_speeds_rad_s":(np.array([500.,1800.])*2*np.pi/60).tolist(),
            "mode_count":3,
            "excitation_orders":[1.0],
            "required_separation_fraction":0.15,
            "operating_speed_rpm":1800.0,
            "support_stiffness_factors":[1.0],
            "mode_overrides":{1:"TRANSLATORY",2:"TRANSLATORY",3:"TRANSLATORY"},
        },
        "I16 compact API541 sentinel",
    )
    result=AnalysisService().execute(q,case).result
    assert result.metadata["status"]=="PASS_I13_API541_LATERAL_ASSESSMENT"
    assert result.metadata["full_api541_compliance_claim"] is False

    with pytest.raises(ValueError,match="API541_LATERAL_READY"):
        AnalysisService().execute(q,AnalysisCase("modal",{"speed_rad_s":0.0},"unsafe generic"))


def test_i16_requires_explicit_operating_reference_and_i14():
    p=load_irdin_project(CASE_PATH)
    with pytest.raises(ValueError,match="half-coupling"):
        enable_api541_lateral_analysis(p,operating_speed_rpm=1800.0)

    p=declare_half_coupling_not_applicable(p,reason="No separate coupling")
    with pytest.raises(ValueError,match="exactly one"):
        enable_api541_lateral_analysis(p)
    with pytest.raises(ValueError,match="exactly one"):
        enable_api541_lateral_analysis(
            p,operating_speed_rpm=1800.0,operating_range_rpm=(1500.0,2100.0)
        )
