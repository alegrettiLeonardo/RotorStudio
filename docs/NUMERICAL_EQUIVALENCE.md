# Numerical equivalence

Formal authority execution uses pinned GNU Octave 7.1.0 as a MATLAB-compatible probe of the preserved V2 sources. It is identified as Octave evidence, not MATLAB execution.

Fixed gates:
- element matrices: relative Frobenius <= 1e-12
- global matrices: relative Frobenius <= 1e-12
- eigenvalues / natural frequencies: relative <= 1e-8
- isolated-mode MAC >= 0.999999
- complex response: relative <= 1e-8
- critical speeds: relative <= 1e-6
- whirl/kappa: <= 1e-10
- transient tolerances are frozen before Fortran comparison from authority-vs-independent-source-reference discrepancy.

M7 formal G5-G12 is reproduced in CI. The G1 correction is documented in `validation/reports/M7_AUTHORITY_INTEGRITY_AUDIT.md`; the earlier M7 run #8 masked a failing verifier because `tee` was used without pipefail. The hardened workflow no longer permits that failure mode.

G14 extends qualification to 83 DRM problem scripts. A_SOLVER cases trace V2 solver calls and compare them to Fortran/Python; B_ANALYTICAL cases execute as independent regressions.
