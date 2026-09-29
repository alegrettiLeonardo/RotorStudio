"""Freeze A5 UCS reference data from the exact ROSS authority.

This is validation-only code. Production UCS physics must remain in Fortran.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROSS_SHA = "6320eab9f890f1b3cc1710d508b446fe063ca68d"


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _jsonable(value):
    import numpy as np
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, complex):
        return {"real": float(value.real), "imag": float(value.imag)}
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _write(path: Path, payload) -> None:
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n")


def _build_rotor(rs, np, bearing0, bearing1=None):
    # ROSS assigns/validates element tags at Rotor construction. Clone the
    # authorities and give the two supports distinct stable tags so a repeated
    # bearing definition is still a valid two-support rotor.
    bearing0 = copy.deepcopy(bearing0)
    bearing0.n = 0
    bearing0.tag = "A5 bearing 0"
    material = rs.Material(name="a5", rho=7810.0, E=211e9, G_s=81.2e9)
    lengths = [0.21, 0.27, 0.19]
    diameters = [0.054, 0.061, 0.049]
    shafts = [
        rs.ShaftElement(
            L=L, idl=0.014, odl=d, material=material,
            shear_effects=True, rotary_inertia=True, gyroscopic=True,
        )
        for L, d in zip(lengths, diameters)
    ]
    # Deliberate proportional damping sentinel. run_ucs() must remove it.
    for shaft in shafts:
        shaft.alpha = 2.5e-3
        shaft.beta = 7.5e-6
    disk = rs.DiskElement(n=2, m=19.0, Id=0.083, Ip=0.151)
    if bearing1 is None:
        bearing1 = copy.deepcopy(bearing0)
    else:
        bearing1 = copy.deepcopy(bearing1)
    bearing1.n = 3
    bearing1.tag = "A5 bearing 1"
    rotor = rs.Rotor(shafts, [disk], [bearing0, bearing1])
    return rotor


def _bearing_cases(rs, np):
    speed = np.array([40.0, 120.0, 260.0, 480.0, 820.0])
    frequency = np.array([30.0, 100.0, 230.0, 470.0, 830.0])

    speed_equal = np.array([4.2e6, 7.1e6, 1.18e7, 1.75e7, 2.65e7])
    speed_kxx = np.array([3.9e6, 7.4e6, 1.28e7, 2.02e7, 3.05e7])
    speed_kyy = np.array([6.2e6, 9.6e6, 1.53e7, 2.42e7, 3.62e7])
    freq_kxx = np.array([4.6e6, 7.8e6, 1.33e7, 2.11e7, 3.28e7])
    freq_kyy = np.array([5.9e6, 9.1e6, 1.51e7, 2.39e7, 3.55e7])

    # grid is indexed [speed, frequency]; single-argument lookup follows the
    # frozen ROSS synchronous diagonal semantics.
    grid_x = np.array([
        [3.6e6, 4.2e6, 5.1e6, 6.3e6, 7.8e6],
        [5.1e6, 5.9e6, 7.0e6, 8.5e6, 1.03e7],
        [7.4e6, 8.4e6, 9.8e6, 1.17e7, 1.39e7],
        [1.04e7, 1.17e7, 1.35e7, 1.58e7, 1.86e7],
        [1.47e7, 1.63e7, 1.86e7, 2.15e7, 2.50e7],
    ])
    grid_y = 1.18 * grid_x + 2.0e5

    return {
        "isotropic_constant": rs.BearingElement(n=0, kxx=1.25e7, kyy=1.25e7, cxx=230.0, cyy=230.0),
        "anisotropic_constant": rs.BearingElement(n=0, kxx=1.05e7, kyy=1.85e7, cxx=210.0, cyy=260.0),
        "speed_equal": rs.BearingElement(n=0, kxx=speed_equal, kyy=speed_equal, cxx=0.0, speed=speed),
        "speed_anisotropic": rs.BearingElement(n=0, kxx=speed_kxx, kyy=speed_kyy, cxx=0.0, speed=speed),
        "frequency_axis": rs.BearingElement(n=0, kxx=freq_kxx, kyy=freq_kyy, cxx=0.0, frequency=frequency),
        "map_2d": rs.BearingElement(n=0, kxx=grid_x, kyy=grid_y, cxx=0.0, speed=speed, frequency=frequency),
        "no_intersection": rs.BearingElement(n=0, kxx=1.0e3, kyy=1.0e3, cxx=0.0),
    }


def _temp_rotor(rs, convert_6dof_to_4dof, rotor, stiffness):
    shafts = copy.deepcopy(rotor.shaft_elements)
    for shaft in shafts:
        shaft.alpha = 0
        shaft.beta = 0
    non_seals = [
        b for b in rotor.bearing_elements
        if not isinstance(b, rs.SealElement)
    ]
    bearings, point_masses = rotor._remove_housing_bearings(
        non_seals, rotor.point_mass_elements
    )
    replacement = [
        rs.BearingElement(n=b.n, n_link=b.n_link, kxx=stiffness, kyy=stiffness, cxx=0.0, cyy=0.0)
        for b in bearings
    ]
    temp = rs.Rotor(
        shaft_elements=shafts,
        disk_elements=rotor.disk_elements,
        bearing_elements=replacement,
        point_mass_elements=point_masses,
    )
    return convert_6dof_to_4dof(temp)


def _critical_summary(modal):
    import numpy as np
    lam = np.asarray(modal.evalues)
    return {
        "speed": float(modal.speed),
        "wn": np.asarray(modal.wn).tolist(),
        "wd": np.asarray(modal.wd).tolist(),
        "damping_ratio": np.asarray(modal.damping_ratio).tolist(),
        "log_dec": np.asarray(modal.log_dec).tolist(),
        "evalues_real": lam.real.tolist(),
        "evalues_imag": lam.imag.tolist(),
    }


def _run_case(rs, np, intersection, convert_6dof_to_4dof, name, bearing, *,
              stiffness_range=(6, 10), num=7, num_modes=16,
              bearing_speed_range=None, synchronous=False):
    rotor = _build_rotor(rs, np, bearing)
    kwargs = {
        "stiffness_range": stiffness_range,
        "num": num,
        "num_modes": num_modes,
        "synchronous": synchronous,
    }
    if bearing_speed_range is not None:
        kwargs["bearing_speed_range"] = bearing_speed_range
    result = rotor.run_ucs(**kwargs)

    brange = np.asarray(result.bearing_speed_range, dtype=float)
    kxx = np.asarray(result.bearing.kxx_interpolated(brange), dtype=float)
    kyy = np.asarray(result.bearing.kyy_interpolated(brange), dtype=float)
    coeffs = ["kxx"] if np.array_equal(np.asarray(result.bearing.kxx), np.asarray(result.bearing.kyy)) else ["kxx", "kyy"]

    payload = {
        "case": name,
        "input": {
            "stiffness_range": list(stiffness_range) if stiffness_range is not None else None,
            "num": int(num),
            "num_modes": int(num_modes),
            "bearing_speed_range": list(bearing_speed_range) if bearing_speed_range is not None else None,
            "synchronous": bool(synchronous),
        },
        "stiffness_range_effective": list(result.stiffness_range),
        "stiffness_log": np.asarray(result.stiffness_log, dtype=float),
        "rotor_wn": np.asarray(result.wn, dtype=float),
        "rotor_wn_shape": list(np.asarray(result.wn).shape),
        "bearing_speed_range": brange,
        "bearing_kxx": kxx,
        "bearing_kyy": kyy,
        "coefficients_processed": coeffs,
        "intersection_x": np.asarray(result.intersection_points["x"], dtype=float),
        "intersection_y": np.asarray(result.intersection_points["y"], dtype=float),
        "critical_modal": [_critical_summary(x) for x in result.critical_points_modal],
    }

    # Matrix-first authority at first/middle/last stiffness values. The map
    # rotor is always undamped; synchronous=True changes M through Rouch.
    sentinels = []
    grid = np.asarray(result.stiffness_log, dtype=float)
    for index in sorted(set([0, len(grid) // 2, len(grid) - 1])):
        k = float(grid[index])
        temp = _temp_rotor(rs, convert_6dof_to_4dof, rotor, k)
        M = np.asarray(temp.M(0.0, synchronous=synchronous), dtype=float)
        C = np.asarray(temp.C(0.0), dtype=float)
        G = np.asarray(temp.G(), dtype=float)
        K = np.asarray(temp.K(0.0), dtype=float)
        modal = temp.run_modal(speed=0, num_modes=num_modes, synchronous=synchronous)
        branch = np.asarray(modal.wn[::2], dtype=float)
        target = num_modes // 2 // 2
        branch = branch[:target]
        sentinels.append({
            "index": index,
            "stiffness": k,
            "M": M,
            "C": C,
            "G": G,
            "K": K,
            "max_abs_C": float(np.max(np.abs(C))),
            "modal_branch": branch,
        })
    payload["matrix_sentinels"] = sentinels
    return payload


def generate(ross_root: Path, out: Path) -> None:
    root = ross_root.resolve()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if head != ROSS_SHA:
        raise RuntimeError(f"ROSS authority mismatch: expected {ROSS_SHA}, got {head}")
    if out.exists():
        raise FileExistsError(f"refusing to overwrite immutable A5 authority: {out}")

    sys.path.insert(0, str(root))
    import numpy as np
    import scipy
    import ross as rs
    from ross.utils import convert_6dof_to_4dof, intersection

    if Path(rs.__file__).resolve() != root / "ross" / "__init__.py":
        raise RuntimeError("imported ROSS is not the frozen checkout")

    out.mkdir(parents=True)
    bearings = _bearing_cases(rs, np)
    specs = [
        ("isotropic_constant", bearings["isotropic_constant"], dict(stiffness_range=(6, 10), num=7)),
        ("anisotropic_constant", bearings["anisotropic_constant"], dict(stiffness_range=(6, 10), num=7)),
        ("speed_equal", bearings["speed_equal"], dict(stiffness_range=(6, 10), num=7)),
        ("speed_anisotropic", bearings["speed_anisotropic"], dict(stiffness_range=(6, 10), num=7)),
        ("frequency_axis", bearings["frequency_axis"], dict(stiffness_range=(6, 10), num=7)),
        ("map_2d", bearings["map_2d"], dict(stiffness_range=(6, 10), num=7)),
        ("explicit_bearing_speed_range", bearings["anisotropic_constant"], dict(stiffness_range=(6, 10), num=7, bearing_speed_range=(40.0, 900.0))),
        ("logspace_gate", bearings["isotropic_constant"], dict(stiffness_range=(6, 10), num=5)),
        ("no_intersection", bearings["no_intersection"], dict(stiffness_range=(6, 10), num=7, bearing_speed_range=(50.0, 900.0))),
        ("synchronous_true", bearings["isotropic_constant"], dict(stiffness_range=(6, 10), num=7, synchronous=True)),
    ]
    manifest = {}
    for name, bearing, kwargs in specs:
        payload = _run_case(rs, np, intersection, convert_6dof_to_4dof, name, bearing, **kwargs)
        path = out / f"{name}.json"
        _write(path, payload)
        manifest[path.name] = _digest(path)

    # Freeze the ROSS default when no rated_w exists. RotorStudio A5 initial
    # production scope intentionally requires an explicit exponent range
    # because its domain has no unambiguous rated-speed property.
    default_rotor = _build_rotor(rs, np, bearings["isotropic_constant"])
    default_result = default_rotor.run_ucs(stiffness_range=None, num=5, num_modes=16)
    default_payload = {
        "case": "ross_default_no_rated_speed",
        "stiffness_range_effective": list(default_result.stiffness_range),
        "stiffness_log": np.asarray(default_result.stiffness_log, dtype=float),
        "rotor_wn": np.asarray(default_result.wn, dtype=float),
    }
    path = out / "ross_default_no_rated_speed.json"
    _write(path, default_payload)
    manifest[path.name] = _digest(path)

    # Synthetic intersection authority exercises one/multiple/none/endpoint/
    # near-parallel cases without depending on a particular rotor branch.
    synthetic = {}
    synthetic_specs = {
        "one": ([0, 1, 2], [0, 1, 2], [0, 1, 2], [2, 1, 0]),
        "multiple": ([0, 1, 2, 3, 4], [0, 2, 0, 2, 0], [0, 1, 2, 3, 4], [1, 1, 1, 1, 1]),
        "none": ([0, 1, 2], [0, 0, 0], [0, 1, 2], [2, 2, 2]),
        "endpoint": ([0, 1, 2], [0, 1, 0], [1, 2, 3], [1, 2, 3]),
        "near_parallel": ([0, 1, 2], [0, 1, 2], [0, 1, 2], [1e-10, 1 + 1e-10, 2 + 2e-10]),
    }
    for key, (x1, y1, x2, y2) in synthetic_specs.items():
        x, y = intersection(np.asarray(x1, float), np.asarray(y1, float), np.asarray(x2, float), np.asarray(y2, float))
        synthetic[key] = {"x": np.asarray(x, float), "y": np.asarray(y, float)}
    path = out / "intersection_sentinels.json"
    _write(path, synthetic)
    manifest[path.name] = _digest(path)

    authority_files = [
        "ross/rotor_assembly.py",
        "ross/utils.py",
        "ross/results.py",
        "ross/bearing_seal_element.py",
        "ross/tests/test_rotor_assembly.py",
    ]
    authority = {
        "repository": "petrobras/ross",
        "commit": ROSS_SHA,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scope": "A5 UCS immutable validation authority; production physics is not Python",
        "source_sha256": {name: _digest(root / name) for name in authority_files},
        "golden_sha256": manifest,
    }
    _write(out / "authority.json", authority)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ross-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    generate(args.ross_root, args.out)
