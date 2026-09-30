"""Fail-closed tests for B1 authority generation/inventory, not native physics."""
from __future__ import annotations

import ast
import copy
import os
from pathlib import Path
import shutil
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from validation.b1.authority_common import (
    REPO_ROOT, GENERATOR_PATH, INPUT_PATH, check_candidate, read_json, validate_array, validate_spec,
)


@pytest.fixture
def spec():
    return read_json(REPO_ROOT / INPUT_PATH)


def test_published_case_contract(spec):
    validate_spec(spec)


@pytest.mark.parametrize("mutation", ["missing_shaft", "missing_disk", "duplicate_id", "wrong_order", "unexpected_matrix", "wrong_count", "three_elastic_constants", "invalid_geometry", "nonfinite"])
def test_bad_input_specification_fails_closed(spec, mutation):
    s = copy.deepcopy(spec)
    if mutation == "missing_shaft": s["shaft_cases"].pop()
    elif mutation == "missing_disk": s["disk_cases"].pop()
    elif mutation == "duplicate_id": s["shaft_cases"][1]["id"] = s["shaft_cases"][0]["id"]
    elif mutation == "wrong_order": s["node_dof_order"][0:2] = ["y", "x"]
    elif mutation == "unexpected_matrix": s["shaft_outputs"].append("C")
    elif mutation == "wrong_count": s["expected_generated_matrix_count"] = 112
    elif mutation == "three_elastic_constants": s["materials"]["A"]["Poisson"] = 0.3
    elif mutation == "invalid_geometry": s["shaft_base"]["L"] = 0.
    elif mutation == "nonfinite": s["shaft_base"]["torque"] = float("nan")
    with pytest.raises(ValueError): validate_spec(s)


@pytest.mark.parametrize("bad", [np.ones((12, 12), dtype=np.float32), np.ones((6, 6)), np.full((12, 12), np.nan), np.full((12, 12), np.inf)])
def test_bad_matrix_rejected(bad):
    with pytest.raises(ValueError): validate_array(bad, (12, 12))


def test_generator_direct_calls_and_no_alternative_matrix_solver():
    tree = ast.parse((REPO_ROOT / GENERATOR_PATH).read_text(encoding="utf-8"))
    source = ast.unparse(tree)
    assert "np.linalg" not in source and "scipy.linalg" not in source and "drm_core" not in source
    calls = [n.func for n in ast.walk(tree) if isinstance(n, ast.Call)]
    constructors = {n.attr for n in calls if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "ross"}
    assert {"Material", "ShaftElement", "DiskElement"} <= constructors
    direct = [n.attr for n in calls if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "element"]
    assert direct.count("M") == 2 and direct.count("G") == 2
    assert direct.count("K") == 1 and direct.count("Kst") == 1 and direct.count("Kdt") == 1
    # No literal matrix construction in the generator. Array I/O is delegated,
    # and the only supplementary arrays are direct index selections.
    assert not any(isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "np" and n.attr in {"array", "zeros", "ones", "eye", "diag"} for n in calls)


@pytest.fixture
def candidate():
    path = os.environ.get("B1_CANDIDATE")
    assert path, "B1_CANDIDATE is mandatory; do not skip the executed-data tests"
    p = Path(path)
    assert p.is_dir()
    return p


def test_all_generated_arrays_and_selections(candidate):
    authority, _, arrays = check_candidate(candidate)
    assert authority["matrix_count"] == 113
    assert authority["lateral_selection_count"] == 63
    assert len(arrays) == 176


@pytest.mark.parametrize("mutation", ["missing", "extra", "bytes", "metadata"])
def test_corrupt_candidate_rejected(candidate, tmp_path, mutation):
    dest = tmp_path / "candidate"
    shutil.copytree(candidate, dest)
    if mutation == "missing": (dest / "arrays/S01_M.npy").unlink()
    elif mutation == "extra": shutil.copyfile(dest / "arrays/S01_M.npy", dest / "arrays/UNEXPECTED.npy")
    elif mutation == "bytes":
        p = dest / "arrays/S01_M.npy"
        b = bytearray(p.read_bytes()); b[-1] ^= 1; p.write_bytes(b)
    elif mutation == "metadata": (dest / "cases.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError): check_candidate(dest)


def test_candidate_has_executed_independent_inspection(candidate):
    report = read_json(candidate / "inspection.json")
    assert report["status"] == "PASS" and report["failed_count"] == 0
    assert report["check_count"] > 500
