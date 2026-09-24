from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import re
import sys
from pathlib import Path

import numpy as np
import scipy
from scipy.io import loadmat

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from comparators import (  # noqa: E402
    ANALYTICAL_REL,
    EIG_REL,
    FREQ_REL,
    MATRIX_REL,
    RESPONSE_REL,
    eigenvalues as compare_eigenvalues,
    frequencies as compare_frequencies,
    matrix as compare_matrix,
    response as compare_response,
    scalar_vector,
)
from cases import SOLVER_CASES, HYBRID_CASES  # noqa: E402
from inventory import verify_inventory  # noqa: E402

from drm_core import (  # noqa: E402
    AnalysisCase,
    AnalysisService,
    Bearing,
    Node,
    RotorModel,
    ShaftElement,
)

NUMBER = re.compile(r"(?<![A-Za-z_])[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")
KNOWN_OCTAVE_NA = {
    "03_12": "GNU Octave 7.1.0 reserves `do` as syntax; the unmodified MATLAB script cannot be parsed. B_ANALYTICAL source-derived oracle used instead."
}


def rows(a):
    x = np.asarray(a)
    if x.size == 0:
        return []
    if x.ndim == 0:
        return [[float(x)]]
    if x.ndim == 1:
        return [x.tolist()]
    return x.tolist()


def get(s, name):
    return s[name] if isinstance(s, dict) and name in s and s[name] is not None else []


def model_from_struct(s):
    node = np.asarray(get(s, "node"))
    if node.ndim == 1:
        node = node.reshape(-1, 1)
    if node.shape[1] == 1:
        node = np.column_stack([np.arange(1, len(node) + 1), node[:, 0]])
    return RotorModel.from_legacy_arrays(
        rows(node),
        rows(get(s, "shaft")),
        rows(get(s, "disc")),
        rows(get(s, "bearing")),
        rows(get(s, "force")),
        rows(get(s, "bend")),
        rows(get(s, "rotors")),
    )


