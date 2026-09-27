from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys

import numpy as np

from drm_core import (
    Bearing,
    BearingMapCache,
    Force,
    Node,
    RotorModel,
    ShaftElement,
    load_irdin_project,
    run_modal,
    run_runup,
)
from drm_core.analysis.modal import MATCHED_WHIRL
from drm_core.solver.bearings_backend import AdvancedBearingBackend


QUALIFIED_B12_HEAD = "4df7801d7c6d16cabd092ad6e2e802a6626873c8"
QUALIFIED_B13_HEAD = "fe0d6c4b906c31a63bb569adfc07b12ddbdfde24"
QUALIFIED_B14_B18_HEAD = "ebf2c2f938a9a5e3a797f9a1904a6c581b4ed111"
ROSS_AUTHORITY_SHA = "6320eab9f890f1b3cc1710d508b446fe063ca68d"


def _fixture_path() -> Path:
    roots = [
        Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "_MEIPASS", None) else None,
        Path(__file__).resolve().parents[3],
    ]
    candidates = []
    for root in roots:
        if root is None:
            continue
        candidates.extend(
            [
                root / "examples" / "EST-12735185-CRYOSTAR_V2.txt",
                root / "examples" / "legacy" / "EST-12735185-CRYOSTAR_V2.txt",
            ]
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError(
        "B13-B18 integrated qualification fixture is missing; checked: "
        + ", ".join(str(path) for path in candidates)
    )


def _qualification_rotor(mapped_bearing):
    source = replace(mapped_bearing, node=1, tag="B15-B18 integrated mapped bearing")
    return RotorModel(
        nodes=[Node(1, 0.0), Node(2, 1.0)],
        shafts=[
            ShaftElement(
                2, 1, 2, 0.05, 0.0, 7810.0, 211e9, 81.2e9,
                0.0, 0.0, 0.0
            )
        ],
        bearings=[
            Bearing(
                5, 2,
                (1.5e8, 0.0, 0.0, 1.5e8, 1.5e5, 0.0, 0.0, 1.5e5),
            )
        ],
        forces=[Force(1, (1, 1.0e-6, 0.0))],
        advanced_bearings=[source],
    )


def run_b15_b18_integrated_smoke(output_dir) -> dict:
    """Exercise the B15->B16->B17->B18 product chain in one process.

    This is intentionally additive qualification code. It does not mutate the
    engineering model, cache the physical field arrays, or invoke Reynolds/
    THD/TEHD from the B18 ODE. The source iRdin table is imported first, then
    materialized to a synchronous B16 K/C map, consumed by B17 matched-whirl,
    and finally consumed by the native B18 synchronous run-up ABI.
    """

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fixture = _fixture_path()

    # B15: real legacy iRdin source, not a synthetic parser-only string.
    imported_project = load_irdin_project(fixture)
    imported = list(imported_project.model.advanced_bearings)
    if len(imported) != 2:
        raise RuntimeError(f"B15 expected 2 mapped Cryostar bearings, got {len(imported)}")
    readiness = imported_project.metadata["numerical_readiness"]
    blockers = {item["code"] for item in readiness["blockers"]}
    if "IRDIN_BEARING_COEFFICIENT_TABLE_UNMAPPED" in blockers:
        raise RuntimeError(f"B15 bearing table unexpectedly remains blocked: {blockers}")
    if "IRDIN_DISTRIBUTED_MASS_UNMAPPED" not in blockers:
        raise RuntimeError("B15 granular distributed-mass blocker was unexpectedly removed")
    source = replace(imported[0], node=1, tag="Cryostar B15 integrated source")
    if source.provenance.get("sign_transform") != "NONE":
        raise RuntimeError(f"B15 sign convention changed: {source.provenance}")

    # B16: coefficient-map generation + deterministic L1 reuse in an isolated
    # cache root. Use three source-supported speeds and no frequency axis:
    # this is exactly the synchronous map contract consumed by B18.
    source_axis = np.asarray(source.speed_rad_s, dtype=float)
    selected = tuple(
        float(source_axis[index])
        for index in (0, len(source_axis) // 2, len(source_axis) - 1)
    )
    backend = AdvancedBearingBackend()
    cache = BearingMapCache(output_dir / "b16_integrated_cache")
    cold = cache.get_or_generate(
        source, selected, interpolation="linear", backend=backend
    )
    warm = cache.get_or_generate(
        source, selected, interpolation="linear", backend=backend
    )
    if cold.source != "GENERATED" or warm.source != "L1":
        raise RuntimeError(
            f"B16 cache sequence expected GENERATED->L1, got {cold.source}->{warm.source}"
        )
    operating_map = cold.operating_map
    if not operating_map.synchronous:
        raise RuntimeError("B16 integrated map must be synchronous")
    mapped = operating_map.to_coefficient_bearing(tag="B16 integrated synchronous map")
    direct = backend.evaluate(source, selected[1], selected[1])
    cached = backend.evaluate(mapped, selected[1], selected[1])
    np.testing.assert_allclose(cached.K, direct.K, rtol=3e-13, atol=1e-5)
    np.testing.assert_allclose(cached.C, direct.C, rtol=3e-13, atol=1e-6)

    # B17: matched-whirl on the B16 map. Because the map is synchronous 1-D,
    # bearing K/C depend on Omega and are independent of the iterative whirl
    # frequency. The MAC fixed-point must therefore converge without falling
    # back to eigenvalue-index tracking.
    model = _qualification_rotor(mapped)
    modal = run_modal(
        model,
        selected[1],
        with_eigenvectors=True,
        coefficient_policy=MATCHED_WHIRL,
        whirl_rtol=1e-3,
        whirl_max_iter=25,
    )
    diagnostics = list(modal.metadata.get("matched_whirl") or [])
    if not diagnostics or not all(bool(item["converged"]) for item in diagnostics):
        raise RuntimeError(f"B17 matched-whirl did not converge: {diagnostics}")
    if any(float(item["last_mac"]) < 0.0 or float(item["last_mac"]) > 1.0 for item in diagnostics):
        raise RuntimeError(f"B17 invalid MAC diagnostics: {diagnostics}")

    # B18: full-order synchronous map-based run-up. The speed range is a
    # strict subset of the B16 map envelope, so native extrapolation must not
    # occur. Use a short high-acceleration sweep to keep the frozen smoke
    # bounded while still evaluating time-varying K/C inside the native ODE.
    omega0 = selected[0] + 0.10 * (selected[1] - selected[0])
    omega1 = selected[1] - 0.10 * (selected[1] - selected[0])
    tf = 0.002
    alpha = np.asarray([(omega1 - omega0) / (2.0 * tf), omega0, 0.0])
    transient = run_runup(
        model,
        alpha,
        [0.0, tf],
        nr=0,
        rtol=2e-4,
        atol=2e-7,
        h_max=tf / 20.0,
        max_points=20000,
    )
    if transient.metadata.get("advanced_bearing_scope") != (
        "FULL_ORDER|SYNCHRONOUS_COEFFICIENT_POLICY|MAP_BASED|NO_TEHD_IN_ODE"
    ):
        raise RuntimeError(f"B18 scope metadata mismatch: {transient.metadata}")
    if transient.metadata.get("native_abi") != "rd_runup_coeffmap_legacy":
        raise RuntimeError(f"B18 native ABI mismatch: {transient.metadata}")
    if not np.isfinite(transient.response).all():
        raise RuntimeError("B18 integrated run-up produced non-finite response")
    if transient.time_s.size < 2 or abs(float(transient.time_s[-1]) - tf) > 1e-10:
        raise RuntimeError(
            f"B18 run-up did not reach final time: n={transient.time_s.size}, "
            f"tf={transient.time_s[-1] if transient.time_s.size else None}"
        )
    np.testing.assert_allclose(
        [transient.speed_rad_s[0], transient.speed_rad_s[-1]],
        [omega0, omega1],
        rtol=0.0,
        atol=2e-8,
    )

    evidence = {
        "status": "PASS",
        "fixture": fixture.name,
        "qualified_heads": {
            "B12": QUALIFIED_B12_HEAD,
            "B13": QUALIFIED_B13_HEAD,
            "B14_B18": QUALIFIED_B14_B18_HEAD,
        },
        "ross_authority_sha": ROSS_AUTHORITY_SHA,
        "b15": {
            "mapped_inline_bearing_tables": int(readiness["mapped_inline_bearing_tables"]),
            "remaining_blockers": sorted(blockers),
            "sign_transform": source.provenance.get("sign_transform"),
        },
        "b16": {
            "cache_key": cold.cache_key,
            "cold_source": cold.source,
            "warm_source": warm.source,
            "speed_axis_rad_s": list(selected),
            "map_contract": operating_map.qualification.get("map_contract"),
            "synchronous": operating_map.synchronous,
        },
        "b17": {
            "policy": modal.metadata.get("coefficient_policy"),
            "modes": int(len(modal.eigenvalues)),
            "all_converged": all(bool(item["converged"]) for item in diagnostics),
            "min_last_mac": float(min(float(item["last_mac"]) for item in diagnostics)),
        },
        "b18": {
            "scope": transient.metadata["advanced_bearing_scope"],
            "native_abi": transient.metadata["native_abi"],
            "points": int(transient.time_s.size),
            "accepted_steps": int(transient.metadata.get("accepted_steps", 0)),
            "rejected_steps": int(transient.metadata.get("rejected_steps", 0)),
            "speed_range_rad_s": [float(omega0), float(omega1)],
        },
    }
    (output_dir / "B13_B18_INTEGRATED_SMOKE.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return evidence


__all__ = [
    "run_b15_b18_integrated_smoke",
    "QUALIFIED_B12_HEAD",
    "QUALIFIED_B13_HEAD",
    "QUALIFIED_B14_B18_HEAD",
    "ROSS_AUTHORITY_SHA",
]
