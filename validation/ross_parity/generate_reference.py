#!/usr/bin/env python3
"""Run ONLY frozen ROSS. Does not load RotorStudio or implement a production solver."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import platform
from pathlib import Path
import sys

from infrastructure import PIN, verify_checkout, verify_import, write_new_json


def serialize(value):
    if hasattr(value, "tolist"):
        return serialize(value.tolist())
    if isinstance(value, dict):
        return {str(k): serialize(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [serialize(v) for v in value]
    return value


def static_record(rotor, description):
    result = rotor.run_static()
    return serialize({
        "description": description,
        "authority_method": "ross.rotor_assembly.Rotor.run_static",
        "units": {"deformation": "m", "Vx": "N", "Bm": "N*m", "w_shaft": "N",
                  "disk_forces": "N", "bearing_forces": "N", "nodes_pos": "m", "Vx_axis": "m"},
        "inputs": {
            "shaft": [{k: getattr(s, k) for k in
                       ("n", "L", "idl", "odl", "idr", "odr", "shear_effects", "shear_method_calc", "rotary_inertia", "gyroscopic", "axial_force", "torque", "alpha", "beta")}
                      | {"material": {k: getattr(s.material, k) for k in ("rho", "E", "G_s", "Poisson")}}
                      for s in rotor.shaft_elements],
            "disks": [{k: getattr(d, k) for k in ("n", "m", "Id", "Ip")} for d in rotor.disk_elements],
            "bearings": [{"class": type(b).__name__, "n": b.n, "n_link": b.n_link,
                          "kxx": b.kxx, "kyy": b.kyy, "cxx": b.cxx, "cyy": b.cyy}
                         for b in rotor.bearing_elements],
        },
        "outputs": {k: getattr(result, k) for k in
                    ("deformation", "Vx", "Bm", "w_shaft", "disk_forces", "bearing_forces", "nodes", "nodes_pos", "Vx_axis")},
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ross-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="New directory; existing output is never overwritten")
    args = parser.parse_args()
    root = args.ross_root.resolve()
    authority = verify_checkout(root)
    if args.out.exists():
        raise FileExistsError(f"Output already exists: {args.out}; golden replacement is prohibited")
    sys.path.insert(0, str(root))
    import ross as rs
    import numpy as np
    import scipy
    verify_import(root, rs)
    for method in PIN["phase1_methods"]:
        if not callable(getattr(rs.Rotor, method, None)):
            raise RuntimeError(f"Frozen ROSS is missing required method {method}")

    base = rs.rotor_example()
    soft = rs.Rotor(base.shaft_elements, base.disk_elements,
                    [rs.BearingElement(n=b.n, kxx=1e4, kyy=3e4, cxx=0) for b in base.bearing_elements])
    sealed = rs.Rotor(base.shaft_elements, base.disk_elements,
                      list(base.bearing_elements) + [rs.SealElement(n=3, kxx=1e8, cxx=1e3)])
    asym = rs.Rotor(base.shaft_elements,
                    [rs.DiskElement(n=2, m=13.7, Id=0.21, Ip=0.42)], base.bearing_elements)
    records = {
        "static_rotor_example.json": static_record(base, "Frozen ROSS rotor_example"),
        "static_soft_supports.json": static_record(soft, "Dynamic K changed; static penalty supports unchanged"),
        "static_seal_exclusion.json": static_record(sealed, "Additional seal must not carry static weight"),
        "static_asymmetric_disk.json": static_record(asym, "Asymmetric disk location and sentinel mass"),
    }
    # These are independent properties of ROSS references, NOT Fortran parity.
    from infrastructure import compare
    for name in ("static_soft_supports.json", "static_seal_exclusion.json"):
        compare(records["static_rotor_example.json"]["outputs"], records[name]["outputs"], rtol=0, atol=0)
    # Recheck tracked source after executing the authority.
    if authority != verify_checkout(root):
        raise RuntimeError("ROSS authority changed during reference generation")
    args.out.mkdir(parents=True, exist_ok=False)
    authority.update({
        "schema_version": 1, "producer": "ROSS_ONLY", "rotorstudio_parity_status": "BLOCKED",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
        "ross_version": rs.__version__, "platform": platform.platform(),
        "packages": sorted({(d.metadata["Name"] or "unknown") + "==" + d.version
                            for d in importlib.metadata.distributions()}),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "cases": {name: write_new_json(args.out / name, record) for name, record in records.items()},
    })
    write_new_json(args.out / "authority.json", authority)
    print(f"Generated {len(records)} ROSS-only static references; RotorStudio parity remains BLOCKED")


if __name__ == "__main__":
    main()
