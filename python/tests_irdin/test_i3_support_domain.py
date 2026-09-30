from __future__ import annotations

import pytest

from drm_core import load_irdin_project, load_project, save_project
from drm_core.importers.irdin_support import build_bearing_supports, support_audit
from validation.irdin.i0_authority import CASE_PATH


def _project():
    return load_irdin_project(CASE_PATH)


def test_i3_st41_support_domain_preserves_legacy_radial_contract():
    project=_project()
    supports=project.model.supports
    assert len(supports)==2
    assert [(x.bearing_number,x.node) for x in supports]==[(1,2),(2,19)]

    for support in supports:
        assert support.mass_kg==415.0
        assert support.kxx_n_m==2.73e9
        assert support.kyy_n_m==3.41e9
        assert support.kxy_n_m==0.0
        assert support.kyx_n_m==0.0
        assert support.cxx_ns_m==0.0
        assert support.cyy_ns_m==0.0
        assert support.cxy_ns_m==0.0
        assert support.cyx_ns_m==0.0
        assert support.provenance["source_axis_convention"]=="X/Z"
        assert support.provenance["domain_axis_convention"]=="X/Y"
        assert support.provenance["axis_mapping"]=="X->X; Z->Y; coefficient order/sign unchanged"

    readiness=project.metadata["numerical_readiness"]
    assert readiness["status"]=="BLOCKED_FOR_NUMERICAL_ANALYSIS"
    assert readiness["components"]["support_semantics"]=="PASS_I3_DOMAIN_ONLY"
    assert readiness["components"]["support_native_assembly"]=="NOT_QUALIFIED"
    assert any(x["code"]=="IRDIN_FLEXIBLE_SUPPORT_UNMAPPED" for x in readiness["blockers"])


def test_i3_st41_support_audit_is_deterministic():
    audit=support_audit(_project().model.supports)
    assert audit=={
        "status":"PASS",
        "count":2,
        "total_mass_kg":830.0,
        "supports":[
            {
                "bearing_number":1,"node":2,"mass_kg":415.0,
                "K_n_m":[[2.73e9,0.0],[0.0,3.41e9]],
                "C_ns_m":[[0.0,0.0],[0.0,0.0]],
                "axis_mapping":"X->X; Z->Y; coefficient order/sign unchanged",
            },
            {
                "bearing_number":2,"node":19,"mass_kg":415.0,
                "K_n_m":[[2.73e9,0.0],[0.0,3.41e9]],
                "C_ns_m":[[0.0,0.0],[0.0,0.0]],
                "axis_mapping":"X->X; Z->Y; coefficient order/sign unchanged",
            },
        ],
    }


def test_i3_support_domain_survives_save_reopen(tmp_path):
    project=_project()
    path=tmp_path/"st41-i3.json"
    save_project(project,path)
    reopened=load_project(path)
    assert reopened.model.supports==project.model.supports
    assert reopened.model.model_hash()==project.model.model_hash()


def test_i3_support_builder_fails_closed_on_duplicate_or_invalid_mass():
    project=_project()
    metadata=project.metadata

    duplicate={**metadata,"sketch":{**metadata["sketch"],"supports":[
        dict(metadata["sketch"]["supports"][0]),
        {**dict(metadata["sketch"]["supports"][1]),"bearing_number":1},
    ]}}
    with pytest.raises(ValueError,match="duplicate support"):
        build_bearing_supports(duplicate)

    invalid={**metadata,"sketch":{**metadata["sketch"],"supports":[
        {**dict(metadata["sketch"]["supports"][0]),"mass_kg":0.0},
    ]}}
    with pytest.raises(ValueError,match="mass > 0"):
        build_bearing_supports(invalid)
