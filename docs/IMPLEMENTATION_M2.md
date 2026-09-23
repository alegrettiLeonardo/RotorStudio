# Stage 1 M2 — continuation from M1

This increment continues the existing M1 baseline; it does not restart the migration.

Implemented in this increment:

- `taper.m` -> `rd_shaft_tapered.f90` for legacy types 21..28.
- `shftasym.m` -> `rd_shaft_asymmetric.f90` for the executable zero-axial-load path.
- Explicit preservation of the V2 `shftasym` axial-force defect: nonzero axial force returns `RD_ERR_UNSUPPORTED` instead of silently inventing `Kre`.
- Explicit preservation of the V2 rotary-inertia `Cs = rhoI*Ms/(15*L)` behavior.
- `bearmtx.m` types 1..8, including short-bearing and seal coefficients.
- `rd_assemble_legacy` ABI for M/C/K/G inspection.
- `freq_rsp.m` synchronous response for force types 1, 2, 3 and 8; other legacy force types are ignored exactly by `freq_rsp`.
- `crit_spd.m` direct method for constant-property bearings and iterative-by-mode-number path for speed-dependent type 7/8 bearings.
- Python typed `TaperedShaftElement`, `AsymmetricShaftElement`, `Force`, `BendPoint`.
- Python `FrequencyResponseResult`, `CriticalSpeedResult`, solver facade methods and CLI commands.

Qualification status:

- Internal no-taper equivalence test: `taper(type=21..28, doj=dok, dij=dik)` matches `shftelem(type=1..8)` for M/K/G within 2e-12 relative: PASS.
- M symmetry, G antisymmetry, positive mass, finite matrix checks through Python↔Fortran ABI: PASS.
- Frequency-response smoke with unbalance, including zero-speed zero response: PASS.
- Critical-speed direct smoke: PASS.
- Type-7 iterative critical-speed execution: PASS (smoke only).
- MATLAB/Octave numerical equivalence remains BLOCKED because neither executable is available in the execution environment.

No desktop UI was added.
