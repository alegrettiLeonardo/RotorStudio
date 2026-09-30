"""B1 authority I/O and provenance helpers. No element matrix equations."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

ROSS_SHA = "6320eab9f890f1b3cc1710d508b446fe063ca68d"
BASE_MAIN = "fcdac252974aeeded6961dbe3310677e234a6495"
START_HEAD = "23a7624374418991fe700c2817150f67c5bd48fb"
REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = "validation/b1/element_cases.json"
GENERATOR_PATH = "validation/ross_parity/generate_6dof_elements_reference.py"
COMMON_PATH = "validation/b1/authority_common.py"
FROZEN_PATH = "validation/ross_parity/6dof_elements"
NODE_ORDER = ["x", "y", "z", "alpha", "beta", "theta"]
SHAFT_ORDER = [f"{d}_{n}" for n in (0, 1) for d in NODE_ORDER]
LATERAL = [0, 1, 3, 4, 6, 7, 9, 10]
AXIAL = [2, 8]
TORSION = [5, 11]
CORE_SOURCES = [
    "ross/shaft_element.py", "ross/disk_element.py", "ross/materials.py",
    "ross/element.py", "ross/units.py",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(canonical_bytes(value))


def read_json(path: Path) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key: {key} in {path}")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def run_bytes(args: list[str], cwd: Path | None = None) -> bytes:
    p = subprocess.run(args, cwd=cwd, capture_output=True, timeout=120)
    if p.returncode:
        raise RuntimeError(f"Command failed ({p.returncode}): {args}\n"
                           + p.stdout.decode("utf-8", "replace")
                           + p.stderr.decode("utf-8", "replace"))
    return p.stdout


def git(root: Path, *args: str) -> bytes:
    return run_bytes(["git", "-C", str(root), *args])


def head(root: Path) -> str:
    return git(root, "rev-parse", "HEAD").decode().strip()


def check_checkout(root: Path, expected: str = ROSS_SHA) -> None:
    require(head(root) == expected, f"Wrong ROSS HEAD: {head(root)}; expected {expected}")
    require(not git(root, "status", "--porcelain", "--untracked-files=no").strip(),
            "ROSS tracked checkout/index is dirty")
    require(git(root, "config", "--get", "core.autocrlf").strip() == b"false", "Require core.autocrlf=false")
    require(git(root, "config", "--get", "core.eol").strip() == b"lf", "Require core.eol=lf")


def source_record(root: Path, path: str, module_paths: list[str], role: str) -> dict[str, Any]:
    local = (root / path).resolve()
    require(local.is_relative_to(root.resolve()) and local.is_file(), f"Invalid source path: {path}")
    blob_id = git(root, "rev-parse", f"{ROSS_SHA}:{path}").decode().strip()
    blob = git(root, "cat-file", "blob", blob_id)
    working = local.read_bytes()
    require(blob == working, f"Raw source bytes differ from frozen Git blob: {path}")
    require(b"\r\n" not in working, f"Unexpected CRLF in frozen source/resource: {path}")
    return {"path": path, "git_commit": ROSS_SHA, "git_blob_id": blob_id,
            "git_blob_sha256": sha256(blob), "checkout_sha256": sha256(working),
            "checkout_path": str(local), "imported_module_paths": module_paths,
            "role": role}


def validate_spec(spec: dict[str, Any]) -> None:
    require(spec["ross_sha"] == ROSS_SHA and spec["ross_repository"] == "petrobras/ross", "Wrong manifest authority")
    require(spec["baseline_main"] == BASE_MAIN, "Wrong manifest baseline")
    require(spec["node_dof_order"] == NODE_ORDER, "Wrong node DOF order")
    require(spec["shaft_dof_order"] == SHAFT_ORDER, "Wrong shaft DOF order")
    require(spec["shaft_lateral_indices_zero_based"] == LATERAL, "Wrong lateral selection")
    require(spec["shaft_axial_indices_zero_based"] == AXIAL, "Wrong axial selection")
    require(spec["shaft_torsional_indices_zero_based"] == TORSION, "Wrong torsion selection")
    require(spec["shaft_outputs"] == ["M", "K", "G", "Kst"], "Unexpected shaft matrix requests")
    require(spec["disk_outputs"] == ["M", "G", "Kdt"], "Unexpected disk matrix requests")
    require(spec["matrix_shapes"] == {"shaft": [12, 12], "disk": [6, 6]}, "Wrong matrix shapes")
    require(len(spec["shaft_cases"]) == 26 and len(spec["disk_cases"]) == 3, "Require 26 shaft / 3 disk cases")
    require(spec["expected_case_counts"] == {"shaft": 26, "disk": 3}, "Wrong case counts")
    require(spec["expected_generated_matrix_count"] == 113, "Require 113 matrices")
    cases = spec["shaft_cases"] + spec["disk_cases"]
    ids = [c["id"] for c in cases]
    require(len(set(ids)) == 29, "Duplicate case ID")
    require(all(re.fullmatch(r"[SD][0-9]{2}_[A-Za-z0-9_]+", i) for i in ids), "Unsafe case ID")
    require(len({i.split("_", 1)[0] for i in ids}) == 29, "Duplicate case filename prefix")
    for material in spec["materials"].values():
        require(set(material) == {"name", "rho", "E", "G_s"}, "Material must use only rho/E/G_s and name")
        require(all(np.isfinite(material[k]) and material[k] > 0 for k in ("rho", "E", "G_s")), "Invalid material")
    combinations = set()
    for case in spec["shaft_cases"]:
        values = {**spec["shaft_base"], **case["overrides"]}
        require(values["material"] in spec["materials"], "Unknown material key")
        require(all(type(values[k]) is bool for k in ("shear_effects", "rotary_inertia", "gyroscopic")), "Flags must be booleans")
        combinations.add(tuple(values[k] for k in ("shear_effects", "rotary_inertia", "gyroscopic")))
        for key in ("L", "idl", "odl", "idr", "odr", "axial_force", "torque"):
            require(np.isfinite(values[key]), f"Nonfinite input: {case['id']} {key}")
        require(values["L"] > 0 and 0 <= values["idl"] < values["odl"] and 0 <= values["idr"] < values["odr"], "Invalid shaft geometry")
        require(values["shear_method_calc"] in ("cowper", "hutchinson"), "Unknown shear method")
    require(len(combinations) == 8, "Missing independent effect-flag combination")
    for case in spec["disk_cases"]:
        require(all(np.isfinite(case[k]) and case[k] > 0 for k in ("m", "Id", "Ip")), "Invalid disk")


def validate_array(value: Any, shape: tuple[int, int]) -> np.ndarray:
    arr = np.asarray(value)
    require(arr.dtype == np.dtype("float64"), f"Unexpected source dtype: {arr.dtype}")
    require(arr.shape == shape, f"Wrong array shape {arr.shape}; expected {shape}")
    require(bool(np.isfinite(arr).all()), "Nonfinite matrix output")
    return np.array(arr, dtype="<f8", order="F", copy=True)


def safe_file(root: Path, relative: str) -> Path:
    require(not Path(relative).is_absolute(), f"Absolute inventory path: {relative}")
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), f"Inventory path escapes root: {relative}")
    require(path.is_file(), f"Missing file: {relative}")
    return path


def save_array(root: Path, case: str, name: str, value: Any, category: str, shape: tuple[int, int]) -> dict[str, Any]:
    arr = validate_array(value, shape)
    prefix = case.split("_", 1)[0]
    folder = "arrays" if category == "element" else "lateral"
    relative = f"{folder}/{prefix}_{name}.npy"
    target = root / relative
    target.parent.mkdir(exist_ok=True)
    require(not target.exists(), f"Duplicate array file: {relative}")
    with target.open("xb") as stream:
        np.lib.format.write_array(stream, arr, version=(1, 0), allow_pickle=False)
    with target.open("rb") as stream:
        back = np.lib.format.read_array(stream, allow_pickle=False)
    require(back.tobytes(order="F") == arr.tobytes(order="F"), "Array serialization did not roundtrip")
    return {"case_id": case, "matrix": name, "category": category, "filename": relative,
            "shape": list(shape), "dtype": "<f8", "storage_order": "F",
            "sha256": file_hash(target), "values_sha256_f_order": sha256(arr.tobytes(order="F")),
            "nonzero_count": int(np.count_nonzero(arr))}


def data_digest(authority: dict[str, Any]) -> str:
    return sha256(canonical_bytes({"input_sha256": authority["input_specification_sha256"],
                                 "cases_sha256": authority["cases_sha256"],
                                 "arrays": authority["arrays"]}))


def check_candidate(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, np.ndarray]]:
    authority = read_json(root / "authority.json")
    spec_path = safe_file(root, "input_specification.json")
    require(file_hash(spec_path) == authority["input_specification_sha256"], "Input snapshot hash mismatch")
    spec = read_json(spec_path)
    validate_spec(spec)
    require(authority["ross_sha"] == ROSS_SHA, "Candidate authority SHA mismatch")
    require(authority["case_count"] == {"shaft": 26, "disk": 3} and authority["matrix_count"] == 113, "Candidate counts mismatch")
    require(authority["node_dof_order"] == NODE_ORDER and authority["shaft_dof_order"] == SHAFT_ORDER, "Candidate DOF order mismatch")
    require(file_hash(safe_file(root, "cases.json")) == authority["cases_sha256"], "Case metadata hash mismatch")
    cases = read_json(root / "cases.json")
    expected_core = {(c["id"], m) for kind in ("shaft", "disk") for c in spec[f"{kind}_cases"] for m in spec[f"{kind}_outputs"]}
    core = [r for r in authority["arrays"] if r["category"] == "element"]
    require(len(core) == 113 and {(r["case_id"], r["matrix"]) for r in core} == expected_core, "Missing/duplicate/unexpected element matrix")
    require(set(cases) == {c["id"] for c in spec["shaft_cases"] + spec["disk_cases"]}, "Case metadata inventory mismatch")
    eligible = set()
    for c in spec["shaft_cases"]:
        p = {**spec["shaft_base"], **c["overrides"]}
        if p["idl"] == p["idr"] and p["odl"] == p["odr"] and p["shear_method_calc"] == "cowper":
            eligible.add(c["id"])
    expected_lateral = {(cid, name) for cid in eligible for name in ("M", "K", "G")}
    lateral = [r for r in authority["arrays"] if r["category"] == "lateral_selection"]
    require(len(lateral) == len(expected_lateral) and {(r["case_id"], r["matrix"]) for r in lateral} == expected_lateral, "Lateral inventory mismatch")
    require(authority["lateral_selection_count"] == len(lateral), "Lateral count mismatch")
    require(len(authority["arrays"]) == 113 + len(lateral), "Unexpected array category")
    arrays: dict[str, np.ndarray] = {}
    for record in authority["arrays"]:
        relative = record["filename"]
        require(relative not in arrays, "Duplicate filename")
        path = safe_file(root, relative)
        require(file_hash(path) == record["sha256"], f"Array file hash mismatch: {relative}")
        arr = np.load(path, allow_pickle=False)
        shape = (8, 8) if record["category"] == "lateral_selection" else ((12, 12) if record["case_id"].startswith("S") else (6, 6))
        validate_array(arr, shape)
        require(record["shape"] == list(shape) and record["dtype"] == "<f8" and record["storage_order"] == "F", "Array descriptor mismatch")
        require(arr.flags.f_contiguous, "Expected column-major array storage")
        require(sha256(arr.tobytes(order="F")) == record["values_sha256_f_order"], "Raw values hash mismatch")
        require(int(np.count_nonzero(arr)) == record["nonzero_count"], "Nonzero inventory mismatch")
        arrays[relative] = arr
    actual_files = {p.relative_to(root).as_posix() for folder in ("arrays", "lateral") for p in (root / folder).rglob("*") if p.is_file()}
    require(actual_files == set(arrays), "Unexpected/missing array file on disk")
    for record in lateral:
        prefix = record["case_id"].split("_", 1)[0]
        core_arr = arrays[f"arrays/{prefix}_{record['matrix']}.npy"]
        require(np.array_equal(arrays[record["filename"]], core_arr[np.ix_(LATERAL, LATERAL)]), "Lateral selection is not a direct submatrix")
    require(data_digest(authority) == authority["data_bundle_sha256"], "Data bundle digest mismatch")
    return authority, cases, arrays
