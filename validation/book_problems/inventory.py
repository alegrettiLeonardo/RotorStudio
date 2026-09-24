from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
from collections import Counter

EXPECTED_ARCHIVE_SHA256 = "8b5db23fa57bc5e41f68ed9e25ab8f1f1a72e4a24b9e11af38dccdd4098501d1"

SOLVER_FUNCTIONS = (
    "bearasym", "bearmtx", "chr_asym", "chr_root", "chr_root_coax", "crit_spd",
    "freq_asym", "freq_aux", "freq_fdn", "freq_rsp", "freq_rsp_coax", "rotorasym",
    "rotormtx", "runup", "shftasym", "shftelem", "taper", "time_fdn",
)
POST_FUNCTIONS = (
    "whirl", "picrotor", "plotcamp", "ploteig", "plotfrf", "plotloci", "plotmode",
    "plotorbit", "plotresp", "fftscale",
)
PLOT_FUNCTIONS = {
    "plot", "plot3", "semilogx", "semilogy", "loglog", "subplot", "figure", "stem",
    "surf", "mesh", "contour", "polar", "pcolor", "quiver", "bar",
}

A_SOLVER = {
    "05_01", "05_02", "05_03", "05_08", "05_09", "05_11",
    "06_10", "06_11", "06_11e", "06_12", "07_10", "07_11", "08_11", "08_12", "08_14",
}
A_WITH_ANALYTIC_ORACLE = {"04_06", "04_07", "04_08", "04_12", "05_04"}
EXPECTED_CLASS_COUNTS = {"A_SOLVER": 15, "A_WITH_ANALYTIC_ORACLE": 5, "B_ANALYTICAL": 63}

SPECIAL_RATIONALE = {
    "04_06": "Pinned-pinned Euler beam FE problem exercises the same bending element mass/stiffness physics used by the shaft solver; the book calculation is an independent FE oracle and the product side goes through AnalysisService to Fortran.",
    "04_07": "Clamped-clamped beam FE problem exercises the same beam element matrices and boundary-condition elimination used by the production shaft model; suitable as an independent FE oracle.",
    "04_08": "Clamped-pinned beam FE problem exercises the same beam element matrices plus mixed boundary constraints; suitable as an independent FE oracle.",
    "04_12": "Pinned-pinned beam mesh-convergence problem exercises repeated assembly of the same Euler beam element and modal solution; suitable as an independent convergence oracle.",
    "05_04": "The script manually evaluates short-width hydrodynamic-bearing eccentricity and K/C coefficients implemented by V2 bearing type 7; compare those coefficients with the Fortran bearing path.",
    "03_12": "Closed-form/low-order rigid-rotor derivation. GNU Octave 7.1.0 cannot parse the original MATLAB identifier `do` because `do` is an Octave keyword, so this B-only case uses a source-derived analytical regression without claiming an Octave baseline.",
}

GROUP_RATIONALE = {
    "02": "General vibration-analysis/Fourier/receptance exercise. It does not instantiate Rotor_Software_v2 rotor elements; keep it as an educational analytical regression outside the production solver.",
    "03": "Closed-form/low-order rigid-rotor derivation. Although physically related to rotordynamics, it is not an exact RotorModel discretization with the production element/mass conventions; use it as a standalone analytical regression rather than forcing a non-equivalent solver comparison.",
    "04": "Finite-element teaching problem outside the exact lateral shaft production contract (typically axial/bar formulation or reduction exercise); keep it as a standalone analytical FE regression.",
    "05": "Book problem does not call the production numerical solver path in a form that can be compared without changing the modeled equations; retain it as an analytical/educational regression.",
    "06": "Closed-form/low-order forced/critical-speed derivation. It is useful numerical evidence but is not an exact production RotorModel case under the V2 mass/element conventions; keep it outside the solver implementation.",
    "07": "Closed-form rotating-frame/asymmetric-rotor derivation. It is related to production physics but not an exact V2 FE model/ABI case; retain it as a standalone analytical regression to avoid an artificial second solver path.",
    "08": "Balancing/influence-coefficient calculation independent of the RotorStudio numerical solver. Keep any Python calculation in validation only; do not create production solver physics.",
    "09": "Axial/torsional/gearbox educational problem outside the Stage-1 lateral Rotor_Software_v2 production solver scope; keep it as validation-only analytical regression.",
}


