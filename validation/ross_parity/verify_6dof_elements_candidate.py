"""Read-only B1 authority integrity and numerical reproduction checks.

No ROSS or native solver is executed here. All primary and supplementary arrays
are compared independently; frozen serialization hashes are not used as a
substitute for cross-platform numerical comparison.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from validation.b1.authority_common import (
    REPO_ROOT, ROSS_SHA, GENERATOR_PATH, COMMON_PATH, INPUT_PATH, FROZEN_PATH,
    CORE_SOURCES, LATERAL, AXIAL, TORSION, check_candidate, file_hash,
    read_json, require, safe_file, write_json, head,
)

POLICY_PATH = REPO_ROOT / "validation/b1/TOLERANCE_POLICY.json"
REVIEW_PATH = REPO_ROOT / "validation/b1/FREEZE_REVIEW.json"
INSPECTOR_PATH = REPO_ROOT / "validation/b1/inspect_candidate.py"


def snapshot(root: Path) -> dict[str, str]:
    require(root.is_dir(), f"Missing reference directory: {root}")
    result = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), f"Symlink not accepted in reference: {path}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = file_hash(path)
    return result


def recorded_relative(filename: str, root: str) -> str:
    name, base = filename.replace("\\", "/"), root.replace("\\", "/").rstrip("/")
    require(name.startswith(base + "/"), f"Recorded module escaped declared ROSS root: {filename}")
    relative = name[len(base) + 1:]
    require(".." not in PurePosixPath(relative).parts, "Parent traversal in recorded source path")
    return relative


def validate_provenance(root: Path, authority: dict[str, Any]) -> dict[str, Any]:
    require(authority["repository"] == "petrobras/ross" and authority["ross_sha"] == ROSS_SHA, "Wrong source repository/revision")
    require(authority["pip_check"] == "PASS", "Dependency check did not pass")
    require(set(authority["environment_sha256"]) == {"requirements-freeze.txt", "pip-check.txt"}, "Incomplete environment evidence")
    for path, digest in authority["environment_sha256"].items():
        require(file_hash(safe_file(root, path)) == digest, f"Environment evidence hash mismatch: {path}")
    require("No broken requirements found" in (root / "pip-check.txt").read_text(encoding="utf-8"), "Missing pip check result")
    require(authority["generator_path"] == GENERATOR_PATH, "Unexpected generator path")
    require(authority["generator_sha256"] == file_hash(REPO_ROOT / GENERATOR_PATH), "Generator hash differs from executed reference")
    require(authority["generator_helpers_sha256"] == {COMMON_PATH: file_hash(REPO_ROOT / COMMON_PATH)}, "Generator helper changed")
    require(authority["input_specification_sha256"] == file_hash(REPO_ROOT / INPUT_PATH), "Published input specification changed")
    require(re.fullmatch(r"[0-9a-f]{40}", authority["generator_head"]) is not None, "Invalid generator HEAD")
    sources = {}
    for record in authority["sources"]:
        path = record["path"]
        require(path not in sources, "Duplicate authority source record")
        require(record["git_commit"] == ROSS_SHA, "Source record commit mismatch")
        require(re.fullmatch(r"[0-9a-f]{40}", record["git_blob_id"]) is not None, "Git blob identity missing")
        require(re.fullmatch(r"[0-9a-f]{64}", record["git_blob_sha256"]) is not None, "Raw source SHA256 missing")
        require(record["git_blob_sha256"] == record["checkout_sha256"], "Git blob/checkout raw-byte mismatch")
        require(recorded_relative(record["checkout_path"], authority["ross_root"]) == path, "Recorded source path mismatch")
        for module_path in record["imported_module_paths"]:
            require(recorded_relative(module_path, authority["ross_root"]) == path, "Imported source path mismatch")
        sources[path] = {key: record[key] for key in ("path", "git_commit", "git_blob_id", "git_blob_sha256", "checkout_sha256", "role")}
    require(set(CORE_SOURCES + ["ross/new_units.txt"]).issubset(sources), "Missing mandatory influencing source/resource")
    require(set(authority["executed_ross_source_files"]).issubset(sources), "Executed source not recorded")
    for name, path in authority["module_paths"].items():
        relative = recorded_relative(path, authority["ross_root"])
        require(relative in sources, f"Imported module not hashed: {name}")
    functions = {}
    for name, value in authority["functions"].items():
        require(value["path"] in sources, "Function source not hashed")
        require(value["first_line"] > 0 and value["last_line"] - value["first_line"] + 1 == value["line_count"], "Invalid dynamic source range")
        functions[name] = dict(value)
        functions[name]["runtime_code_file"] = recorded_relative(value["runtime_code_file"], authority["ross_root"])
        require(functions[name]["runtime_code_file"] in sources, "Runtime wrapper source not hashed")
    require(len(functions) == 12, "Incomplete function inventory")
    return {"sources": sources, "functions": functions,
            "executed_sources": authority["executed_ross_source_files"],
            "module_sources": {name: recorded_relative(path, authority["ross_root"]) for name, path in authority["module_paths"].items()}}


def validate_policy(policy: dict[str, Any]) -> None:
    expected = {"shaft_M_lateral", "shaft_M_axial", "shaft_M_torsional", "shaft_K_lateral", "shaft_K_axial", "shaft_K_torsional",
                "shaft_axial_load_addition", "shaft_torque_addition", "shaft_G", "shaft_Kst", "disk_M", "disk_G", "disk_Kdt"}
    require(set(policy["blocks"]) == expected, "Incomplete block-specific tolerance policy")
    require(policy["binary64_epsilon"] == float(np.finfo(float).eps), "Incorrect epsilon")
    for block in list(policy["blocks"].values()) + [policy["derived_metadata"]]:
        require(all(math.isfinite(block[key]) and block[key] >= 0 for key in ("rtol", "atol")), "Invalid tolerance")
        require(block["atol"] == 0, "B1 reviewed policy has no global absolute tolerance")
        require(bool(block["reason"]), "Missing tolerance rationale")
    for key in ("shaft_axial_load_addition", "shaft_torque_addition"):
        require(policy["blocks"][key]["cancellation_epsilon_multiplier"] == 16, "Unexpected subtraction-roundoff policy")


def validate_inspection(root: Path, authority: dict[str, Any]) -> None:
    audit = read_json(safe_file(root, "inspection.json"))
    require(audit["status"] == "PASS" and audit["failed_count"] == 0 and not audit["failures"], "Candidate inspection failed")
    require(audit["check_count"] == 670 and len(audit["checks"]) == 670, "Independent audit coverage changed")
    require(all(c["status"] == "PASS" for c in audit["checks"]), "A failed independent check is hidden by the summary")
    require(audit["data_bundle_sha256"] == authority["data_bundle_sha256"], "Stale inspection data digest")
    require(audit["authority_sha256"] == file_hash(root / "authority.json"), "Stale inspection provenance")
    require(audit["inspector_sha256"] == file_hash(INSPECTOR_PATH), "Independent inspector hash changed")


def verify_frozen_integrity(reference: Path) -> dict[str, Any]:
    actual = snapshot(reference)
    sums = read_json(safe_file(reference, "SHA256SUMS.json"))
    require(sums["files"] == {k: v for k, v in actual.items() if k != "SHA256SUMS.json"}, "Frozen file inventory/bytes changed")
    review = read_json(REVIEW_PATH)
    require((reference / "FREEZE_REVIEW.json").read_bytes() == REVIEW_PATH.read_bytes(), "Frozen review anchor differs")
    require((reference / "tolerances.json").read_bytes() == POLICY_PATH.read_bytes(), "Frozen tolerance policy changed")
    require(actual["authority.json"] == review["linux_authority_sha256"], "Not the inspected first Linux authority")
    authority, _, _ = check_candidate(reference)
    require(authority["generator_head"] == review["reviewed_head"], "Unreviewed generation HEAD")
    require(authority["data_bundle_sha256"] == review["reviewed_data_bundle_sha256"], "Frozen data differs from reviewed candidate")
    provenance = validate_provenance(reference, authority)
    for path, digest in review["source_sha256"].items():
        require(provenance["sources"][path]["checkout_sha256"] == digest, "Reviewed source hash changed")
    validate_inspection(reference, authority)
    freeze = read_json(safe_file(reference, "FREEZE_RECORD.json"))
    require(freeze["review_sha256"] == file_hash(REVIEW_PATH), "Freeze review hash mismatch")
    require(freeze["tolerances_sha256"] == actual["tolerances.json"], "Freeze tolerance hash mismatch")
    require(freeze["source_candidate_authority_sha256"] == actual["authority.json"], "Freeze candidate hash mismatch")
    require(freeze["native_implementation"] == "NOT_STARTED" and freeze["ABI"] == "NOT_STARTED", "Authority freeze must not claim native qualification")
    return {"status": "PASS", "frozen_file_count": len(actual), "sha256sums_sha256": actual["SHA256SUMS.json"],
            "authority_sha256": actual["authority.json"], "tolerances_sha256": actual["tolerances.json"],
            "data_bundle_sha256": authority["data_bundle_sha256"]}


def compare_entries(candidate: np.ndarray, reference: np.ndarray, tolerance: dict[str, Any], floor: Any = 0.0, exact_pattern: bool = True) -> dict[str, Any]:
    require(candidate.shape == reference.shape, "Comparison shape mismatch")
    with np.errstate(over="raise", invalid="raise", divide="ignore"):
        error = np.abs(candidate - reference)
        budget = tolerance["atol"] + tolerance["rtol"] * np.abs(reference) + np.broadcast_to(floor, reference.shape)
        nonzero = reference != 0
        relative = np.divide(error, np.abs(reference), out=np.zeros_like(error), where=nonzero)
        zero_budget_error = bool(np.any((budget == 0) & (error != 0)))
        ratios = np.divide(error, budget, out=np.zeros_like(error), where=budget != 0)
    patterns = int(np.count_nonzero((candidate == 0) != (reference == 0)))
    passed = bool(np.all(error <= budget)) and (not exact_pattern or patterns == 0)
    return {"status": "PASS" if passed else "FAIL", "max_absolute_difference": float(error.max(initial=0)),
            "max_relative_difference_nonzero": float(relative.max(initial=0)),
            "max_budget_ratio": None if zero_budget_error else float(ratios.max(initial=0)),
            "zero_budget_violation": zero_budget_error, "zero_pattern_differences": patterns,
            "failed_entries": int(np.count_nonzero(error > budget)), "entry_count": int(error.size)}


def compare_metadata(received: Any, expected: Any, tolerance: dict[str, Any], path: str = "cases") -> list[str]:
    errors = []
    if isinstance(expected, dict):
        if not isinstance(received, dict) or set(received) != set(expected):
            return [f"{path}: dictionary keys/types differ"]
        for key, value in expected.items():
            # Case input, IDs, flags and DOF mapping are exact; only constructor
            # derived numeric values receive the predeclared scalar tolerance.
            if key in ("resolved_input", "material_input", "dof_mapping"):
                if received[key] != value: errors.append(f"{path}.{key}: exact metadata mismatch")
            else:
                errors.extend(compare_metadata(received[key], value, tolerance, f"{path}.{key}"))
    elif isinstance(expected, list):
        if not isinstance(received, list) or len(received) != len(expected): return [f"{path}: list mismatch"]
        for i, value in enumerate(expected): errors.extend(compare_metadata(received[i], value, tolerance, f"{path}[{i}]"))
    elif type(expected) is float:
        if type(received) not in (int, float) or not math.isfinite(received) or abs(received - expected) > tolerance["atol"] + tolerance["rtol"] * abs(expected):
            errors.append(f"{path}: derived scalar mismatch")
    elif received != expected or type(received) is not type(expected):
        errors.append(f"{path}: exact metadata mismatch")
    return errors


def compare_bundles(reference: Path, candidate: Path, policy: dict[str, Any]) -> dict[str, Any]:
    validate_policy(policy)
    ra, rc, rvalues = check_candidate(reference)
    ca, cc, cvalues = check_candidate(candidate)
    rp, cp = validate_provenance(reference, ra), validate_provenance(candidate, ca)
    require(rp == cp, "Source/import/function provenance differs from frozen ROSS")
    require(set(rvalues) == set(cvalues), "Different matrix inventories")
    metadata_errors = compare_metadata(cc, rc, policy["derived_metadata"])
    results, failures, summaries = [], [], {}
    primary_bytes, lateral_bytes, primary_values, lateral_values = 0, 0, 0, 0
    for record in ra["arrays"]:
        path, name = record["filename"], record["matrix"]
        a, b = cvalues[path], rvalues[path]
        is_primary = record["category"] == "element"
        byte_equal = file_hash(candidate / path) == file_hash(reference / path)
        value_bytes_equal = a.tobytes(order="F") == b.tobytes(order="F")
        if is_primary:
            primary_bytes += byte_equal; primary_values += value_bytes_equal
        else:
            lateral_bytes += byte_equal; lateral_values += value_bytes_equal
        if record["case_id"].startswith("D"):
            blocks = [(f"disk_{name}", np.ones(b.shape, dtype=bool))]
        elif not is_primary:
            key = f"shaft_{name}_lateral" if name in ("M", "K") else f"shaft_{name}"
            blocks = [(key, np.ones(b.shape, dtype=bool))]
        elif name in ("M", "K"):
            blocks = []
            covered = np.zeros(b.shape, dtype=bool)
            for label, indices in (("lateral", LATERAL), ("axial", AXIAL), ("torsional", TORSION)):
                mask = np.zeros(b.shape, dtype=bool); mask[np.ix_(indices, indices)] = True
                blocks.append((f"shaft_{name}_{label}", mask)); covered |= mask
            require(np.all(b[~covered] == 0) and np.all(a[~covered] == 0), f"Cross-block structural zero violated: {path}")
        else:
            blocks = [(f"shaft_{name}", np.ones(b.shape, dtype=bool))]
        block_results = []
        for key, mask in blocks:
            value = compare_entries(a[mask], b[mask], policy["blocks"][key])
            value.update({"block": key, "units": policy["blocks"][key]["units"]})
            block_results.append(value)
            group = summaries.setdefault(key, {"max_absolute_difference": 0.0, "max_relative_difference_nonzero": 0.0, "compared_entries": 0})
            for metric in ("max_absolute_difference", "max_relative_difference_nonzero"):
                group[metric] = max(group[metric], value[metric])
            group["compared_entries"] += value["entry_count"]
            if value["status"] != "PASS": failures.append({"filename": path, **value})
        results.append({"filename": path, "case_id": record["case_id"], "matrix": name,
                        "category": record["category"], "npy_bytes_equal": byte_equal,
                        "raw_value_bytes_equal": value_bytes_equal, "blocks": block_results})
    additions = []
    for prefix, key in (("S20", "shaft_axial_load_addition"), ("S21", "shaft_axial_load_addition"),
                        ("S22", "shaft_torque_addition"), ("S23", "shaft_torque_addition")):
        rbase = rvalues["arrays/S02_K.npy"][np.ix_(LATERAL, LATERAL)]
        cbase = cvalues["arrays/S02_K.npy"][np.ix_(LATERAL, LATERAL)]
        rload = rvalues[f"arrays/{prefix}_K.npy"][np.ix_(LATERAL, LATERAL)]
        cload = cvalues[f"arrays/{prefix}_K.npy"][np.ix_(LATERAL, LATERAL)]
        floor = policy["blocks"][key]["cancellation_epsilon_multiplier"] * policy["binary64_epsilon"] * (np.abs(rload) + np.abs(rbase))
        value = compare_entries(cload - cbase, rload - rbase, policy["blocks"][key], floor=floor, exact_pattern=False)
        value.update({"case": prefix, "block": key, "subtraction_floor_entrywise": True, "max_subtraction_floor": float(floor.max())})
        additions.append(value)
        if value["status"] != "PASS": failures.append(value)
    result = {"schema_version": 1, "status": "FAIL" if failures or metadata_errors else "PASS",
              "scope": "Frozen ROSS element-authority reproduction only; no native B1 comparison",
              "verification_head": head(REPO_ROOT), "ross_sha": ROSS_SHA,
              "reference_generator_head": ra["generator_head"], "candidate_generator_head": ca["generator_head"],
              "reference_platform": ra["platform"], "candidate_platform": ca["platform"],
              "reference_data_bundle_sha256": ra["data_bundle_sha256"], "candidate_data_bundle_sha256": ca["data_bundle_sha256"],
              "physics_metadata": "FAIL" if metadata_errors else "PASS", "metadata_errors": metadata_errors,
              "source_provenance": "PASS", "source_file_count": len(rp["sources"]), "function_count": len(rp["functions"]),
              "primary_matrices_compared": 113, "lateral_selections_compared": 63,
              "primary_npy_files_bitwise_equal": primary_bytes, "lateral_npy_files_bitwise_equal": lateral_bytes,
              "primary_raw_values_bitwise_equal": primary_values, "lateral_raw_values_bitwise_equal": lateral_values,
              "by_block": summaries, "load_additions": additions, "failures": failures, "arrays": results,
              "native_implementation": "NOT_STARTED", "ABI": "NOT_STARTED"}
    return result


def verify(reference: Path, candidate: Path, report_path: Path, review_only: bool = False, policy_path: Path | None = None) -> dict[str, Any]:
    reference, candidate, report_path = reference.resolve(), candidate.resolve(), report_path.resolve()
    require(reference != candidate and not candidate.is_relative_to(reference), "Candidate must be separate from reference")
    require(not report_path.is_relative_to(reference), "Report may not overwrite frozen authority")
    before = snapshot(reference)
    try:
        integrity = None if review_only else verify_frozen_integrity(reference)
        path = (policy_path or POLICY_PATH) if review_only else reference / "tolerances.json"
        require(path.read_bytes() == POLICY_PATH.read_bytes(), "Unreviewed tolerance policy")
        result = compare_bundles(reference, candidate, read_json(path))
        ca = read_json(candidate / "authority.json")
        validate_inspection(candidate, ca)
        result["mode"] = "CANDIDATE_REVIEW_ONLY" if review_only else "IMMUTABLE_AUTHORITY_REPRODUCTION"
        result["integrity"] = integrity
        result["policy_sha256"] = file_hash(path)
    finally:
        require(snapshot(reference) == before, "Read-only verification changed reference bytes")
    result["reference_unchanged"] = True
    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(report_path, result)
    print("B1_REPRODUCTION " + json.dumps({k: v for k, v in result.items() if k not in ("arrays",)}, sort_keys=True))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=REPO_ROOT / FROZEN_PATH)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--review-only", action="store_true", help="Compare temporary candidates before first freeze; never emit frozen qualification")
    parser.add_argument("--policy", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.reference, args.candidate, args.report, args.review_only, args.policy)
    except Exception as error:
        # Never write an error report into a protected reference path either.
        if not args.report.resolve().is_relative_to(args.reference.resolve()):
            args.report.parent.mkdir(parents=True, exist_ok=True)
            write_json(args.report, {"status": "FAIL", "error": str(error), "native_implementation": "NOT_STARTED"})
        raise
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
