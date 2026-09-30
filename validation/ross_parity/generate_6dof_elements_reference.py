"""Generate B1 candidates by calling actual, explicitly pinned ROSS objects.

This validation-only script contains no element matrix equations or eigensolver.
It cannot write into the immutable authority directory or overwrite a candidate.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib
import inspect
import os
from pathlib import Path
import platform
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from validation.b1.authority_common import (
    REPO_ROOT, ROSS_SHA, START_HEAD, INPUT_PATH, GENERATOR_PATH, COMMON_PATH,
    FROZEN_PATH, NODE_ORDER, SHAFT_ORDER, CORE_SOURCES, LATERAL,
    check_checkout, check_candidate, data_digest, file_hash, git, head,
    read_json, require, run_bytes, save_array, source_record, validate_spec, write_json,
)


def scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        value = value.item()
    require(value is None or isinstance(value, (bool, str, int, float)), f"Unsupported metadata type: {type(value)}")
    return value


def properties(obj: Any, names: list[str]) -> tuple[dict[str, Any], list[str]]:
    found = {key: scalar(getattr(obj, key)) for key in names if hasattr(obj, key)}
    return found, [key for key in names if not hasattr(obj, key)]


def import_provenance(ross_root: Path, executed: set[str]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    modules: dict[str, str] = {}
    by_file: dict[str, list[str]] = {}
    for name, module in sorted(sys.modules.items()):
        if name != "ross" and not name.startswith("ross."):
            continue
        filename = getattr(module, "__file__", None)
        if filename is None:
            continue
        path = Path(inspect.getsourcefile(module) or filename).resolve()
        require(path.is_relative_to(ross_root), f"Imported ROSS module outside --ross-root: {name}: {path}")
        require(path.is_file(), f"Missing imported module source: {path}")
        modules[name] = str(path)
        by_file.setdefault(path.relative_to(ross_root).as_posix(), []).append(str(path))
    paths = set(by_file) | set(CORE_SOURCES) | executed
    # The unit registry definitions affect the constructor decorators. Include
    # build/dependency declarations and material data as explicit resources too.
    paths.update(["ross/new_units.txt", "pyproject.toml", "requirements.txt", "ross/available_materials.toml"])
    records = []
    for path in sorted(paths):
        role = "matrix_or_constructor_executed" if path in executed else "imported_transitively"
        if path in CORE_SOURCES:
            role = "mandatory_matrix_material_unit_source"
        elif path not in by_file:
            role = "runtime_resource_or_dependency_declaration" if path not in executed else role
        records.append(source_record(ross_root, path, sorted(set(by_file.get(path, []))), role))
    return records, modules


def function_ranges(ross: Any, root: Path) -> dict[str, Any]:
    functions = {}
    mapping = {"ShaftElement": (ross.ShaftElement, ["__init__", "dof_mapping", "M", "K", "G", "Kst"]),
               "DiskElement": (ross.DiskElement, ["__init__", "dof_mapping", "M", "G", "Kdt"]),
               "Material": (ross.Material, ["__init__"])}
    for clsname, (cls, names) in mapping.items():
        for name in names:
            wrapped = getattr(cls, name)
            function = inspect.unwrap(wrapped)
            lines, first = inspect.getsourcelines(function)
            path = Path(inspect.getsourcefile(function)).resolve()
            require(path.is_relative_to(root), "Function implementation outside frozen checkout")
            functions[f"{clsname}.{name}"] = {
                "path": path.relative_to(root).as_posix(), "first_line": first,
                "last_line": first + len(lines) - 1, "line_count": len(lines),
                "runtime_code_file": str(Path(wrapped.__code__.co_filename).resolve()),
                "runtime_code_first_line": wrapped.__code__.co_firstlineno,
                "unwrapped": wrapped is not function,
            }
    require(len(functions) == 12, "Function source-map inventory mismatch")
    return functions


def generate(ross_root: Path, output: Path, input_file: Path) -> dict[str, Any]:
    ross_root, output, input_file = ross_root.resolve(), output.resolve(), input_file.resolve()
    immutable = (REPO_ROOT / FROZEN_PATH).resolve()
    require(not output.is_relative_to(immutable) and not immutable.is_relative_to(output), "Generator cannot target immutable authority or its parent")
    require(not output.exists(), f"Refuse to overwrite candidate: {output}")
    require(input_file == (REPO_ROOT / INPUT_PATH).resolve(), "Use the published B1 input specification")
    require(input_file.read_bytes() == git(REPO_ROOT, "show", f"{START_HEAD}:{INPUT_PATH}"), "Published physical input specification changed")
    spec = read_json(input_file)
    validate_spec(spec)
    check_checkout(ross_root)
    # Check mandatory raw sources BEFORE import; recheck all imported sources after execution.
    for relative in CORE_SOURCES + ["ross/new_units.txt"]:
        source_record(ross_root, relative, [], "pre_import")
    require("ross" not in sys.modules, "ROSS was already imported before provenance validation")
    for relative in (INPUT_PATH, GENERATOR_PATH, COMMON_PATH):
        require((REPO_ROOT / relative).read_bytes() == git(REPO_ROOT, "show", f"HEAD:{relative}"), f"Uncommitted generator/input/helper: {relative}")
    pip_check = run_bytes([sys.executable, "-m", "pip", "check"]).decode("utf-8")
    freeze = run_bytes([sys.executable, "-m", "pip", "freeze", "--all"]).decode("utf-8")
    sys.path.insert(0, str(ross_root))
    ross = importlib.import_module("ross")
    import numpy as np
    import scipy
    require(Path(ross.__file__).resolve().is_relative_to(ross_root), "Wrong imported ROSS package")
    for name in ("Material", "ShaftElement", "DiskElement"):
        require(Path(inspect.getsourcefile(getattr(ross, name))).resolve().is_relative_to(ross_root), f"Wrong {name} implementation")
    output.mkdir(parents=True, exist_ok=False)
    (output / "input_specification.json").write_bytes(input_file.read_bytes())
    (output / "requirements-freeze.txt").write_bytes(freeze.encode("utf-8"))
    (output / "pip-check.txt").write_bytes(pip_check.encode("utf-8"))
    executed: set[str] = set()
    def profile_call(frame: Any, event: str, arg: Any) -> None:
        if event == "call":
            filename = Path(frame.f_code.co_filename)
            if filename.is_absolute():
                resolved = filename.resolve()
                if resolved.is_relative_to(ross_root):
                    executed.add(resolved.relative_to(ross_root).as_posix())
    cases: dict[str, Any] = {}
    arrays = []
    previous_profile = sys.getprofile()
    require(previous_profile is None, "Unexpected active profiler during authority generation")
    sys.setprofile(profile_call)
    try:
        for case in spec["shaft_cases"]:
            resolved = {**spec["shaft_base"], **case["overrides"]}
            material_key = resolved["material"]
            material_values = dict(spec["materials"][material_key])
            # Exactly two elastic constants are passed. Poisson is read back.
            material = ross.Material(**material_values)
            constructor = dict(resolved)
            constructor["material"] = material
            element = ross.ShaftElement(**constructor)
            # These seven direct method calls (four here, three below) are the
            # ONLY origins of the primary reference matrix values.
            matrices = {"M": element.M(), "K": element.K(), "G": element.G(), "Kst": element.Kst()}
            derived, unavailable = properties(element, [
                "L", "idl", "odl", "idr", "odr", "A_l", "A_r", "Ie_l", "Ie_r", "A", "Ie",
                "phi", "kappa", "a1", "a2", "b1", "b2", "gama", "delta", "m", "volume", "Im", "beam_cg",
                "axial_force", "torque", "shear_effects", "rotary_inertia", "gyroscopic", "shear_method_calc",
            ])
            material_effective, missing = properties(material, ["name", "rho", "E", "G_s", "Poisson"])
            require(not missing, "Required effective material properties missing")
            dofs = element.dof_mapping()
            require(dofs == dict(zip(SHAFT_ORDER, range(12))), f"Shaft DOF map mismatch: {case['id']}")
            cases[case["id"]] = {"kind": "shaft", "resolved_input": resolved,
                                  "material_input": material_values, "material_effective": material_effective,
                                  "derived": derived, "unavailable_attributes": unavailable,
                                  "mass_attribute_name": "m", "dof_mapping": dofs}
            for name, values in matrices.items():
                arrays.append(save_array(output, case["id"], name, values, "element", (12, 12)))
            if element.idl == element.idr and element.odl == element.odr and element.shear_method_calc == "cowper":
                for name in ("M", "K", "G"):
                    arrays.append(save_array(output, case["id"], name, matrices[name][np.ix_(LATERAL, LATERAL)], "lateral_selection", (8, 8)))
        for case in spec["disk_cases"]:
            inputs = {key: case[key] for key in ("n", "m", "Id", "Ip")}
            element = ross.DiskElement(**inputs)
            matrices = {"M": element.M(), "G": element.G(), "Kdt": element.Kdt()}
            effective, missing = properties(element, ["n", "m", "Id", "Ip"])
            require(not missing, "Required disk properties missing")
            dofs = element.dof_mapping()
            require(dofs == dict(zip([f"{d}_0" for d in NODE_ORDER], range(6))), "Disk DOF map mismatch")
            cases[case["id"]] = {"kind": "disk", "resolved_input": inputs, "derived": effective, "dof_mapping": dofs}
            for name, values in matrices.items():
                arrays.append(save_array(output, case["id"], name, values, "element", (6, 6)))
    finally:
        sys.setprofile(previous_profile)
    check_checkout(ross_root)
    sources, module_paths = import_provenance(ross_root, executed)
    write_json(output / "cases.json", cases)
    authority = {
        "schema_version": 1, "record_role": "ROSS_GENERATION_PROVENANCE_NOT_NATIVE_QUALIFICATION",
        "repository": "petrobras/ross", "ross_sha": ROSS_SHA,
        "generation_utc": datetime.now(timezone.utc).isoformat(),
        "generator_repository": "alegrettiLeonardo/RotorStudio", "generator_head": head(REPO_ROOT),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"), "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "python": sys.version, "python_executable": sys.executable, "numpy": np.__version__, "scipy": scipy.__version__,
        "platform": platform.platform(), "machine": platform.machine(),
        "ross_root": str(ross_root), "module_paths": module_paths, "sources": sources,
        "executed_ross_source_files": sorted(executed), "functions": function_ranges(ross, ross_root),
        "generator_path": GENERATOR_PATH, "generator_sha256": file_hash(REPO_ROOT / GENERATOR_PATH),
        "generator_helpers_sha256": {COMMON_PATH: file_hash(REPO_ROOT / COMMON_PATH)},
        "input_specification_path": INPUT_PATH, "input_specification_sha256": file_hash(input_file),
        "cases_sha256": file_hash(output / "cases.json"),
        "environment_sha256": {name: file_hash(output / name) for name in ("requirements-freeze.txt", "pip-check.txt")},
        "pip_check": "PASS", "case_count": {"shaft": 26, "disk": 3}, "matrix_count": 113,
        "lateral_selection_count": sum(r["category"] == "lateral_selection" for r in arrays),
        "lateral_scope": "Cylindrical Cowper M/K/G selections only; no legacy comparison performed",
        "node_dof_order": NODE_ORDER, "shaft_dof_order": SHAFT_ORDER,
        "storage_policy": "NPY v1.0, little-endian float64, Fortran-contiguous. [row,column] is physical indexing; no transpose.",
        "arrays": sorted(arrays, key=lambda r: r["filename"]),
    }
    authority["data_bundle_sha256"] = data_digest(authority)
    write_json(output / "authority.json", authority)
    check_candidate(output)
    print("B1_GENERATION " + __import__("json").dumps({
        "status": "PASS", "head": authority["generator_head"], "cases": authority["case_count"],
        "matrix_count": 113, "lateral_selections": authority["lateral_selection_count"],
        "data_bundle_sha256": authority["data_bundle_sha256"], "authority_sha256": file_hash(output / "authority.json"),
        "generator_sha256": authority["generator_sha256"], "input_sha256": authority["input_specification_sha256"],
        "numpy": authority["numpy"], "scipy": authority["scipy"], "native": "NOT_STARTED",
    }, sort_keys=True))
    for record in sources:
        if record["path"] in CORE_SOURCES or record["path"] in executed or record["path"] == "ross/new_units.txt":
            print("B1_SOURCE " + __import__("json").dumps(record, sort_keys=True))
    print("B1_FUNCTION_RANGES " + __import__("json").dumps(authority["functions"], sort_keys=True))
    return authority


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ross-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--input", type=Path, default=REPO_ROOT / INPUT_PATH)
    args = parser.parse_args()
    generate(args.ross_root, args.out, args.input)


if __name__ == "__main__":
    main()