def sample_indices(n: int) -> list[int]:
    if n <= 9:
        return list(range(n))
    return sorted(set([0, n // 10, n // 5, n // 3, n // 2, 2 * n // 3, 4 * n // 5, 9 * n // 10, n - 1]))


def matrix2(x):
    a = np.asarray(x)
    if a.ndim == 0:
        return a.reshape(1, 1).astype(complex)
    if a.ndim == 1:
        return a[:, None].astype(complex)
    return a.astype(complex)


def parse_numeric_stdout(path: Path) -> np.ndarray:
    vals = []
    for token in NUMBER.findall(path.read_text(errors="replace")):
        try:
            vals.append(float(token))
        except ValueError:
            pass
    return np.asarray(vals, dtype=float)


def load_probe(path: Path) -> tuple[list[str], np.ndarray]:
    if not path.is_file():
        return [], np.empty((0, 9), float)
    names, probe_rows = [], []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            names.append(row["name"])
            probe_rows.append(
                [
                    float(row["numel"]),
                    float(row["sum_real"]),
                    float(row["sum_imag"]),
                    float(row["sum_abs"]),
                    float(row["sum_abs2"]),
                    float(row["first_real"]),
                    float(row["first_imag"]),
                    float(row["last_real"]),
                    float(row["last_imag"]),
                ]
            )
    return names, np.asarray(probe_rows, dtype=float)


def check_reference_determinism(cid: str, run1: Path, run2: Path) -> dict:
    p1_path = run1 / "numeric_probes" / f"Problem_{cid}.csv"
    p2_path = run2 / "numeric_probes" / f"Problem_{cid}.csv"
    n1, p1 = load_probe(p1_path)
    n2, p2 = load_probe(p2_path)
    if n1 and n1 == n2 and p1.shape == p2.shape:
        cmp = scalar_vector(p1, p2, ANALYTICAL_REL)
        if cmp["pass"]:
            return {
                "status": "PASS",
                "mechanism": "numeric_workspace_signature",
                "numeric_variable_count": len(n1),
                "variables": n1,
                "metric": cmp,
                "probe_run1_sha256": hashlib.sha256(p1_path.read_bytes()).hexdigest(),
                "probe_run2_sha256": hashlib.sha256(p2_path.read_bytes()).hexdigest(),
            }

    s1_path = run1 / "stdout" / f"Problem_{cid}.txt"
    s2_path = run2 / "stdout" / f"Problem_{cid}.txt"
    s1 = parse_numeric_stdout(s1_path)
    s2 = parse_numeric_stdout(s2_path)
    if s1.size == 0:
        return {
            "status": "FAIL",
            "reason": "no deterministic numeric workspace signature or stdout response",
            "numeric_count": 0,
        }
    cmp = scalar_vector(s1, s2, ANALYTICAL_REL)
    return {
        "status": "PASS" if cmp["pass"] else "FAIL",
        "mechanism": "numeric_stdout",
        "numeric_count": int(s1.size),
        "metric": cmp,
        "stdout_run1_sha256": hashlib.sha256(s1_path.read_bytes()).hexdigest(),
        "stdout_run2_sha256": hashlib.sha256(s2_path.read_bytes()).hexdigest(),
    }


def _execute_modal(service: AnalysisService, model: RotorModel, speeds: np.ndarray, asymmetric=False):
    cols = []
    for speed in speeds:
        kind = "asymmetric_modal" if asymmetric else "modal"
        execution = service.execute(
            model,
            AnalysisCase(kind, {"speed_rad_s": float(speed)}, name=f"G14-{kind}"),
        )
        cols.append(np.asarray(execution.result.eigenvalues))
    return np.column_stack(cols)


def run_solver_case(cid: str, workspace: dict, service: AnalysisService) -> dict:
    cfg = SOLVER_CASES[cid]
    model = model_from_struct(workspace[cfg["model"]])
    speeds = np.asarray(workspace[cfg["speed"]], float).reshape(-1)
    reference = matrix2(workspace[cfg["reference"]])
    indices = sample_indices(len(speeds))
    selected = speeds[indices]

    if cfg["kind"] == "modal":
        actual = _execute_modal(service, model, selected, False)
        expected = reference[:, indices] if reference.shape[1] > 1 else reference
        comparison = compare_eigenvalues(expected, actual)
    elif cfg["kind"] == "asymmetric_modal":
        actual = _execute_modal(service, model, selected, True)
        expected = reference[:, indices] if reference.shape[1] > 1 else reference
        comparison = compare_eigenvalues(expected, actual)
    elif cfg["kind"] == "response":
        execution = service.execute(
            model,
            AnalysisCase("frequency_response", {"speeds_rad_s": selected}, name=f"G14-{cid}"),
        )
        actual = np.asarray(execution.result.response)
        expected = reference[:, indices]
        comparison = compare_response(expected, actual)
    else:
        raise AssertionError(cfg)

    return {
        "status": "PASS" if comparison["pass"] else "FAIL",
        "product_path": "AnalysisService -> SolverFacade -> ctypes -> Fortran",
        "kind": cfg["kind"],
        "sample_count": len(indices),
        "sample_indices": indices,
        "comparator": comparison,
    }


def _beam_material(d=1.0):
    area = math.pi * d * d / 4.0
    inertia = math.pi * d**4 / 64.0
    return d, 1.0 / area, 1.0 / inertia


def _beam_model(ne: int, bc: str) -> RotorModel:
    d, rho, young = _beam_material()
    nodes = [Node(i + 1, i / ne) for i in range(ne + 1)]
    shafts = [
        ShaftElement(1, i, i + 1, d, 0.0, rho, young, 0.0, 0.0)
        for i in range(1, ne + 1)
    ]
    if bc == "pinned-pinned":
        bearings = [Bearing(1, 1), Bearing(1, ne + 1)]
    elif bc == "clamped-clamped":
        bearings = [Bearing(2, 1), Bearing(2, ne + 1)]
    elif bc == "clamped-pinned":
        bearings = [Bearing(2, 1), Bearing(1, ne + 1)]
    else:
        raise ValueError(bc)
    return RotorModel(nodes, shafts, [], bearings)


def _positive_unique_omega(eigenvalues, count):
    values = np.sort(
        np.abs(np.imag(np.asarray(eigenvalues)[np.imag(np.asarray(eigenvalues)) > 1e-9]))
    )
    unique = []
    for value in values:
        if not unique or abs(value - unique[-1]) > max(1e-9, abs(value) * 1e-9):
            unique.append(float(value))
    if len(unique) < count:
        raise AssertionError(
            f"expected {count} unique positive frequencies, got {unique}"
        )
    return np.asarray(unique[:count])


def run_hybrid_case(cid: str, workspace: dict, service: AnalysisService) -> dict:
    cfg = HYBRID_CASES[cid]
    checks = []

    if cfg["kind"] == "beam_modal":
        ne = int(cfg["elements"][0])
        execution = service.execute(
            _beam_model(ne, cfg["bc"]),
            AnalysisCase("modal", {"speed_rad_s": 0.0}, name=f"G14-{cid}"),
        )
        actual = _positive_unique_omega(execution.result.eigenvalues, 1)
        expected = np.asarray(
            [math.sqrt(float(np.min(np.asarray(workspace["omega"], float))))]
        )
        checks.append(compare_frequencies(expected, actual))

    elif cfg["kind"] == "beam_convergence":
        mesh_sizes = np.asarray(workspace[cfg["elements_var"]], int).reshape(-1)
        error_percent = np.asarray(workspace[cfg["error_var"]], float)
        exact = np.asarray(workspace[cfg["exact_var"]], float).reshape(3, 1)
        expected_all = exact * (1.0 + error_percent / 100.0)
        actual_columns = []
        for ne in mesh_sizes:
            execution = service.execute(
                _beam_model(int(ne), "pinned-pinned"),
                AnalysisCase("modal", {"speed_rad_s": 0.0}, name=f"G14-{cid}-{int(ne)}"),
            )
            actual_columns.append(
                _positive_unique_omega(execution.result.eigenvalues, 3)
            )
        checks.append(
            compare_frequencies(expected_all, np.column_stack(actual_columns))
        )

    elif cfg["kind"] == "short_bearing":
        force = float(workspace["F"])
        diameter = float(workspace["D"])
        length = float(workspace["L"])
        clearance = float(workspace["c"])
        viscosity = float(workspace["eta"])
        speed = float(np.asarray(workspace[cfg["speed_var"]]).reshape(-1)[-1])
        model = RotorModel(
            [Node(1, 0.0)],
            [],
            [],
            [Bearing(7, 1, (force, diameter, length, clearance, viscosity))],
        )
        execution = service.execute(
            model,
            AnalysisCase("bearing_matrices", {"speed_rad_s": speed}, name=f"G14-{cid}"),
        )
        mb, cb, kb, mask, eccentricity = execution.result
        checks.append(
            compare_matrix(np.asarray(workspace[cfg["k_var"]]), np.asarray(kb)[:2, :2])
        )
        checks.append(
            compare_matrix(np.asarray(workspace[cfg["c_var"]]), np.asarray(cb)[:2, :2])
        )
        checks.append(
            scalar_vector(
                np.asarray([float(workspace[cfg["ecc_var"]])]),
                np.asarray([float(np.asarray(eccentricity).reshape(-1)[0])]),
                MATRIX_REL,
            )
        )
    else:
        raise AssertionError(cfg)

    return {
        "status": "PASS" if all(check["pass"] for check in checks) else "FAIL",
        "product_path": "AnalysisService -> SolverFacade -> ctypes -> Fortran",
        "kind": cfg["kind"],
        "comparators": checks,
    }


def problem_03_12_source_oracle() -> dict:
    # Validation-only translation of the closed-form equations in
    # Problem_03_12.m. It does not use RotorModel or any alternative rotor
    # solver. The fixed values below were independently evaluated from those
    # source equations at high precision and are not claimed as Octave output.
    rho = 7800.0
    young = 200e9
    a = 1.1
    b = 0.4
    do_ = 0.060
    di = 0.040
    bearing_k = 10e6
    inertia = math.pi * (do_**4 - di**4) / 64.0
    ei = young * inertia
    dt = a**3 * (3.0 * ei + b**3 * bearing_k)
    kt = (3.0 * ei / dt) * (3.0 * ei + (a**3 + b**3) * bearing_k)
    kc = (3.0 * ei / dt) * (
        -3.0 * ei * a + a * b * (a * a - b * b) * bearing_k
    )
    kr = (3.0 * ei / dt) * (
        3.0 * ei * a * a + a * a * b * b * (a + b) * bearing_k
    )
    reduced_k = kt - kc * kc / kr

    frequencies = []
    reduced = []
    for diameter, thickness in ((0.650, 0.065), (1.200, 0.120)):
        mass = rho * thickness * math.pi * (diameter * diameter - do_ * do_) / 4.0
        polar = mass * (diameter * diameter + do_ * do_) / 8.0
        diametral = polar / 2.0 + mass * thickness * thickness / 12.0
        qa = mass * diametral
        qb = -(kt * diametral + kr * mass)
        qc = kt * kr - kc * kc
        discriminant = qb * qb - 4.0 * qa * qc
        lam = [
            (-qb - math.sqrt(discriminant)) / (2.0 * qa),
            (-qb + math.sqrt(discriminant)) / (2.0 * qa),
        ]
        frequencies.append([math.sqrt(value) / (2.0 * math.pi) for value in lam])
        reduced_mass = mass + diametral * kc * kc / (kr * kr)
        reduced.append(math.sqrt(reduced_k / reduced_mass) / (2.0 * math.pi))

    actual = np.asarray(frequencies, float).T
    expected = np.asarray(
        [
            [17.450452831716323, 6.497123590767111],
            [68.58334279133886, 15.808352495544077],
        ]
    )
    reduced_actual = np.asarray(reduced, float)
    reduced_expected = np.asarray([17.47849673947623, 6.607422350448485])
    c1 = compare_frequencies(expected, actual)
    c2 = compare_frequencies(reduced_expected, reduced_actual)
    return {
        "status": "PASS" if c1["pass"] and c2["pass"] else "FAIL",
        "mechanism": "source-derived B_ANALYTICAL closed-form oracle; original Octave probe NOT_APPLICABLE",
        "comparators": [c1, c2],
        "frequencies_hz": actual.tolist(),
        "reduced_hz": reduced_actual.tolist(),
    }


def load_runtime_csv(path: Path) -> dict[str, dict]:
    with path.open(newline="") as f:
        return {
            row["problem"].replace("Problem_", "").replace(".m", ""): row
            for row in csv.DictReader(f)
        }


def audit_no_solver_duplication(root: Path) -> dict:
    offenders = []
    forbidden = (
        "np.linalg.eig",
        "numpy.linalg.eig",
        "scipy.linalg.eig",
        "np.linalg.solve",
        "scipy.linalg.solve",
    )
    path = root / "validation" / "book_problems" / "cases"
    if path.exists():
        for file in sorted(path.rglob("*.py")):
            text = file.read_text(errors="replace")
            for token in forbidden:
                if token in text:
                    offenders.append(f"{file.relative_to(root)}:{token}")
    return {
        "pass": not offenders,
        "offenders": offenders,
        "rule": "A_SOLVER/A_WITH_ANALYTIC_ORACLE adapters contain no Python eigensolver/linear-system substitute; production physics is reached through AnalysisService and Fortran. B analytical calculations remain validation-only.",
    }


def write_reports(out: dict, report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "G14_BOOK_PROBLEM_REGRESSION.json").write_text(
        json.dumps(out, indent=2, sort_keys=True)
    )

    fields = [
        "id",
        "chapter",
        "classification",
        "status",
        "octave_run1",
        "octave_run2",
        "probe_mechanism",
        "numeric_count",
        "product_status",
        "detail",
    ]
    with (report_dir / "G14_BOOK_PROBLEM_REGRESSION.csv").open(
        "w", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            [{key: row.get(key, "") for key in fields} for row in out["cases"]]
        )

    md = [
        "# G14 — Book problem regression",
        "",
        f"Overall: **{out['status']}**",
        "",
        f"- 83/83 inventoried: **{out['inventory']['problem_count']}/83**",
        f"- Semantic classes: `{out['inventory']['classification_counts']}`",
        f"- GNU Octave 7.1.0 run 1: **{out['summary']['octave_run1_pass']} PASS / {out['summary']['octave_run1_na']} N/A / {out['summary']['octave_run1_fail']} FAIL**",
        f"- GNU Octave 7.1.0 run 2: **{out['summary']['octave_run2_pass']} PASS / {out['summary']['octave_run2_na']} N/A / {out['summary']['octave_run2_fail']} FAIL**",
        f"- Deterministic numeric regressions: **{out['summary']['deterministic_pass']}/83 PASS**",
        f"- Product comparisons: **{out['summary']['product_pass']}/{out['summary']['product_required']} PASS**",
        f"- Unexpected BLOCKED: **{out['summary']['blocked']}**",
        f"- Solver duplication audit: **{'PASS' if out['solver_duplication_audit']['pass'] else 'FAIL'}**",
        "",
        "Reference executions are explicitly **GNU Octave 7.1.0 probes**, not MATLAB executions. Problem 03_12 is the sole planned Octave N/A because `do` is a reserved Octave keyword; its B-only regression is source-derived and makes no Octave-baseline claim.",
        "",
        "## Per-case status",
        "",
        "| ID | Class | Status | Octave | Numeric probe | Product |",
        "|---|---|---|---|---|---|",
    ]
    for row in out["cases"]:
        octave = f"{row.get('octave_run1','?')}/{row.get('octave_run2','?')}"
        md.append(
            f"| {row['id']} | {row['classification']} | {row['status']} | {octave} | {row.get('probe_mechanism','')} | {row.get('product_status','NOT_APPLICABLE')} |"
        )
    (report_dir / "G14_BOOK_PROBLEM_REGRESSION.md").write_text(
        "\n".join(md) + "\n"
    )
    (report_dir / "G14_ENVIRONMENT.json").write_text(
        json.dumps(out["environment"], indent=2, sort_keys=True)
    )

    commands = """# Commands executed for G14

```bash
python validation/book_problems/materialize_archive.py --target reference/drm_problem_scripts --write-zip validation/reports/DRM_problem_scripts.authority.zip
python validation/book_problems/inventory.py --problem-dir reference/drm_problem_scripts --output validation/reports/problem_inventory.json --csv-output validation/reports/problem_inventory.csv --md-output validation/reports/BOOK_PROBLEM_INVENTORY.md
python validation/equivalence/verify_authority_sources.py
cmake -S fortran -B build-g14 -DCMAKE_BUILD_TYPE=Release
cmake --build build-g14 -j2
ctest --test-dir build-g14 --output-on-failure
docker run --rm -v "$GITHUB_WORKSPACE:/work" -w /work gnuoctave/octave:7.1.0 octave --no-gui --quiet --eval "addpath('/work/validation/book_problems/octave'); run_problem_suite('/work','/work/validation/reports/book_problems/octave_run1',1);"
docker run --rm -v "$GITHUB_WORKSPACE:/work" -w /work gnuoctave/octave:7.1.0 octave --no-gui --quiet --eval "addpath('/work/validation/book_problems/octave'); run_problem_suite('/work','/work/validation/reports/book_problems/octave_run2',0);"
python validation/book_problems/run_regression.py
```
"""
    (report_dir / "COMMANDS_EXECUTED_G14.md").write_text(commands)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem-dir", default="reference/drm_problem_scripts")
    parser.add_argument(
        "--run1", default="validation/reports/book_problems/octave_run1"
    )
    parser.add_argument(
        "--run2", default="validation/reports/book_problems/octave_run2"
    )
    parser.add_argument("--report-dir", default="validation/reports")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    inventory = verify_inventory(args.problem_dir)
    run1 = Path(args.run1)
    run2 = Path(args.run2)
    runtime1 = load_runtime_csv(run1 / "octave_runtime.csv")
    runtime2 = load_runtime_csv(run2 / "octave_runtime.csv")
    service = AnalysisService(
        build_options={
            "qualification_gate": "G14",
            "authority_engine": "GNU Octave 7.1.0",
        }
    )

    cases = []
    product_required = 0
    product_pass = 0
    deterministic_pass = 0
    blocked = 0

    for item in inventory["rows"]:
        cid = item["id"]
        print(f"G14_CASE_BEGIN {cid} class={item['classification']}", flush=True)
        r1 = runtime1.get(cid)
        r2 = runtime2.get(cid)
        row = {
            "id": cid,
            "chapter": item["chapter"],
            "classification": item["classification"],
            "octave_run1": r1["status"] if r1 else "MISSING",
            "octave_run2": r2["status"] if r2 else "MISSING",
        }

        if cid in KNOWN_OCTAVE_NA:
            if (
                not r1
                or not r2
                or r1["status"] != "NOT_APPLICABLE"
                or r2["status"] != "NOT_APPLICABLE"
            ):
                row.update(
                    status="FAIL",
                    detail="Problem_03_12 must be the explicit Octave 7.1.0 N/A; observed different runtime status",
                    product_status="NOT_APPLICABLE",
                )
                cases.append(row)
                continue
            deterministic = problem_03_12_source_oracle()
            row["determinism"] = deterministic
            row["probe_mechanism"] = deterministic["mechanism"]
            if deterministic["status"] != "PASS":
                row.update(
                    status="FAIL",
                    detail="source-derived analytical oracle failed",
                    product_status="NOT_APPLICABLE",
                )
                cases.append(row)
                continue
            deterministic_pass += 1
            row.update(
                status="PASS",
                detail=KNOWN_OCTAVE_NA[cid],
                product_status="NOT_APPLICABLE",
            )
            cases.append(row)
            continue

        if (
            not r1
            or not r2
            or r1["status"] != "PASS"
            or r2["status"] != "PASS"
        ):
            row.update(
                status="BLOCKED",
                detail="unexpected Octave authority-probe failure",
                product_status="NOT_EXECUTED",
            )
            blocked += 1
            cases.append(row)
            continue

        print(f"G14_DETERMINISM_BEGIN {cid}", flush=True)
        deterministic = check_reference_determinism(cid, run1, run2)
        print(f"G14_DETERMINISM_END {cid} status={deterministic.get('status')}", flush=True)
        row["determinism"] = deterministic
        row["probe_mechanism"] = deterministic.get("mechanism", "")
        row["numeric_count"] = deterministic.get(
            "numeric_count", deterministic.get("numeric_variable_count", 0)
        )
        if deterministic["status"] != "PASS":
            row.update(
                status="FAIL",
                detail=deterministic.get("reason", "numeric repeatability failure"),
                product_status="NOT_EXECUTED",
            )
            cases.append(row)
            continue

        deterministic_pass += 1
        product = None
        if item["classification"] == "A_SOLVER":
            product_required += 1
            print(f"G14_PRODUCT_BEGIN {cid} class=A_SOLVER", flush=True)
            workspace = loadmat(
                run1 / "workspaces" / f"Problem_{cid}.mat", simplify_cells=True
            )
            product = run_solver_case(cid, workspace, service)
            print(f"G14_PRODUCT_END {cid} status={product.get('status')}", flush=True)
        elif item["classification"] == "A_WITH_ANALYTIC_ORACLE":
            product_required += 1
            print(f"G14_PRODUCT_BEGIN {cid} class=A_WITH_ANALYTIC_ORACLE", flush=True)
            workspace = loadmat(
                run1 / "workspaces" / f"Problem_{cid}.mat", simplify_cells=True
            )
            product = run_hybrid_case(cid, workspace, service)
            print(f"G14_PRODUCT_END {cid} status={product.get('status')}", flush=True)

        if product is not None:
            row["product"] = product
            row["product_status"] = product["status"]
            if product["status"] == "PASS":
                product_pass += 1
            else:
                row.update(
                    status="FAIL", detail="production Fortran comparison failed"
                )
                cases.append(row)
                continue
        else:
            row["product_status"] = "NOT_APPLICABLE"

        row.update(
            status="PASS",
            detail="deterministic GNU Octave 7.1.0 numeric probe"
            + (
                " plus production Fortran comparison"
                if product is not None
                else "; validation-only analytical case"
            ),
        )
        cases.append(row)

    audit = audit_no_solver_duplication(root)

    def count_status(runtime, status):
        return sum(value["status"] == status for value in runtime.values())

    summary = {
        "octave_run1_pass": count_status(runtime1, "PASS"),
        "octave_run1_na": count_status(runtime1, "NOT_APPLICABLE"),
        "octave_run1_fail": count_status(runtime1, "FAIL"),
        "octave_run2_pass": count_status(runtime2, "PASS"),
        "octave_run2_na": count_status(runtime2, "NOT_APPLICABLE"),
        "octave_run2_fail": count_status(runtime2, "FAIL"),
        "deterministic_pass": deterministic_pass,
        "product_required": product_required,
        "product_pass": product_pass,
        "blocked": blocked,
        "fail": sum(row["status"] == "FAIL" for row in cases),
        "pass": sum(row["status"] == "PASS" for row in cases),
    }

    status = (
        "PASS"
        if (
            summary["pass"] == 83
            and summary["blocked"] == 0
            and summary["fail"] == 0
            and summary["octave_run1_pass"] == 82
            and summary["octave_run1_na"] == 1
            and summary["octave_run1_fail"] == 0
            and summary["octave_run2_pass"] == 82
            and summary["octave_run2_na"] == 1
            and summary["octave_run2_fail"] == 0
            and product_required == 20
            and product_pass == 20
            and audit["pass"]
        )
        else "FAIL"
    )

    out = {
        "schema_version": 3,
        "gate": "G14",
        "status": status,
        "authority": "GNU Octave 7.1.0 probes of exact DRM_problem_scripts; frozen Rotor_Software_v2 only where original problems call it",
        "not_matlab_claim": True,
        "known_octave_not_applicable": KNOWN_OCTAVE_NA,
        "inventory": {
            "problem_count": inventory["problem_count"],
            "classification_counts": inventory["classification_counts"],
            "source_archive_sha256": inventory["source_archive_sha256"],
            "direct_toolbox_call_cases": inventory["direct_toolbox_call_case_count"],
            "direct_numerical_solver_cases": inventory[
                "direct_numerical_solver_case_count"
            ],
        },
        "frozen_thresholds": {
            "matrix_rel": MATRIX_REL,
            "eig_rel": EIG_REL,
            "freq_rel": FREQ_REL,
            "response_rel": RESPONSE_REL,
            "analytical_repeat_rel": ANALYTICAL_REL,
        },
        "summary": summary,
        "solver_duplication_audit": audit,
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
            "github_sha": os.environ.get("GITHUB_SHA", ""),
            "drmrotor_lib": os.environ.get("DRMROTOR_LIB", ""),
            "octave_run1_summary": (run1 / "octave_summary.txt").read_text(
                errors="replace"
            ),
            "octave_run2_summary": (run2 / "octave_summary.txt").read_text(
                errors="replace"
            ),
        },
        "cases": cases,
    }
    write_reports(out, Path(args.report_dir))
    print(
        json.dumps(
            {
                "gate": "G14",
                "status": status,
                "summary": summary,
                "classification_counts": inventory["classification_counts"],
                "solver_duplication_audit": audit,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
