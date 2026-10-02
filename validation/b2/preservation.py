"""B2 preservation gate anchored to promoted B1 main.

B2 must not modify B1 element physics, ABI, frozen authority or historical
A0-A8/Flet product files. The only allowed modification to an existing B1
file in the Fortran integration surface is the exact additive B2 CMake suffix.
"""
from __future__ import annotations
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
B1_PROMOTED_MAIN="d44ad24590f984e3f0655c427fcbf39be94a6da6"
B3_MARKER=ROOT/"validation/b3/preservation.py"
C1_MARKER=ROOT/"validation/c1/preservation.py"

B1_IMMUTABLE_PATHS=(
    "fortran/src/rd_shaft_6dof.f90",
    "fortran/src/rd_disk_6dof.f90",
    "fortran/src/rd_6dof_element_c_api.f90",
    "fortran/tests/test_6dof_elements.f90",
    "python/src/drm_core/solver/sixdof_elements.py",
    "python/tests_6dof_elements",
    "validation/ross_parity/6dof_elements",
)

B1_VALIDATION_GATE_EXCEPTION="validation/b1/native_preservation.py"

PINNED_B2_ADAPTER_BLOBS={
    B1_VALIDATION_GATE_EXCEPTION:"7ec7d62572769a703dbb454eec45ff14d77b2c5c",
    "python/src/drm_core/__init__.py":"4aca4be955ef3e3e3e193a71805eaafec3a3b42f",
    "python/src/drm_core/solver/facade.py":"8a8e9b5ca7c2e6ddbf058461413ea910ee4de68e",
    "python/tests_ucs/test_ucs_bearing_order_authority.py":"9e7266c994bf95059bd833ee2d45f3a061f7fa03",
    "scripts/verify_a1_legacy_preservation.py":"c12f35fc3c93a73f66ecd0158826134744bc8a7f",
}

B3_CONTROLLED_ADAPTERS=frozenset({
    "python/src/drm_core/__init__.py",
    "python/src/drm_core/solver/facade.py",
    "python/tests_ucs/test_ucs_bearing_order_authority.py",
    "scripts/verify_a1_legacy_preservation.py",
})

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

B2_CMAKE_APPEND=b"""
# B2 additive global 6-DOF assembly/modal/Campbell kernels.
target_sources(drmrotor PRIVATE
 src/rd_6dof_assembly.f90
 src/rd_6dof_modal.f90
 src/rd_6dof_campbell.f90
 src/rd_6dof_global_c_api.f90)
add_executable(test_6dof_global tests/test_6dof_global.f90)
target_link_libraries(test_6dof_global PRIVATE drmrotor)
target_include_directories(test_6dof_global PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
if(CMAKE_Fortran_COMPILER_ID STREQUAL "GNU")
 target_compile_options(test_6dof_global PRIVATE -ffree-line-length-none)
endif()
add_test(NAME sixdof_global_modal_campbell_native_contract COMMAND test_6dof_global)
"""

def git(*args: str) -> bytes:
    return subprocess.check_output(["git",*args],cwd=ROOT)

def verify() -> dict:
    subprocess.run(["git","merge-base","--is-ancestor",B1_PROMOTED_MAIN,"HEAD"],cwd=ROOT,check=True)
    for path in B1_IMMUTABLE_PATHS:
        subprocess.run(["git","diff","--exit-code",B1_PROMOTED_MAIN,"HEAD","--",path],cwd=ROOT,check=True)
    for path in PROMOTED_PRODUCT_PATHS:
        subprocess.run(["git","diff","--exit-code",B1_PROMOTED_MAIN,"HEAD","--",path],cwd=ROOT,check=True)
    # Every B1 validation file remains byte-identical except the inheritance
    # gate itself, whose exact B2-aware bytes are pinned below.
    tracked=git("ls-tree","-r","--name-only",B1_PROMOTED_MAIN,"--","validation/b1").decode().splitlines()
    for path in tracked:
        if path != B1_VALIDATION_GATE_EXCEPTION:
            subprocess.run(["git","diff","--exit-code",B1_PROMOTED_MAIN,"HEAD","--",path],cwd=ROOT,check=True)
    for path,expected_blob in PINNED_B2_ADAPTER_BLOBS.items():
        if B3_MARKER.is_file() and path in B3_CONTROLLED_ADAPTERS:
            continue
        actual=git("hash-object",path).decode().strip()
        if actual != expected_blob:
            raise ValueError(f"B2 adapter bytes changed: {path}: {actual} != {expected_blob}")
    before=git("show",f"{B1_PROMOTED_MAIN}:fortran/CMakeLists.txt")
    # Compare committed Git bytes, not checkout bytes: Windows worktrees may use CRLF.
    # The preservation contract is repository-byte exact and must be platform invariant.
    after=git("show","HEAD:fortran/CMakeLists.txt")
    expected=before+B2_CMAKE_APPEND
    if B3_MARKER.is_file():
        from validation.b3.preservation import B3_CMAKE_APPEND
        expected=expected+B3_CMAKE_APPEND
    if C1_MARKER.is_file():
        from validation.c1.preservation import C1_CMAKE_APPEND
        expected=expected+C1_CMAKE_APPEND
    if after != expected:
        raise ValueError("B2/B3/C1 CMake integration differs from the exact additive suffix")
    return {
        "status":"PASS",
        "b1_promoted_main":B1_PROMOTED_MAIN,
        "immutable_paths":list(B1_IMMUTABLE_PATHS),
        "promoted_product_paths":list(PROMOTED_PRODUCT_PATHS),
        "cmake":"EXACT_B2_ADDITIVE_SUFFIX",
        "pinned_b2_adapter_blobs":dict(PINNED_B2_ADAPTER_BLOBS),
    }

if __name__=="__main__":
    import json
    print("B2_B1_PRESERVATION",json.dumps(verify(),sort_keys=True))
