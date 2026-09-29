# Frozen source and implementation map

Authority: petrobras/ross, commit 6320eab9f890f1b3cc1710d508b446fe063ca68d,
Apache License 2.0, ROSS developers. A0 calls the unchanged upstream API.
Per-file SHA-256, Python/NumPy/SciPy/ROSS/platform and generation time are in
validation/ross_parity/static/authority.json. This is not a production ROSS dependency.

| Feature | Frozen ROSS authority / production boundary | Versioned ABI | Current campaign status |
|---|---|---|---|
| A0 | immutable reference infrastructure | none | PASS / PROMOTED |
| A1 | `Rotor.run_static` / native `rd_static.f90` | `rd_static_v1` | PASS / PROMOTED |
| A2 | `run_freq_response` / native general dynamic stiffness + FRF | `rd_frf_general_v1` | PASS / PROMOTED |
| A3 | `run_forced_response` / native arbitrary forced response | `rd_forced_response_v1` | PASS / PROMOTED |
| A4 | `run_time_response` / native Newmark/general time response | `rd_time_response_v1` | PASS / PROMOTED |
| A5 | `run_ucs` / native UCS, intersections and Rouch logic | `rd_ucs_required_v1`, `rd_ucs_map_v1`, `rd_ucs_matrix_v1`, `rd_ucs_v1` | PASS / PROMOTED |
| A6 | `run_level1` / native Level 1 sweep and whirl selection | `rd_level1_required_v1`, `rd_level1_matrix_v1`, `rd_level1_v1` | PASS / PROMOTED |
| A7 | `api617_unbalance` / native modal-whirl-antinode-static-load placement | `rd_api617_unbalance_required_v1`, `rd_api617_unbalance_v1` | PASS / PROMOTED |
| A8 | `run_clearance_analysis` / native synchronous response, probe scaling and clearance check | `rd_clearance_required_v1`, `rd_clearance_v1` | IMPLEMENTED; exact-head promotion gates pending |

Never infer a qualified Fortran feature from a generated ROSS reference.
Full pre-implementation inventory, risks and acceptance: ROSS_ANALYSIS_EXPANSION_AUDIT.md.

Qualification is always bound to the exact implementation SHA under review.
Previous-head runs are evidence of progress only and are never substituted for
the matching final push/PR matrix. A8 must branch from the promoted A7 merge,
not from an intermediate A7 implementation head.
