from __future__ import annotations
import subprocess
import pytest
from validation.b3.preservation import (
    ROOT,B2_PROMOTED_MAIN,B3_AUTHORITY_FREEZE,B3_EXISTING_ADAPTERS,
    B3_CMAKE_APPEND,allowed_addition,verify,
)

C1_MARKER=ROOT/"validation/c1/preservation.py"

def test_b3_preservation_gate_passes_exact_working_tree():
    result=verify()
    assert result["status"]=="PASS"
    assert result["b2_promoted_main"]==B2_PROMOTED_MAIN
    assert result["b3_authority_freeze"]==B3_AUTHORITY_FREEZE

def test_b3_declared_additions_are_narrow():
    assert allowed_addition("fortran/src/rd_axial_torsional.f90")
    assert allowed_addition("python/tests_axial_torsional/test_parity.py")
    assert not allowed_addition("fortran/src/rd_shaft_6dof.f90")
    assert not allowed_addition("python/src/drm_core/solver/sixdof_global.py")

def test_b3_existing_adapters_are_exactly_pinned():
    c1_adapters={}
    if C1_MARKER.is_file():
        from validation.c1.preservation import C1_EXISTING_ADAPTERS
        c1_adapters=C1_EXISTING_ADAPTERS
    for path,expected in B3_EXISTING_ADAPTERS.items():
        actual=subprocess.check_output(["git","hash-object",path],cwd=ROOT,text=True).strip()
        effective=c1_adapters.get(path,expected)
        assert actual==effective,(path,actual,effective)

def test_b3_cmake_is_exact_additive_suffix():
    before=subprocess.check_output(["git","show",f"{B2_PROMOTED_MAIN}:fortran/CMakeLists.txt"],cwd=ROOT)
    after=subprocess.check_output(["git","show","HEAD:fortran/CMakeLists.txt"],cwd=ROOT)
    expected=before+B3_CMAKE_APPEND
    if C1_MARKER.is_file():
        from validation.c1.preservation import C1_CMAKE_APPEND
        expected+=C1_CMAKE_APPEND
    assert after==expected
