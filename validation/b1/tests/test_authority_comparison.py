"""Exercise numerical comparison independently of self-consistent file hashes."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from validation.b1.authority_common import (
    LATERAL, REPO_ROOT, read_json, write_json, file_hash, sha256, data_digest,
)
from validation.ross_parity.verify_6dof_elements_candidate import (
    POLICY_PATH, compare_bundles, compare_entries, snapshot, verify,
)


@pytest.fixture
def original():
    value = os.environ.get("B1_CANDIDATE")
    assert value, "B1_CANDIDATE must identify actually generated data"
    path = Path(value)
    assert path.is_dir()
    return path


@pytest.fixture
def changed(original, tmp_path):
    target = tmp_path / "changed"
    shutil.copytree(original, target)
    return target


def refresh(root, filename, array):
    # Deliberately produce consistent attacker/corruption metadata: the numeric
    # comparator must still reject wrong physics even when hashes are refreshed.
    authority = read_json(root / "authority.json")
    replacements = {filename: np.array(array, dtype="<f8", order="F")}
    prefix, matrix = Path(filename).stem.split("_", 1)
    lateral_name = f"lateral/{prefix}_{matrix}.npy"
    if (root / lateral_name).is_file():
        replacements[lateral_name] = np.array(array[np.ix_(LATERAL, LATERAL)], dtype="<f8", order="F")
    for relative, values in replacements.items():
        with (root / relative).open("wb") as stream:
            np.lib.format.write_array(stream, values, version=(1, 0), allow_pickle=False)
        record = next(r for r in authority["arrays"] if r["filename"] == relative)
        record["sha256"] = file_hash(root / relative)
        record["values_sha256_f_order"] = sha256(values.tobytes(order="F"))
        record["nonzero_count"] = int(np.count_nonzero(values))
    authority["data_bundle_sha256"] = data_digest(authority)
    write_json(root / "authority.json", authority)


def compare(original, changed):
    return compare_bundles(original, changed, read_json(POLICY_PATH))


def test_identical_reproduction_is_exact_and_read_only(original, changed, tmp_path):
    before = snapshot(original)
    result = verify(original, changed, tmp_path / "comparison.json", review_only=True)
    assert result["status"] == "PASS"
    assert result["primary_matrices_compared"] == 113 and result["primary_npy_files_bitwise_equal"] == 113
    assert result["lateral_npy_files_bitwise_equal"] == 63
    assert before == snapshot(original)


@pytest.mark.parametrize("mutation", ["tiny_new_zero", "Kst_transposed", "small_torsional_error", "torque_sign", "disk_inertia_swap"])
def test_wrong_physics_rejected_despite_refreshed_hashes(original, changed, mutation):
    filename = {"tiny_new_zero": "arrays/S03_Kst.npy", "Kst_transposed": "arrays/S03_Kst.npy",
                "small_torsional_error": "arrays/S16_K.npy", "torque_sign": "arrays/S22_K.npy",
                "disk_inertia_swap": "arrays/D01_M.npy"}[mutation]
    a = np.load(changed / filename, allow_pickle=False).copy(order="F")
    if mutation == "tiny_new_zero": a[2, 2] = 1e-300
    elif mutation == "Kst_transposed": a = a.T
    elif mutation == "small_torsional_error": a[5, 5] += 1e-6
    elif mutation == "torque_sign": a[3, 4] = -a[3, 4]
    elif mutation == "disk_inertia_swap": a[3, 3], a[5, 5] = a[5, 5], a[3, 3]
    refresh(changed, filename, a)
    result = compare(original, changed)
    assert result["status"] == "FAIL" and result["failures"]


def test_permitted_roundoff_is_not_confused_with_serialization_integrity(original, changed):
    filename = "arrays/S16_M.npy"
    a = np.load(changed / filename, allow_pickle=False).copy(order="F")
    a[0, 0] *= 1 + 1e-14
    refresh(changed, filename, a)
    result = compare(original, changed)
    assert result["status"] == "PASS"
    assert result["primary_npy_files_bitwise_equal"] == 112
    assert result["by_block"]["shaft_M_lateral"]["max_absolute_difference"] > 0


def test_signed_zero_bytes_do_not_change_physics(original, changed):
    filename = "arrays/S03_Kst.npy"
    a = np.load(changed / filename, allow_pickle=False).copy(order="F")
    a[2, 2] = -0.0
    refresh(changed, filename, a)
    result = compare(original, changed)
    assert result["status"] == "PASS" and result["primary_npy_files_bitwise_equal"] == 112


@pytest.mark.parametrize("mutation", ["blob_checkout_disagree", "self_consistent_wrong_source", "outside_import", "wrong_generator", "wrong_function_range", "pip_evidence_corrupt"])
def test_provenance_guard_rejects_tampering(original, changed, mutation):
    a = read_json(changed / "authority.json")
    if mutation == "blob_checkout_disagree": a["sources"][0]["checkout_sha256"] = "f" * 64
    elif mutation == "self_consistent_wrong_source":
        a["sources"][0]["checkout_sha256"] = a["sources"][0]["git_blob_sha256"] = "f" * 64
    elif mutation == "outside_import": a["module_paths"]["ross"] = "/outside/site-packages/ross/__init__.py"
    elif mutation == "wrong_generator": a["generator_sha256"] = "f" * 64
    elif mutation == "wrong_function_range":
        a["functions"]["ShaftElement.M"]["first_line"] += 1
        a["functions"]["ShaftElement.M"]["last_line"] += 1
    elif mutation == "pip_evidence_corrupt": (changed / "pip-check.txt").write_text("PASS", encoding="utf-8")
    write_json(changed / "authority.json", a)
    with pytest.raises(ValueError): compare(original, changed)


def test_derived_physics_metadata_rejected_with_refreshed_hash(original, changed):
    cases = read_json(changed / "cases.json")
    cases["S02_hollow_all_effects"]["derived"]["phi"] *= 1.01
    write_json(changed / "cases.json", cases)
    a = read_json(changed / "authority.json")
    a["cases_sha256"] = file_hash(changed / "cases.json")
    a["data_bundle_sha256"] = data_digest(a)
    write_json(changed / "authority.json", a)
    result = compare(original, changed)
    assert result["status"] == "FAIL" and result["metadata_errors"]


def test_report_cannot_overwrite_reference(original, changed):
    before = snapshot(original)
    with pytest.raises(ValueError): verify(original, changed, original / "authority.json", review_only=True)
    assert snapshot(original) == before


def test_block_comparison_not_dominated_by_large_unrelated_stiffness():
    policy = read_json(POLICY_PATH)
    r = np.array([1e-3, 1e9]); c = np.array([1.000001e-3, 1e9])
    assert compare_entries(c, r, policy["blocks"]["shaft_K_lateral"])["status"] == "FAIL"
    assert np.allclose(c, r, rtol=0, atol=1e-3)  # deliberately unsuitable global bound
