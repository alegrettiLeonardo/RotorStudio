# Frozen source and implementation map

Authority: petrobras/ross, commit 6320eab9f890f1b3cc1710d508b446fe063ca68d,
Apache License 2.0, ROSS developers. A0 calls the unchanged upstream API.
Per-file SHA-256, Python/NumPy/SciPy/ROSS/platform and generation time are in
validation/ross_parity/static/authority.json. This is not a production ROSS dependency.

| Feature | ROSS file / method | Planned Fortran | Planned ABI | Binding / tests | Status |
|---|---|---|---|---|---|
| A0 | rotor_assembly.py / Rotor.run_static | none (reference infrastructure) | none | validation/ross_parity/tests | BLOCKED: full CI pending |
| A1 | rotor_assembly.py / run_static | rd_static.f90 | rd_static_v1 | thin ffi/backend/facade + service; golden static | BLOCKED by A0 |
| A2 | rotor_assembly.py / run_freq_response, transfer_matrix | rd_dynamic_stiffness, rd_frf_general | rd_frf_general_v1 | not implemented | BLOCKED |
| A3 | rotor_assembly.py / run_forced_response | rd_forced_response | rd_forced_response_v1 | not implemented | BLOCKED |
| A4 | rotor_assembly.py / run_time_response; utils.py / Newmark | rd_newmark, rd_time_response, rd_force_provider | rd_time_response_v1 | not implemented | BLOCKED |
| A5 | rotor_assembly.py / run_ucs | rd_ucs, rd_intersections | to specify | not implemented | BLOCKED |
| A6 | rotor_assembly.py / run_level1 | rd_level1 | to specify | not implemented | BLOCKED |
| A7 | rotor_assembly.py / api617_unbalance | rd_orbit, rd_antinode, rd_api617 | to specify | not implemented | BLOCKED |
| A8 | rotor_assembly.py / run_clearance_analysis | rd_api617_clearance | to specify | not implemented | BLOCKED |

Never infer a qualified Fortran feature from a generated ROSS reference.
Full pre-implementation inventory, risks and acceptance: ROSS_ANALYSIS_EXPANSION_AUDIT.md.
