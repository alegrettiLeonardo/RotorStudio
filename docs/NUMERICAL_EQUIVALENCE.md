# Numerical equivalence and M2 internal qualification

Requested MATLAB-equivalence thresholds remain unchanged:

- element matrices: `<= 1e-12` relative;
- global matrices: `<= 1e-12` relative;
- eigenvalues/frequencies: `<= 1e-8` relative;
- isolated-mode MAC: `>= 0.999999`;
- complex response: `<= 1e-8` relative;
- critical speeds: `<= 1e-6` relative;
- whirl/kappa: `<= 1e-10` abs/rel.

These gates cannot be evaluated without an authoritative MATLAB/Octave run and are therefore **BLOCKED**, not relaxed.

M2 adds independent implementation evidence:

- Debug and Release Fortran builds and six CTest targets;
- tapered constant-section / circular relation for axial-force zero across types 21–28;
- global `M` symmetry, conservative `K0` symmetry, gyroscopic `G` skew symmetry, positive mass and finite matrices;
- `freq_rsp` complex solve smoke test through ZGESV;
- direct and iterative critical-speed internal consistency;
- 11 Python tests across the real ABI;
- `Example_05_08_01` end-to-end regression on the migrated stack.

Exact measured values are in `validation/reports/M2_INTERNAL_METRICS.json`. These checks **do not substitute for MATLAB equivalence**.
