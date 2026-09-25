#!/usr/bin/env python3
"""Generate frozen ROSS bearing reference cases for RotorStudio B12 parity.

This script deliberately executes the ROSS fluid-film engine from one exact
Git commit.  The generated files are *test data*, not a runtime dependency of
RotorStudio.  B12 consumes only the checked-in JSON files.

Usage (CI example):
    git clone https://github.com/petrobras/ross.git _ross_ref
    git -C _ross_ref checkout 6320eab9f890f1b3cc1710d508b446fe063ca68d
    python -m pip install -e ./_ross_ref
    python scripts/generate_ross_golden_cases.py --ross-root ./_ross_ref
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROSS_SHA = "6320eab9f890f1b3cc1710d508b446fe063ca68d"
DEFAULT_OUT = Path("tests/reference/ross_6320eab9")


def _git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def _jsonable(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _sha256_json(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _fixture(ross_root: Path, name: str) -> dict:
    p = ross_root / "ross" / "tests" / "data" / "fluid_film" / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _result_record(run_case, ross_root: Path, fixture_name: str, *, overrides=None, omega=None):
    doc = _fixture(ross_root, fixture_name)
    inp = copy.deepcopy(doc["inputs"])
    overrides = {} if overrides is None else dict(overrides)
    inp.update(overrides)

    omega_spin = float(np.atleast_1d(inp["frequency"])[0])
    if omega is not None:
        if omega_spin == 0.0:
            raise ValueError("asynchronous golden case requires nonzero spin")
        inp["excit_ratios"] = float(omega) / omega_spin

    # For the synchronous TiltingPad THD qualification case, capture the
    # unreduced ROSS coefficient blocks entering dynamic_reduction.  The B12
    # reduced cross terms are small differences of much larger direct/coupled
    # terms, so this diagnostic is necessary to distinguish a field-state
    # mismatch from a condensation mismatch.  It is log-only and does not
    # change the frozen golden payload.
    captured_blocks = None
    if fixture_name == "tilt_5pad_full":
        from ross.bearings.fluid_film import coefficients as _coeff

        _orig_dynamic_reduction = _coeff.dynamic_reduction
        captured_blocks = {}

        def _capture_dynamic_reduction(total_pads, stiffness, damping_block, pads, pad_density, excit_rad, ip, k_rotate):
            names = (
                "xx", "yx", "xy", "yy",
                "deltax", "deltay", "xdelta", "ydelta", "deltadelta",
                "xxi", "yxi", "xyi", "yyi",
            )
            captured_blocks["K"] = {name: _jsonable(getattr(stiffness, name)) for name in names}
            captured_blocks["C"] = {name: _jsonable(getattr(damping_block, name)) for name in names}
            captured_blocks["omega"] = float(excit_rad)
            return _orig_dynamic_reduction(
                total_pads, stiffness, damping_block, pads, pad_density, excit_rad, ip, k_rotate
            )

        _coeff.dynamic_reduction = _capture_dynamic_reduction
        try:
            out = run_case(**inp, field_outputs=True)
        finally:
            _coeff.dynamic_reduction = _orig_dynamic_reduction
    else:
        out = run_case(**inp, field_outputs=True)

    if captured_blocks:
        print("B12_ROSS_RAW_BLOCKS", json.dumps(captured_blocks, sort_keys=True))

    fields = out["fields"][0]
    pressure = np.asarray(fields["pressure"], dtype=float)
    temperature = np.asarray(fields["film_temperature"], dtype=float)

    k = np.array(
        [[out["kxx"][0], out["kxy"][0]], [out["kyx"][0], out["kyy"][0]]],
        dtype=float,
    )
    c = np.array(
        [[out["cxx"][0], out["cxy"][0]], [out["cyx"][0], out["cyy"][0]]],
        dtype=float,
    )

    # ROSS reports the thermal outlet by pad.  Preserve the vector and expose
    # a single deterministic bulk outlet scalar for the B12 scalar gate.
    tout_by_pad = np.asarray(out["temp_out_let_bulk"][0], dtype=float)
    # Formal B12 scalar T_max is the ROSS-reported bearing maximum
    # (tpad_max), i.e. the exact quantity returned by the pinned solver.
    # Keep the max of the exported comparison field separately: it is useful
    # diagnostics, but it is not interchangeable with ROSS tpad_max.
    tmax = float(np.atleast_1d(out["tpad_max"])[0])
    temperature_field_max = float(np.max(temperature))
    pmax = float(np.max(pressure))

    dhc = np.asarray(out.get("dhc", [[[0.0]]])[0], dtype=float)
    deform_max = float(np.max(np.abs(dhc))) if dhc.size else 0.0

    record = {
        "authority": {
            "repository": "petrobras/ross",
            "commit": ROSS_SHA,
            "fixture": fixture_name,
        },
        "case": {
            "spin_rad_s": omega_spin,
            "whirl_rad_s": float(
                omega_spin * float(np.atleast_1d(inp["excit_ratios"])[0])
            ),
            "thermal_type": inp.get("thermal_type"),
            "deform_type": inp.get("deform_type"),
            "bearing_type": inp.get("bearing_type"),
            "overrides": overrides,
        },
        "inputs": inp,
        "outputs": {
            "xj_ratio": float(out["xj_cb"][0]),
            "yj_ratio": float(out["yj_cb"][0]),
            "p_max_pa": pmax,
            "t_max_k": tmax,
            "temperature_field_max_k": temperature_field_max,
            "t_out_bulk_k": float(np.mean(tout_by_pad)),
            "t_out_bulk_by_pad_k": tout_by_pad,
            "deformation_max_m": deform_max,
            "K_n_m": k,
            "C_n_s_m": c,
            "tilt_angle_rad": np.asarray(out["tilt_angle"][0], dtype=float),
            "fx_hydro_n": float(out["fx_hydro"][0]),
            "fy_hydro_n": float(out["fy_hydro"][0]),
            "pressure_field_pa": pressure,
            "temperature_field_k": temperature,
            "theta_grid_rad": np.asarray(fields["theta"], dtype=float),
            "axial_grid_m": np.asarray(fields["axial_position"], dtype=float),
            "film_thickness_field_m": np.asarray(fields["film_thickness"], dtype=float),
        },
    }
    record = _jsonable(record)
    record["authority"]["payload_sha256"] = _sha256_json(record["outputs"])
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ross-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    root = args.ross_root.resolve()
    head = _git_head(root)
    if head != ROSS_SHA:
        raise SystemExit(
            f"ROSS authority mismatch: expected {ROSS_SHA}, found {head} at {root}"
        )

    # Force the checked-out source tree to win over any globally installed ROSS.
    sys.path.insert(0, str(root))
    from ross.bearings.fluid_film.driver import run_case

    args.out.mkdir(parents=True, exist_ok=True)

    cases = {
        "plain_journal_isoviscous.json": _result_record(
            run_case, root, "fixed_isoviscous"
        ),
        "plain_journal_tehd.json": _result_record(
            run_case, root, "fixed_deform_pad_thermal"
        ),
        # Isolate the THD contribution for the synchronous tilting-pad case.
        "tilting_pad_synchronous_thd.json": _result_record(
            run_case,
            root,
            "tilt_5pad_full",
            overrides={"deform_type": None, "excit_ratios": 1.0},
        ),
    }

    async_cases = []
    base = _fixture(root, "tilt_5pad_isoviscous")["inputs"]
    omega_spin = float(np.atleast_1d(base["frequency"])[0])
    for ratio in (0.30, 0.60, 1.00, 1.30):
        async_cases.append(
            _result_record(
                run_case,
                root,
                "tilt_5pad_isoviscous",
                omega=ratio * omega_spin,
            )
        )
    async_doc = {
        "authority": {
            "repository": "petrobras/ross",
            "commit": ROSS_SHA,
            "fixture": "tilt_5pad_isoviscous",
        },
        "case": {
            "spin_rad_s": omega_spin,
            "whirl_ratios": [0.30, 0.60, 1.00, 1.30],
        },
        "points": async_cases,
    }
    async_doc = _jsonable(async_doc)
    async_doc["authority"]["payload_sha256"] = _sha256_json(
        {"points": async_doc["points"]}
    )
    cases["tilting_pad_asynchronous.json"] = async_doc

    field_keys = (
        "pressure_field_pa",
        "temperature_field_k",
        "theta_grid_rad",
        "axial_grid_m",
        "film_thickness_field_m",
    )
    manifest = {
        "ross_commit": ROSS_SHA,
        "generator": "scripts/generate_ross_golden_cases.py",
        "format": "JSON metadata/scalars + compressed NPZ full fields",
        "cases": {},
    }
    for json_name, payload in cases.items():
        stem = Path(json_name).stem
        npz_name = f"{stem}.npz"
        summary = copy.deepcopy(payload)

        if "points" in summary:
            arrays = {
                key: np.stack(
                    [np.asarray(point["outputs"].pop(key), dtype=float) for point in summary["points"]]
                )
                for key in field_keys
            }
        else:
            arrays = {
                key: np.asarray(summary["outputs"].pop(key), dtype=float)
                for key in field_keys
            }
        summary["field_file"] = npz_name
        summary["field_shapes"] = {key: list(value.shape) for key, value in arrays.items()}

        npz_path = args.out / npz_name
        np.savez_compressed(npz_path, **arrays)
        json_path = args.out / json_name
        json_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest["cases"][stem] = {
            "json": json_name,
            "json_sha256": hashlib.sha256(json_path.read_bytes()).hexdigest(),
            "npz": npz_name,
            "npz_sha256": hashlib.sha256(npz_path.read_bytes()).hexdigest(),
        }

    (args.out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {len(cases)} frozen cases under {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
