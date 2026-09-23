# M2 qualification report — continuation of M1

## Scope executed

M2 continued the same Stage-1 baseline and implemented `taper.m`, element-level `shftasym.m`, completed stationary `bearmtx.m`, expanded the stationary M/C/G/K assembly path, implemented `freq_rsp.m`, and implemented `crit_spd.m` direct / iterative-index / iterative-nearest paths.

## Source-preservation decisions

- Tapered types 21–28 follow `taper.m`. The no-taper, zero-axial-force limiting case was checked against the circular element and agrees to floating-point roundoff. The V2 tapered axial-force expression is retained as written; no undocumented reconciliation with `shftelem.m` was introduced.
- `shftasym.m` with nonzero axial force reaches an undefined `Kre` source branch. M2 returns `RD_ERR_LEGACY_DEFECT=40`; it does not invent a corrected physical matrix.
- Type-7 hydrodynamic bearing at exactly zero speed is mathematically undefined in the V2 expressions because they divide by speed. The ABI rejects that point with `RD_ERR_INPUT` rather than propagating NaN/Inf.

## Executed internal numerical evidence

`M2_INTERNAL_METRICS.json` records:

- global test model: `M_sym_rel=0`, `K0_sym_rel=0`, `G_skew_rel=0` in the executed arithmetic path;
- minimum global mass diagonal `1.829169915657742e-02`;
- synchronous-response smoke: finite 12x3 complex response, max amplitude `4.694373601314077e-06`;
- first three direct criticals `[201.3563044026349, 201.3759693011592, 556.1850985175189] rad/s`;
- max internal relative difference direct vs iterative-index `4.515094184254428e-09`;
- max internal relative difference direct vs iterative-nearest `3.147674577055436e-14`;
- all iterative checks converged.

These are internal/source-contract measurements only.

## MATLAB-equivalence gate

**BLOCKED**: neither MATLAB nor GNU Octave is installed. No matrix, modal, FRF or critical-speed result in this report is promoted to MATLAB-equivalence PASS.

## Migrated example smoke tests

- `Example_05_08_01`: executed end-to-end; same first-eight 80-element frequencies as M1.
- `Example_06_03_01`: case 1 executed, including Campbell and 450-point synchronous `freq_rsp`; max response amplitude `4.038121054413e-03`.
- `Example_06_08_01`: LH case 1 / RH case 1 executed, including direct and iterative critical-speed paths. The outputs are deliberately **not** used as MATLAB reference values. In particular, any source-ordering oddities remain subject to MATLAB baseline comparison rather than being silently normalized.
