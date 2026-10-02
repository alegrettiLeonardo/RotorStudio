"""C1 preservation gate anchored to promoted B3 main.

C1 is additive. It may extend only the declared fault-analysis integration
surfaces while preserving all promoted B1/B2/B3 physics and frozen authorities.
"""
from __future__ import annotations
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
B3_PROMOTED_MAIN="0e9e57b7eed9a598c7001ba5258ce8829894344e"
C1_AUTHORITY_FREEZE="b45bbaa5ec91ca004643142e83f75d0c13f7a8ea"

PROMOTED_IMMUTABLE_PATHS=(
    "fortran/src/rd_shaft_6dof.f90",
    "fortran/src/rd_disk_6dof.f90",
    "fortran/src/rd_6dof_element_c_api.f90",
    "fortran/src/rd_6dof_assembly.f90",
    "fortran/src/rd_6dof_modal.f90",
    "fortran/src/rd_6dof_campbell.f90",
    "fortran/src/rd_6dof_global_c_api.f90",
    "fortran/src/rd_axial_torsional.f90",
    "fortran/src/rd_axial_torsional_c_api.f90",
    "fortran/tests/test_6dof_elements.f90",
    "fortran/tests/test_6dof_global.f90",
    "fortran/tests/test_axial_torsional.f90",
    "python/src/drm_core/solver/sixdof_elements.py",
    "python/src/drm_core/solver/sixdof_global.py",
    "python/src/drm_core/solver/axial_torsional.py",
    "python/src/drm_core/analysis/axial_torsional.py",
    "python/tests_6dof_elements",
    "python/tests_6dof_global",
    "python/tests_axial_torsional",
    "validation/ross_parity/6dof_elements",
    "validation/ross_parity/6dof_global",
    "validation/ross_parity/axial_torsional",
)

PROMOTED_PRODUCT_PATHS=(
    "python/src/drm_flet",
    "python/src/drm_studio",
    "python/tests_flet",
    "python/tests_ui",
    "fortran/bearings",
    "python/tests_bearings",
    "python/src/drm_core/domain/bearings.py",
    "python/src/drm_core/solver/bearings_backend.py",
    "python/src/drm_core/solver/bearings_ffi.py",
    "python/src/drm_core/solver/bearing_maps.py",
)

C1_EXISTING_ADAPTERS={
    "fortran/CMakeLists.txt":"4bf52fb67ecb47bb1e2ee2bcff565819371dab24",
    "python/src/drm_core/stage1.py":"f14d5319914c78fb0b886381724a61156d87186c",
    "python/src/drm_core/__init__.py":"ebc65952f507760b6332dd9e900fc31c8f14c002",
    "python/src/drm_core/solver/facade.py":"553d8e3ddb750346809bb1a7ebfe989fe04c7dc1",
}

ALLOWED_ADDITIVE_PREFIXES=(
    "validation/c1/",
    "validation/ross_parity/misalignment/",
    "python/tests_misalignment/",
)
ALLOWED_ADDITIVE_FILES={
    ".github/workflows/c1-misalignment-authority.yml",
    ".github/workflows/ross-analysis-c1-misalignment.yml",
    "validation/ross_parity/generate_misalignment_reference.py",
    "validation/ross_parity/verify_misalignment_candidate.py",
    "fortran/src/rd_fault_misalignment.f90",
    "fortran/src/rd_fault_misalignment_c_api.f90",
    "fortran/tests/test_fault_misalignment.f90",
    "python/src/drm_core/solver/misalignment.py",
    "python/src/drm_core/analysis/misalignment.py",
    "docs/ROSS_C1_MISALIGNMENT_IMPLEMENTATION.md",
}

C1_CMAKE_APPEND=b"""
# C1 additive 6-DOF misalignment fault dynamics on the promoted B3 platform.
target_sources(drmrotor PRIVATE
 src/rd_fault_misalignment.f90
 src/rd_fault_misalignment_c_api.f90)
add_executable(test_fault_misalignment tests/test_fault_misalignment.f90)
target_link_libraries(test_fault_misalignment PRIVATE drmrotor)
target_include_directories(test_fault_misalignment PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_fault_misalignment PRIVATE -ffree-line-length-none)
endif()
add_test(NAME misalignment_native_contract COMMAND test_fault_misalignment)
"""

def git(*args:str)->bytes:
    return subprocess.check_output(["git",*args],cwd=ROOT)

def allowed_addition(path:str)->bool:
    return path in ALLOWED_ADDITIVE_FILES or any(path.startswith(p) for p in ALLOWED_ADDITIVE_PREFIXES)

def verify()->dict:
    subprocess.run(["git","merge-base","--is-ancestor",B3_PROMOTED_MAIN,"HEAD"],cwd=ROOT,check=True)
    subprocess.run(["git","merge-base","--is-ancestor",C1_AUTHORITY_FREEZE,"HEAD"],cwd=ROOT,check=True)
    for path in PROMOTED_IMMUTABLE_PATHS:
        subprocess.run(["git","diff","--exit-code",B3_PROMOTED_MAIN,"HEAD","--",path],cwd=ROOT,check=True)
    for path in PROMOTED_PRODUCT_PATHS:
        subprocess.run(["git","diff","--exit-code",B3_PROMOTED_MAIN,"HEAD","--",path],cwd=ROOT,check=True)
    subprocess.run(["git","diff","--exit-code",C1_AUTHORITY_FREEZE,"HEAD","--",
                    "validation/ross_parity/misalignment"],cwd=ROOT,check=True)
    rows=git("diff","--no-renames","--name-status",B3_PROMOTED_MAIN,"HEAD").decode().splitlines()
    for row in rows:
        fields=row.split("\t")
        if len(fields)!=2:
            raise ValueError("C1 unexpected diff record: "+row)
        status,path=fields
        if status=="A":
            if not allowed_addition(path):
                raise ValueError("C1 unapproved additive path: "+path)
        elif status=="M":
            if path not in C1_EXISTING_ADAPTERS:
                raise ValueError("C1 modified unapproved promoted-B3 path: "+path)
        else:
            raise ValueError("C1 unsupported promoted-main delta: "+row)
    for path,expected in C1_EXISTING_ADAPTERS.items():
        actual=git("hash-object",path).decode().strip()
        if actual!=expected:
            raise ValueError(f"C1 adapter bytes changed: {path}: {actual} != {expected}")
    before=git("show",f"{B3_PROMOTED_MAIN}:fortran/CMakeLists.txt")
    after=git("show","HEAD:fortran/CMakeLists.txt")
    if after!=before+C1_CMAKE_APPEND:
        raise ValueError("C1 CMake integration differs from exact additive suffix")
    return {
        "status":"PASS",
        "b3_promoted_main":B3_PROMOTED_MAIN,
        "c1_authority_freeze":C1_AUTHORITY_FREEZE,
        "immutable_promoted_paths":list(PROMOTED_IMMUTABLE_PATHS),
        "promoted_product_paths":list(PROMOTED_PRODUCT_PATHS),
        "existing_adapters":dict(C1_EXISTING_ADAPTERS),
        "cmake":"EXACT_C1_ADDITIVE_SUFFIX",
    }

if __name__=="__main__":
    import json
    print("C1_B3_PRESERVATION",json.dumps(verify(),sort_keys=True))
