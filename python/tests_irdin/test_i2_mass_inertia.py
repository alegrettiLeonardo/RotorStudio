from __future__ import annotations

import math

import pytest

from drm_core import load_irdin_project, load_project, save_project
from drm_core.importers.irdin_mass import (
    all_mass_slices,
    disk_inertias_kg_m2,
    mass_audit,
)
from validation.irdin.i0_authority import CASE_PATH


def _project():
    return load_irdin_project(CASE_PATH)


def test_i2_st41_logical_mass_spans_are_source_faithful_and_blocker_remains():
    project=_project()
    spans=project.model.mass_spans
    assert len(spans)==3
    assert [x.mass_kg for x in spans]==[10090.0,70.0,520.0]
    assert sum(x.mass_kg for x in spans)==10680.0

    package=spans[0]
    assert package.z_start_m==pytest.approx(1.3709)
    assert package.length_m==pytest.approx(1.675)
    assert package.outer_diameter_m==pytest.approx(1.140)
    assert package.inner_diameter_m==pytest.approx(0.620)
    assert package.package is True
    assert package.divisions==6
    assert package.provenance["geometry_resolution"]["inner_source"]=="RIBBED_PACKAGE_DPCT"

    assert spans[1].inner_diameter_m==pytest.approx(0.192)
    assert spans[2].inner_diameter_m==pytest.approx(0.172)
    assert spans[1].provenance["geometry_resolution"]["inner_source"]=="LOCAL_PHYSICAL_SHAFT_OD"
    assert spans[2].provenance["geometry_resolution"]["inner_source"]=="LOCAL_PHYSICAL_SHAFT_OD"

    readiness=project.metadata["numerical_readiness"]
    assert readiness["status"]=="BLOCKED_FOR_NUMERICAL_ANALYSIS"
    assert readiness["components"]["mass_semantics"]=="PASS"
    assert readiness["components"]["mass_inertia"]=="PASS_I2_LOGICAL_ONLY"
    assert readiness["components"]["mass_native_materialization"]=="NOT_QUALIFIED"
    assert any(x["code"]=="IRDIN_DISTRIBUTED_MASS_UNMAPPED" for x in readiness["blockers"])


def test_i2_st41_legacy_inertia_formula_sentinels():
    project=_project()
    spans=project.model.mass_spans

    expected=[
        (3421.035520833333,2123.945),
        (1.365490525,2.68856),
        (13.80704,19.49896),
    ]
    for span,(id_expected,ip_expected) in zip(spans,expected):
        assert span.diametral_inertia_kgm2==pytest.approx(id_expected,rel=2e-15)
        assert span.polar_inertia_kgm2==pytest.approx(ip_expected,rel=2e-15)
        id_direct,ip_direct=disk_inertias_kg_m2(
            span.mass_kg,span.length_m,span.outer_diameter_m,span.inner_diameter_m
        )
        assert id_direct==pytest.approx(span.diametral_inertia_kgm2,rel=0,abs=0)
        assert ip_direct==pytest.approx(span.polar_inertia_kgm2,rel=0,abs=0)


def test_i2_package_expansion_conserves_mass_extent_centroid_and_full_cylinder_inertia():
    project=_project()
    package=project.model.mass_spans[0]
    slices=all_mass_slices([package])

    assert len(slices)==6
    assert sum(x.mass_kg for x in slices)==pytest.approx(package.mass_kg,rel=2e-16)
    assert slices[0].z_start_m==pytest.approx(package.z_start_m)
    assert slices[-1].z_start_m+slices[-1].length_m==pytest.approx(
        package.z_start_m+package.length_m
    )
    cg=sum(x.mass_kg*x.z_center_m for x in slices)/sum(x.mass_kg for x in slices)
    assert cg==pytest.approx(package.z_center_m,abs=5e-16)

    ip=sum(x.polar_inertia_kgm2 for x in slices)
    id_about_package_cg=sum(
        x.diametral_inertia_kgm2+x.mass_kg*(x.z_center_m-package.z_center_m)**2
        for x in slices
    )
    assert ip==pytest.approx(package.polar_inertia_kgm2,rel=3e-16)
    # Six independently rounded slice centers/inertias are recombined through
    # the parallel-axis theorem. 8*machine-epsilon-scale relative roundoff is
    # expected; this is not a production/golden tolerance.
    assert id_about_package_cg==pytest.approx(package.diametral_inertia_kgm2,rel=2e-15)


def test_i2_st41_mass_audit_is_deterministic():
    audit=mass_audit(_project().model.mass_spans)
    assert audit["status"]=="PASS"
    assert audit["logical_spans"]==3
    assert audit["materialized_slices"]==8
    assert audit["mass_kg"]==pytest.approx(10680.0)
    assert audit["center_m"]==pytest.approx(2.3494416198501873,rel=2e-15)
    assert audit["slice_first_moment_kg_m"]==pytest.approx(25092.0365,rel=2e-15)
    assert audit["logical_first_moment_kg_m"]==pytest.approx(25092.0365,rel=2e-15)
    assert audit["polar_inertia_sum_kgm2"]==pytest.approx(2146.13252,rel=2e-15)
    assert audit["diametral_inertia_about_cg_kgm2"]==pytest.approx(7075.87058243331,rel=2e-15)


def test_i2_mass_spans_survive_save_reopen_exactly(tmp_path):
    project=_project()
    target=tmp_path/"st41-i2.json"
    save_project(project,target)
    reopened=load_project(target)
    assert reopened.model.mass_spans==project.model.mass_spans
    assert reopened.model.model_hash()==project.model.model_hash()
    assert reopened.metadata["numerical_readiness"]==project.metadata["numerical_readiness"]


def test_i2_zero_mass_is_supported_but_invalid_geometry_fails_closed():
    id_,ip=disk_inertias_kg_m2(0.0,0.1,0.2,0.0)
    assert id_==0.0 and ip==0.0
    with pytest.raises(ValueError):
        disk_inertias_kg_m2(1.0,0.1,0.1,0.1)
    with pytest.raises(ValueError):
        disk_inertias_kg_m2(1.0,0.0,0.2,0.0)
    with pytest.raises(ValueError):
        disk_inertias_kg_m2(float("nan"),0.1,0.2,0.0)
