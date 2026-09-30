"""Independent diagnostics on B1 ROSS output, never an authority generator.

Small axial/torsional energy identities and signed/zero patterns are validation
oracles. The source's full lateral element equations are not reimplemented.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from validation.b1.authority_common import (
    REPO_ROOT, LATERAL, AXIAL, TORSION, check_candidate, file_hash, write_json,
)

EPS = float(np.finfo(np.float64).eps)
AUDIT_ROUNDING_BOUND = 1024 * EPS
XPLANE = [0, 4, 6, 10]
YPLANE = [1, 3, 7, 9]


def maxabs(value: Any) -> float:
    return float(np.max(np.abs(value)))


def inspect_candidate(root: Path, report_path: Path | None = None) -> dict[str, Any]:
    authority, cases, arrays = check_candidate(root)
    checks: list[dict[str, Any]] = []
    diagnostics = {}
    by_prefix = {cid.split("_", 1)[0]: cid for cid in cases}

    def matrix(prefix: str, name: str) -> np.ndarray:
        return arrays[f"arrays/{prefix}_{name}.npy"]

    def exact(name: str, condition: bool, **detail: Any) -> None:
        checks.append({"check": name, "status": "PASS" if condition else "FAIL", **detail})

    def close(name: str, received: Any, expected: Any) -> None:
        a, b = np.asarray(received), np.asarray(expected)
        err = maxabs(a - b)
        scale = max(maxabs(a), maxabs(b), np.finfo(float).tiny)
        ratio = err / scale
        exact(name, ratio <= AUDIT_ROUNDING_BOUND, absolute_error=err,
              relative_scale_error=ratio, bound=AUDIT_ROUNDING_BOUND)

    for prefix, cid in sorted(by_prefix.items()):
        case = cases[cid]
        names = ("M", "K", "G", "Kst") if case["kind"] == "shaft" else ("M", "G", "Kdt")
        mats = {name: matrix(prefix, name) for name in names}
        per_matrix = {name: {"shape": list(a.shape), "dtype": str(a.dtype),
                             "min": float(a.min()), "max": float(a.max()),
                             "finite": bool(np.isfinite(a).all()),
                             "nonzero": int(np.count_nonzero(a))} for name, a in mats.items()}
        exact(f"{prefix}:finite", all(d["finite"] for d in per_matrix.values()))
        M, G = mats["M"], mats["G"]
        exact(f"{prefix}:M_symmetric", np.array_equal(M, M.T), max_asymmetry=maxabs(M - M.T))
        exact(f"{prefix}:G_skew", np.array_equal(G, -G.T), max_skew_residual=maxabs(G + G.T))
        exact(f"{prefix}:G_zero_diagonal", bool(np.all(np.diag(G) == 0)))
        if case["kind"] == "shaft":
            p, d, mat = case["resolved_input"], case["derived"], case["material_effective"]
            L, rho, E, Gs = p["L"], mat["rho"], mat["E"], mat["G_s"]
            scale = np.array([L, L, L, 1., 1., 1.] * 2)
            scaled_M = scale[:, None] * M * scale[None, :]
            mass_eigenvalues = np.linalg.eigvalsh(scaled_M)
            exact(f"{prefix}:scaled_M_positive_definite", bool(mass_eigenvalues.min() > 0),
                  minimum_eigenvalue=float(mass_eigenvalues.min()))
            K, Kst = mats["K"], mats["Kst"]
            scaled_K = scale[:, None] * K * scale[None, :]
            if p["torque"] == 0:
                exact(f"{prefix}:torque_free_K_symmetric", np.array_equal(K, K.T), max_asymmetry=maxabs(K - K.T))
            if not p["gyroscopic"]:
                exact(f"{prefix}:gyro_off_G_zero", bool(np.all(G == 0)))
                exact(f"{prefix}:gyro_off_Kst_not_zero", bool(np.any(Kst != 0)))
            m_mask = np.zeros((12, 12), dtype=bool)
            for idx in (XPLANE, YPLANE, AXIAL, TORSION):
                m_mask[np.ix_(idx, idx)] = True
            k_mask = m_mask.copy()
            if p["torque"] != 0:
                k_mask[np.ix_(LATERAL, LATERAL)] = True
            g_mask = np.zeros((12, 12), dtype=bool)
            g_mask[np.ix_(XPLANE, YPLANE)] = True
            g_mask[np.ix_(YPLANE, XPLANE)] = True
            kst_mask = np.zeros((12, 12), dtype=bool)
            kst_mask[np.ix_([0, 4, 6, 10], [1, 3, 7, 9])] = True
            violations = {}
            for name, mask in (("M", m_mask), ("K", k_mask), ("G", g_mask), ("Kst", kst_mask)):
                violations[name] = int(np.count_nonzero(mats[name][~mask]))
                exact(f"{prefix}:{name}_structural_zero_pattern", violations[name] == 0, violations=violations[name])
            # Derive only elementary section/energy checks from the input geometry.
            # The separate generator never calls this code to create matrices.
            Al = np.pi * (p["odl"]**2 - p["idl"]**2) / 4
            Ar = np.pi * (p["odr"]**2 - p["idr"]**2) / 4
            Il = np.pi * (p["odl"]**4 - p["idl"]**4) / 64
            Ir = np.pi * (p["odr"]**4 - p["idr"]**4) / 64
            Ae, Je = (Al + Ar) / 2, Il + Ir
            ones, differential = np.ones(2), np.array([0.0017, -0.0023])
            axial_M = M[np.ix_(AXIAL, AXIAL)]
            torsional_M = M[np.ix_(TORSION, TORSION)]
            axial_K = K[np.ix_(AXIAL, AXIAL)]
            torsional_K = K[np.ix_(TORSION, TORSION)]
            close(f"{prefix}:axial_endpoint_mean_rigid_mass", ones @ axial_M @ ones, rho * Ae * L)
            close(f"{prefix}:torsion_endpoint_mean_rigid_inertia", ones @ torsional_M @ ones, rho * Je * L)
            close(f"{prefix}:axial_strain_energy", 0.5 * differential @ axial_K @ differential,
                  0.5 * E * Ae / L * (differential[1] - differential[0])**2)
            close(f"{prefix}:torsional_strain_energy", 0.5 * differential @ torsional_K @ differential,
                  0.5 * Gs * Je / L * (differential[1] - differential[0])**2)
            for name, sub, stiffness in (("axial", axial_K, E * Ae / L), ("torsion", torsional_K, Gs * Je / L)):
                close(f"{prefix}:{name}_extension_block", sub, stiffness * np.array([[1., -1.], [-1., 1.]]))
            for name, sub, inertia in (("axial", axial_M, rho * Ae * L), ("torsion", torsional_M, rho * Je * L)):
                close(f"{prefix}:{name}_consistent_mass_block", sub, inertia / 6 * np.array([[2., 1.], [1., 2.]]))
            cylindrical = p["idl"] == p["idr"] and p["odl"] == p["odr"]
            if cylindrical:
                close(f"{prefix}:cylinder_mass_equals_constructor_mass", ones @ axial_M @ ones, d["m"])
                for coord in (0, 1, 2):
                    v = np.zeros(12); v[coord] = v[coord + 6] = 1
                    close(f"{prefix}:cylinder_translation_mass_{coord}", v @ M @ v, rho * Al * L)
            scaled_G = scale[:, None] * G * scale[None, :]
            v = np.linspace(-0.73, 0.91, 12)
            quadratic = float(v @ scaled_G @ v)
            energy_scale = max(maxabs(scaled_G) * float(np.sum(np.abs(v)))**2, np.finfo(float).tiny)
            exact(f"{prefix}:G_real_vector_quadratic", abs(quadratic) <= AUDIT_ROUNDING_BOUND * energy_scale,
                  value=quadratic, scaled_residual=abs(quadratic) / energy_scale)
            diagnostics[cid] = {"matrices": per_matrix, "derived_geometry": d,
                "M_max_asymmetry": maxabs(M - M.T), "K_max_asymmetry": maxabs(K - K.T),
                "K_symmetry_applicable": p["torque"] == 0, "G_max_skew_residual": maxabs(G + G.T),
                "zero_pattern_violations": violations,
                "scaled_M_min_eigenvalue": float(mass_eigenvalues.min()),
                "scaled_M_max_eigenvalue": float(mass_eigenvalues.max()),
                "scaled_M_rank": int(np.linalg.matrix_rank(scaled_M)),
                "scaled_K_rank": int(np.linalg.matrix_rank(scaled_K)),
                "scaled_K_min_eigenvalue_if_symmetric": float(np.linalg.eigvalsh(scaled_K).min()) if p["torque"] == 0 else None,
                "Kst_rank": int(np.linalg.matrix_rank(Kst)),
                "coordinate_scaling": "diag(L,L,L,1,1,1,L,L,L,1,1,1); diagnostics only",
                "axial_rigid_mass": float(ones @ axial_M @ ones), "constructor_geometric_mass": d["m"],
                "axial_mass_to_geometric_mass_ratio": float(ones @ axial_M @ ones) / d["m"],
                "axial_torsional_convention": "endpoint means; not exact-frustum integration"}
        else:
            p = case["resolved_input"]
            expected_M = np.diag([p["m"], p["m"], p["m"], p["Id"], p["Id"], p["Ip"]])
            expected_G = np.zeros((6, 6)); expected_G[3, 4] = p["Ip"]; expected_G[4, 3] = -p["Ip"]
            expected_Kdt = np.zeros((6, 6)); expected_Kdt[4, 3] = p["Ip"]
            exact(f"{prefix}:disk_M_diagonal_values", np.array_equal(M, expected_M))
            exact(f"{prefix}:disk_G_pattern_and_sign", np.array_equal(G, expected_G))
            exact(f"{prefix}:disk_Kdt_one_sided_pattern", np.array_equal(mats["Kdt"], expected_Kdt))
            v = np.array([0.31, -0.47, 0.59, 0.71, -0.83, 0.97])
            close(f"{prefix}:disk_kinetic_energy", 0.5 * v @ M @ v,
                  0.5 * (p["m"] * sum(v[:3]**2) + p["Id"] * sum(v[3:5]**2) + p["Ip"] * v[5]**2))
            diagnostics[cid] = {"matrices": per_matrix, "derived": case["derived"],
                                "M_max_asymmetry": maxabs(M - M.T), "G_max_skew_residual": maxabs(G + G.T),
                                "M_min_eigenvalue": float(np.linalg.eigvalsh(M).min()),
                                "M_rank": int(np.linalg.matrix_rank(M)), "zero_pattern_violations": 0}
        print("B1_CASE " + json.dumps({"id": cid, "matrices": per_matrix,
              "M_asymmetry": diagnostics[cid]["M_max_asymmetry"],
              "G_skew_residual": diagnostics[cid]["G_max_skew_residual"]}, sort_keys=True))

    # Otherwise identical S02..S09 exhaust the eight independent flag combinations.
    for i in range(2, 10):
        prefix = f"S{i:02d}"
        d = cases[by_prefix[prefix]]["derived"]
        exact(f"{prefix}:Kst_flag_independence", np.array_equal(matrix(prefix, "Kst"), matrix("S02", "Kst")))
        exact(f"{prefix}:torsional_mass_retained", np.array_equal(matrix(prefix, "M")[np.ix_(TORSION, TORSION)], matrix("S02", "M")[np.ix_(TORSION, TORSION)]))
        exact(f"{prefix}:torsional_stiffness_retained", np.array_equal(matrix(prefix, "K")[np.ix_(TORSION, TORSION)], matrix("S02", "K")[np.ix_(TORSION, TORSION)]))
        exact(f"{prefix}:phi_controlled_only_by_shear", d["phi"] == (cases[by_prefix["S02"]]["derived"]["phi"] if d["shear_effects"] else 0))
    exact("rotary_flag_changes_lateral_mass", not np.array_equal(matrix("S02", "M")[np.ix_(LATERAL, LATERAL)], matrix("S05", "M")[np.ix_(LATERAL, LATERAL)]))
    exact("shear_flag_changes_lateral_K", not np.array_equal(matrix("S02", "K")[np.ix_(LATERAL, LATERAL)], matrix("S04", "K")[np.ix_(LATERAL, LATERAL)]))
    for label, plus, minus in (("axial_load", "S20", "S21"), ("torque", "S22", "S23")):
        base = matrix("S02", "K")[np.ix_(LATERAL, LATERAL)]
        kp, km = matrix(plus, "K")[np.ix_(LATERAL, LATERAL)], matrix(minus, "K")[np.ix_(LATERAL, LATERAL)]
        dp, dm = kp - base, km - base
        err = np.abs(dp + dm)
        # Subtracting loaded/base matrices has a per-entry cancellation floor.
        # Do not normalize this load check by unrelated axial/torsional stiffness.
        rounding = 8 * EPS * (np.abs(kp) + np.abs(km) + 2 * np.abs(base))
        exact(f"{label}:signed_linear_addition", bool(np.all(err <= rounding)),
              max_addition_error=float(err.max()), max_entry_rounding_bound=float(rounding.max()),
              contribution_max=float(np.max(np.abs(dp))), per_entry_bound=True)
        exact(f"{label}:nonzero_addition", bool(np.any(dp != 0)))
    T = cases[by_prefix["S22"]]["resolved_input"]["torque"]
    torque_delta = matrix("S22", "K") - matrix("S02", "K")
    close("torque:alpha_beta_sign", torque_delta[3, 4], -T / 2)
    close("torque:beta_alpha_sign", torque_delta[4, 3], T / 2)
    exact("torque:nonsymmetry_is_not_removed", not np.array_equal(matrix("S22", "K"), matrix("S22", "K").T))
    rho_ratio = cases[by_prefix["S26"]]["material_effective"]["rho"] / cases[by_prefix["S02"]]["material_effective"]["rho"]
    for name in ("M", "G", "Kst"):
        for block_name, idx in (("lateral", LATERAL), ("axial", AXIAL), ("torsion", TORSION)):
            close(f"density:{name}:{block_name}", matrix("S26", name)[np.ix_(idx, idx)], rho_ratio * matrix("S02", name)[np.ix_(idx, idx)])
    exact("density:K_unchanged", np.array_equal(matrix("S26", "K"), matrix("S02", "K")))

    baseline = cases[by_prefix["S02"]]
    L = baseline["resolved_input"]["L"]
    K = matrix("S02", "K")
    scaling = np.array([L, L, L, 1., 1., 1.] * 2)
    KH = scaling[:, None] * K * scaling[None, :]
    rigid = np.zeros((12, 6))
    for i in range(3):
        rigid[i, i] = rigid[i + 6, i] = L
    rigid[5, 3] = rigid[11, 3] = 1
    rigid[3, 4] = rigid[9, 4] = 1; rigid[7, 4] = -L
    rigid[4, 5] = rigid[10, 5] = 1; rigid[6, 5] = L
    for i, label in enumerate(("x_translation", "y_translation", "z_translation", "torsion", "alpha_rotation_y1_negative", "beta_rotation_x1_positive")):
        vhat = rigid[:, i] / scaling
        residual = maxabs(KH @ vhat) / (maxabs(KH) * maxabs(vhat))
        exact(f"baseline:rigid_{label}", residual <= AUDIT_ROUNDING_BOUND, scaled_residual=residual)
    eigK = np.linalg.eigvalsh(KH)
    exact("baseline:K_positive_semidefinite", bool(eigK.min() >= -AUDIT_ROUNDING_BOUND * maxabs(KH)), minimum=float(eigK.min()))
    exact("baseline:six_elastic_directions", int(np.linalg.matrix_rank(KH)) == 6, rank=int(np.linalg.matrix_rank(KH)))
    failures = [c for c in checks if c["status"] != "PASS"]
    report = {"schema_version": 1, "status": "FAIL" if failures else "PASS",
              "role": "Independent audit of ROSS authority outputs; not native B1 qualification",
              "generator_head": authority["generator_head"], "ross_sha": authority["ross_sha"],
              "case_count": authority["case_count"], "matrix_count": authority["matrix_count"],
              "lateral_selection_count": authority["lateral_selection_count"],
              "data_bundle_sha256": authority["data_bundle_sha256"],
              "authority_sha256": file_hash(root / "authority.json"),
              "inspector_sha256": file_hash(Path(__file__)),
              "rounding_bound": AUDIT_ROUNDING_BOUND, "rounding_basis": "1024*binary64 epsilon for independent scalar/block arithmetic; exact structural gates separate",
              "source_sha256": {r["path"]: r["checkout_sha256"] for r in authority["sources"]},
              "output_sha256": {r["filename"]: r["sha256"] for r in authority["arrays"]},
              "check_count": len(checks), "failed_count": len(failures), "failures": failures,
              "checks": checks, "cases": diagnostics}
    if report_path is None:
        report_path = root / "inspection.json"
    write_json(report_path, report)
    print("B1_INSPECTION " + json.dumps({k: report[k] for k in ("status", "check_count", "failed_count", "failures", "data_bundle_sha256", "inspector_sha256")}, sort_keys=True))
    for prefix in ("S17", "S18", "S19", "S24"):
        d = diagnostics[by_prefix[prefix]]
        print("B1_CONICAL_CONVENTION " + json.dumps({"case": prefix, "axial_rigid_mass": d["axial_rigid_mass"], "constructor_geometric_mass": d["constructor_geometric_mass"], "ratio": d["axial_mass_to_geometric_mass_ratio"]}, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = inspect_candidate(args.candidate, args.report)
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
