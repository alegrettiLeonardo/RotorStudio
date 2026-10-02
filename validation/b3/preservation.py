"""B3 preservation gate anchored to the promoted B2 main.

B3 is additive. It may extend only the explicitly declared integration surfaces
while keeping B1/B2 physics, frozen authorities and promoted product code
byte-identical.
"""
from __future__ import annotations
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
B2_PROMOTED_MAIN="c23a5e515480fa28fb6dd770fca235b73dd0198a"
B3_AUTHORITY_FREEZE="e4fda44cba1dd29696c67be449fa560440d9ebc0"

B2_IMMUTABLE_PATHS=(
    "fortran/src/rd_shaft_6dof.f90",
    "fortran/src/rd_disk_6dof.f90",
    "fortran/src/rd_6dof_element_c_api.f90",
    "fortran/src/rd_6dof_assembly.f90",
    "fortran/src/rd_6dof_modal.f90",
    "fortran/src/rd_6dof_campbell.f90",
    "fortran/src/rd_6dof_global_c_api.f90",
    "fortran/tests/test_6dof_elements.f90",
    "fortran/tests/test_6dof_global.f90",
    "python/src/drm_core/solver/sixdof_elements.py",
    "python/src/drm_core/solver/sixdof_global.py",
    "python/tests_6dof_elements",
    "python/tests_6dof_global",
    "validation/ross_parity/6dof_elements",
    "validation/ross_parity/6dof_global",
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

B3_EXISTING_ADAPTERS={
    "fortran/CMakeLists.txt":"f4f276e7eddcbfea80566976e2bb883ad9a1f1c4",
    "python/src/drm_core/stage1.py":"8a9d96550edf085450b0d71544ae8b92e6de499c",
    "python/src/drm_core/__init__.py":"6d28515c6a3de947cc24cfe3d772ae0562a76ee6",
    "python/src/drm_core/solver/facade.py":"5d1886720fb40b26c4f4974ef3e125fdc6b86e98",
    "python/tests_ucs/test_ucs_bearing_order_authority.py":"d0be9bb5687d764bfd34bfbd1502776be46a35ed",
    "scripts/verify_a1_legacy_preservation.py":"b5b27922fe0d27ab951f7a07c4ffc6c8d03e2fb0",
    "validation/b1/native_preservation.py":"7ec7d62572769a703dbb454eec45ff14d77b2c5c",
    "validation/b2/preservation.py":"7192a9179371bcb098c7dbd8155df926bf131134",
}

ALLOWED_ADDITIVE_PREFIXES=(
    "validation/b3/",
    "validation/ross_parity/axial_torsional/",
    "python/tests_axial_torsional/",
)
ALLOWED_ADDITIVE_FILES={
    ".github/workflows/b3-axial-torsional-authority.yml",
    ".github/workflows/ross-analysis-b3-axial-torsional.yml",
    "validation/ross_parity/generate_axial_torsional_reference.py",
    "validation/ross_parity/verify_axial_torsional_candidate.py",
    "fortran/src/rd_axial_torsional.f90",
    "fortran/src/rd_axial_torsional_c_api.f90",
    "fortran/tests/test_axial_torsional.f90",
    "python/src/drm_core/solver/axial_torsional.py",
    "python/src/drm_core/analysis/axial_torsional.py",
    "docs/ROSS_B3_AXIAL_TORSIONAL_IMPLEMENTATION.md",
}

B3_CMAKE_APPEND=b"""
# B3 additive dedicated axial/torsional workflows on the qualified B2 6-DOF platform.
target_sources(drmrotor PRIVATE
 src/rd_axial_torsional.f90
 src/rd_axial_torsional_c_api.f90)
add_executable(test_axial_torsional tests/test_axial_torsional.f90)
target_link_libraries(test_axial_torsional PRIVATE drmrotor)
target_include_directories(test_axial_torsional PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_axial_torsional PRIVATE -ffree-line-length-none)
endif()
add_test(NAME axial_torsional_native_contract COMMAND test_axial_torsional)
"""

def git(*args:str)->bytes:
    return subprocess.check_output(["git",*args],cwd=ROOT)

def allowed_addition(path:str)->bool:
    return path in ALLOWED_ADDITIVE_FILES or any(path.startswith(p) for p in ALLOWED_ADDITIVE_PREFIXES)

def verify()->dict:
    subprocess.run(["git","merge-base","--is-ancestor",B2_PROMOTED_MAIN,"HEAD"],cwd=ROOT,check=True)
    subprocess.run(["git","merge-base","--is-ancestor",B3_AUTHORITY_FREEZE,"HEAD"],cwd=ROOT,check=True)

    for path in B2_IMMUTABLE_PATHS:
        subprocess.run(["git","diff","--exit-code",B2_PROMOTED_MAIN,"HEAD","--",path],cwd=ROOT,check=True)
    for path in PROMOTED_PRODUCT_PATHS:
        subprocess.run(["git","diff","--exit-code",B2_PROMOTED_MAIN,"HEAD","--",path],cwd=ROOT,check=True)
    subprocess.run(["git","diff","--exit-code",B3_AUTHORITY_FREEZE,"HEAD","--",
                    "validation/ross_parity/axial_torsional"],cwd=ROOT,check=True)

    rows=git("diff","--no-renames","--name-status",B2_PROMOTED_MAIN,"HEAD").decode().splitlines()
    for row in rows:
        fields=row.split("\t")
        if len(fields)!=2:
            raise ValueError("B3 unexpected diff record: "+row)
        status,path=fields
        if status=="A":
            if not allowed_addition(path):
                raise ValueError("B3 unapproved additive path: "+path)
        elif status=="M":
            if path not in B3_EXISTING_ADAPTERS:
                raise ValueError("B3 modified unapproved promoted-B2 path: "+path)
        else:
            raise ValueError("B3 unsupported promoted-main delta: "+row)

    for path,expected in B3_EXISTING_ADAPTERS.items():
        actual=git("hash-object",path).decode().strip()
        if actual!=expected:
            raise ValueError(f"B3 adapter bytes changed: {path}: {actual} != {expected}")

    before=git("show",f"{B2_PROMOTED_MAIN}:fortran/CMakeLists.txt")
    after=git("show","HEAD:fortran/CMakeLists.txt")
    if after!=before+B3_CMAKE_APPEND:
        raise ValueError("B3 CMake integration differs from the exact additive suffix")

    return {
        "status":"PASS",
        "b2_promoted_main":B2_PROMOTED_MAIN,
        "b3_authority_freeze":B3_AUTHORITY_FREEZE,
        "immutable_b1_b2_paths":list(B2_IMMUTABLE_PATHS),
        "promoted_product_paths":list(PROMOTED_PRODUCT_PATHS),
        "existing_adapters":dict(B3_EXISTING_ADAPTERS),
        "cmake":"EXACT_B3_ADDITIVE_SUFFIX",
    }

if __name__=="__main__":
    import json
    print("B3_B2_PRESERVATION",json.dumps(verify(),sort_keys=True))
