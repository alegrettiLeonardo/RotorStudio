from __future__ import annotations

import numpy as np

from drm_core import load_irdin_project
from drm_core.importers.irdin_bearing_policy import legacy_speed_status
from drm_core.solver.bearings_backend import AdvancedBearingBackend
from drm_core.units import rpm_to_rad_s
from validation.irdin.i0_authority import CASE_PATH


def _legacy_reference(axis, values, q):
    x=np.asarray(axis,dtype=float);y=np.asarray(values,dtype=float);q=float(q)
    if len(x)<2: raise ValueError
    if len(x)==2 or q>x[-2]:
        return y[-2]+(y[-1]-y[-2])*(q-x[-2])/(x[-1]-x[-2])
    for i in range(1,len(x)-1):
        if abs(q-x[i])<=1e-15:
            return y[i]
        if x[i]>q:
            idx=(i-1,i,i+1)
            out=0.0
            for j in idx:
                term=y[j]
                for k in idx:
                    if k!=j: term*=((q-x[k])/(x[j]-x[k]))
                out+=term
            return out
    return y[-2]+(y[-1]-y[-2])*(q-x[-2])/(x[-1]-x[-2])


def test_i5_import_uses_demonstrated_legacy_policy_and_records_300rpm_warning():
    project=load_irdin_project(CASE_PATH)
    for bearing in project.model.advanced_bearings:
        assert bearing.interpolation=="irdin_lagrange"
        p=bearing.provenance
        assert p["source_table_speed_range_rpm"]==[500.0,4000.0]
        assert p["legacy_recommended_speed_range_rpm"]==[375.0,5000.0]
        rows={x["rpm"]:x["status"] for x in p["requested_speed_status"]}
        assert rows[300.0]=="EXTRAPOLATED_OUTSIDE_LEGACY_RECOMMENDED_RANGE"
        assert rows[3000.0]=="INTERPOLATED"
    assert project.metadata["numerical_readiness"]["components"]["bearing_extrapolation"]=="PASS_I5_LEGACY_POLICY"


def test_i5_status_boundaries_are_explicit():
    axis=(500.0,850.0,1200.0,4000.0)
    assert legacy_speed_status(axis,375.0)=="EXTRAPOLATED_WITHIN_LEGACY_RECOMMENDED_RANGE"
    assert legacy_speed_status(axis,300.0)=="EXTRAPOLATED_OUTSIDE_LEGACY_RECOMMENDED_RANGE"
    assert legacy_speed_status(axis,500.0)=="TABULATED"
    assert legacy_speed_status(axis,700.0)=="INTERPOLATED"
    assert legacy_speed_status(axis,5000.0)=="EXTRAPOLATED_WITHIN_LEGACY_RECOMMENDED_RANGE"
    assert legacy_speed_status(axis,5100.0)=="EXTRAPOLATED_OUTSIDE_LEGACY_RECOMMENDED_RANGE"


def test_i5_native_coefficients_match_independent_legacy_intlag_at_key_speeds():
    project=load_irdin_project(CASE_PATH)
    bearing=project.model.advanced_bearings[0]
    backend=AdvancedBearingBackend()
    axis_rpm=np.asarray([x*60.0/(2*np.pi) for x in bearing.speed_rad_s])
    for rpm in (300.0,375.0,500.0,675.0,3650.0,4000.0,5000.0):
        result=backend.evaluate(bearing,float(rpm_to_rad_s(rpm)),float(rpm_to_rad_s(rpm)))
        expected={
            "kxx":_legacy_reference(axis_rpm,bearing.kxx,rpm),
            "kxy":_legacy_reference(axis_rpm,bearing.kxy,rpm),
            "kyx":_legacy_reference(axis_rpm,bearing.kyx,rpm),
            "kyy":_legacy_reference(axis_rpm,bearing.kyy,rpm),
            "cxx":_legacy_reference(axis_rpm,bearing.cxx,rpm),
            "cxy":_legacy_reference(axis_rpm,bearing.cxy,rpm),
            "cyx":_legacy_reference(axis_rpm,bearing.cyx,rpm),
            "cyy":_legacy_reference(axis_rpm,bearing.cyy,rpm),
        }
        np.testing.assert_allclose(result.K,[[expected["kxx"],expected["kxy"]],[expected["kyx"],expected["kyy"]]],rtol=5e-14,atol=1e-7)
        np.testing.assert_allclose(result.C,[[expected["cxx"],expected["cxy"]],[expected["cyx"],expected["cyy"]]],rtol=5e-14,atol=1e-9)


def test_i5_policy_remains_qualified_after_later_readiness_stages():
    project=load_irdin_project(CASE_PATH)
    readiness=project.metadata["numerical_readiness"]
    assert readiness["status"]=="LEGACY_NUMERIC_READY"
    assert readiness["components"]["bearing_extrapolation"]=="PASS_I5_LEGACY_POLICY"
    assert readiness["components"]["expanded_solver"]=="PASS_I9_NATIVE_MODAL_RESPONSE"
    assert readiness["components"]["automatic_cases"]=="PASS_I10_LEGACY_CASES"
    assert readiness["blockers"]==[]