def _code_without_comments(text: str) -> str:
    return "\n".join(line.split("%", 1)[0] for line in text.splitlines())


def _function_calls(code: str) -> list[str]:
    calls: list[str] = []
    for m in re.finditer(r"(?<![.\w])([A-Za-z]\w*)\s*\(", code):
        name = m.group(1)
        if name not in calls:
            calls.append(name)
    return calls


def _output_kinds(text: str) -> list[str]:
    low = text.lower()
    kinds: list[str] = []

    def add(name: str) -> None:
        if name not in kinds:
            kinds.append(name)

    if "stiffness matrix" in low or re.search(r"\bkb\s*=", low) or re.search(r"\bk\s*=\s*\[", low):
        add("matrix/stiffness")
    if "damping matrix" in low or re.search(r"\bcb\s*=", low):
        add("matrix/damping")
    if "mass matrix" in low or re.search(r"\bm\s*=\s*\[", low):
        add("matrix/mass")
    if "critical speed" in low:
        add("critical_speed")
    if "natural frequ" in low or "nat freq" in low or "omega_n" in low:
        add("natural_frequency")
    if re.search(r"\beig\s*\(", text):
        add("eigenvalues")
    if "mode shape" in low:
        add("mode_shape")
    if "response" in low or "receptance" in low:
        add("response")
    if "whirl" in low or "kappa" in low:
        add("whirl/kappa")
    if "balance" in low or "balancing" in low:
        add("balancing_vector")
    if "fourier" in low or "fft" in low:
        add("fourier/spectrum")
    if "load" in low or "force" in low or "torque" in low:
        add("force/load")
    if not kinds:
        add("deterministic_numeric_workspace")
    return kinds


def _comparator_policy(kinds: list[str], classification: str, cid: str) -> list[str]:
    if cid == "03_12":
        return ["source_derived_freq_rel<=1e-8"]
    if classification == "B_ANALYTICAL":
        return ["deterministic_numeric_probe_rel<=1e-12"]
    out: list[str] = []
    if any(k.startswith("matrix/") for k in kinds):
        out.append("matrix_rel<=1e-12")
    if "eigenvalues" in kinds:
        out.append("eig_rel<=1e-8")
    if "natural_frequency" in kinds:
        out.append("freq_rel<=1e-8")
    if "mode_shape" in kinds:
        out.append("isolated_mode_MAC>=0.999999")
    if "response" in kinds:
        out.append("complex_response_rel<=1e-8")
    if "critical_speed" in kinds:
        out.append("critical_speed_rel<=1e-6")
    if "whirl/kappa" in kinds:
        out.append("kappa_absrel<=1e-10")
    return out or ["deterministic_numeric_probe_rel<=1e-12"]


def _classification(cid: str) -> str:
    if cid in A_SOLVER:
        return "A_SOLVER"
    if cid in A_WITH_ANALYTIC_ORACLE:
        return "A_WITH_ANALYTIC_ORACLE"
    return "B_ANALYTICAL"


def _baseline_mechanism(cid: str, classification: str) -> str:
    if classification == "A_SOLVER":
        return "GNU Octave 7.1.0 probe executes the exact original problem with the frozen Rotor_Software_v2 on path; selected V2 numerical outputs are then compared with AnalysisService -> SolverFacade -> ctypes -> Fortran. This is an Octave probe, not a MATLAB claim."
    if classification == "A_WITH_ANALYTIC_ORACLE":
        return "GNU Octave 7.1.0 probe executes the original standalone/book equations and freezes the exact corresponding numeric oracle before comparison with the production Fortran component/model path. This is an Octave probe, not a MATLAB claim."
    if cid == "03_12":
        return "GNU Octave 7.1.0 probe is NOT_APPLICABLE because the original MATLAB variable name `do` is an Octave keyword. A validation-only source-derived analytical runner evaluates the published equations and compares them with frozen source-derived frequency constants; no product-equivalence claim is made."
    return "Two independent GNU Octave 7.1.0 probes execute the exact original analytical/educational script; at least one numeric response/workspace output is compared run-to-run with the strictest already-frozen relative threshold. This is an Octave repeatability regression, not a MATLAB or product-equivalence claim."


def build_inventory(problem_dir: str | Path) -> dict:
    root = Path(problem_dir)
    files = sorted(root.glob("Problem_*.m"))
    if len(files) != 83:
        raise RuntimeError(f"expected 83 Problem_*.m files, found {len(files)}")
    rows = []
    for p in files:
        cid = p.stem.replace("Problem_", "")
        chapter = cid.split("_", 1)[0]
        raw = p.read_bytes()
        text = raw.decode(errors="replace")
        code = _code_without_comments(text)
        calls = _function_calls(code)
        solver_calls = sorted(c for c in calls if c in SOLVER_FUNCTIONS)
        post_calls = sorted(c for c in calls if c in POST_FUNCTIONS)
        toolbox_calls = sorted(set(solver_calls + post_calls))
        uses_bnpr = "bnpr" in calls
        plots = sorted(
            set(c for c in calls if c.lower() in PLOT_FUNCTIONS)
            | set(c for c in post_calls if c.startswith("plot") or c == "picrotor")
        )
        inter = sorted(set(c for c in calls if c.lower() in {"input", "menu", "keyboard", "pause"}))
        kinds = _output_kinds(text)
        cls = _classification(cid)
        reason = SPECIAL_RATIONALE.get(cid)
        if reason is None and cls == "A_SOLVER":
            reason = "Calls Rotor_Software_v2 numerical analysis routines directly; regression must reproduce the same final model/case through AnalysisService -> SolverFacade -> ctypes -> Fortran and compare against a GNU Octave 7.1.0 authority probe."
        if reason is None:
            reason = GROUP_RATIONALE[chapter]
        rows.append(
            {
                "id": cid,
                "chapter": int(chapter),
                "original_file": p.name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "dependencies": toolbox_calls + (["bnpr.m"] if uses_bnpr else []),
                "toolbox_calls": toolbox_calls,
                "solver_calls": solver_calls,
                "post_calls": post_calls,
                "uses_bnpr": uses_bnpr,
                "inputs_interactivity": ("interactive:" + ",".join(inter)) if inter else "hard-coded deterministic script inputs; no interactive input()/menu()",
                "comparable_outputs": kinds,
                "plots": plots,
                "classification": cls,
                "justification": reason,
                "baseline_mechanism": _baseline_mechanism(cid, cls),
                "comparator_policy": _comparator_policy(kinds, cls, cid),
                "status": "NOT_EXECUTED",
            }
        )
    counts = dict(Counter(r["classification"] for r in rows))
    if counts != EXPECTED_CLASS_COUNTS:
        raise RuntimeError(f"semantic class counts changed unexpectedly: {counts}")
    direct_toolbox = sum(bool(r["toolbox_calls"]) for r in rows)
    direct_solver = sum(bool(r["solver_calls"]) for r in rows)
    if direct_toolbox != 17 or direct_solver != 15:
        raise RuntimeError(
            f"unexpected direct-call scan after comment stripping: toolbox={direct_toolbox}, numerical_solver={direct_solver}"
        )
    return {
        "schema_version": 2,
        "source_archive": "DRM_problem_scripts.zip",
        "source_archive_sha256": EXPECTED_ARCHIVE_SHA256,
        "problem_count": 83,
        "helper_files": ["bnpr.m"],
        "classification_counts": EXPECTED_CLASS_COUNTS,
        "direct_toolbox_call_case_count": direct_toolbox,
        "direct_numerical_solver_case_count": direct_solver,
        "semantic_review": "manual source review of all 83 scripts; direct-call scan is evidence only, not the classifier",
        "rows": rows,
    }


def verify_inventory(problem_dir: str | Path) -> dict:
    return build_inventory(problem_dir)


def write_csv(data: dict, path: str | Path) -> None:
    cols = [
        "id",
        "chapter",
        "original_file",
        "sha256",
        "dependencies",
        "toolbox_calls",
        "solver_calls",
        "post_calls",
        "uses_bnpr",
        "inputs_interactivity",
        "comparable_outputs",
        "plots",
        "classification",
        "justification",
        "baseline_mechanism",
        "comparator_policy",
        "status",
    ]
    with Path(path).open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in data["rows"]:
            r = {k: row.get(k, "") for k in cols}
            for k in (
                "dependencies",
                "toolbox_calls",
                "solver_calls",
                "post_calls",
                "comparable_outputs",
                "plots",
                "comparator_policy",
            ):
                if isinstance(r[k], list):
                    r[k] = ";".join(map(str, r[k]))
            w.writerow(r)


def write_markdown(data: dict, path: str | Path) -> None:
    md = [
        "# G14 — Book problem inventory and semantic A/B classification",
        "",
        f"Source: `DRM_problem_scripts.zip` SHA256 `{data['source_archive_sha256']}`.",
        f"Inventory: **{data['problem_count']}/83** problems plus helper `bnpr.m`.",
        "",
        "## Classification semantics",
        "",
        "- `A_SOLVER`: original problem calls a V2 numerical solver/matrix path; product regression must pass through AnalysisService -> SolverFacade -> ctypes -> Fortran.",
        "- `A_WITH_ANALYTIC_ORACLE`: book equations form an exact independent oracle for a production component/model; production side still uses the Fortran path.",
        "- `B_ANALYTICAL`: analytical/educational validation outside the production solver. No second RotorStudio solver is introduced.",
        "",
        f"Counts: `{data['classification_counts']}`. Exact executable-code scan finds **{data['direct_toolbox_call_case_count']}** scripts with V2 calls and **{data['direct_numerical_solver_case_count']}** with numerical-solver calls. `Problem_07_02.m` mentions `whirl()` only in a comment and is not counted.",
        "",
        "## 83-case baseline/comparator map",
        "",
        "| ID | Class | V2 calls | Numeric outputs | Baseline | Comparator |",
        "|---|---|---|---|---|---|",
    ]
    for r in data["rows"]:
        calls = ", ".join(r["toolbox_calls"]) or "—"
        kinds = ", ".join(r["comparable_outputs"])
        if r["classification"] == "A_SOLVER":
            base = "Octave 7.1 + V2 -> Fortran"
        elif r["classification"] == "A_WITH_ANALYTIC_ORACLE":
            base = "Octave 7.1 book oracle -> Fortran"
        elif r["id"] == "03_12":
            base = "source-derived B oracle; Octave N/A"
        else:
            base = "two pinned Octave 7.1 probes"
        md.append(
            f"| {r['id']} | {r['classification']} | {calls} | {kinds} | {base} | {', '.join(r['comparator_policy'])} |"
        )
    md += [
        "",
        "## Inventory checkpoint",
        "",
        "- 83/83 inventoried: **PASS**",
        "- 83/83 semantically classified: **PASS**",
        "- regression execution at this file-generation stage: **NOT_EXECUTED**",
        "- G14 overall is not promoted by inventory alone.",
    ]
    Path(path).write_text("\n".join(md) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem-dir", default="reference/drm_problem_scripts")
    ap.add_argument("--output", default="validation/reports/problem_inventory.json")
    ap.add_argument("--csv-output", default="validation/reports/problem_inventory.csv")
    ap.add_argument("--md-output", default="validation/reports/BOOK_PROBLEM_INVENTORY.md")
    a = ap.parse_args()
    inv = build_inventory(a.problem_dir)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(inv, indent=2, sort_keys=True))
    write_csv(inv, a.csv_output)
    write_markdown(inv, a.md_output)
    print(
        json.dumps(
            {
                "case_count": inv["problem_count"],
                "classification_counts": inv["classification_counts"],
                "direct_toolbox": inv["direct_toolbox_call_case_count"],
                "direct_solver": inv["direct_numerical_solver_case_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
