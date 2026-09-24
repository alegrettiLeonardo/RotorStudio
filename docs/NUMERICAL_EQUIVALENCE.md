# Numerical equivalence and qualification

Stage 1 uses explicit PASS/FAIL/BLOCKED gates. Compilation alone is not qualification.

## Formal V2 gates

The formal comparator evaluates element matrices, global assembly, modal results, harmonic response, critical speeds, transients, coaxial and asymmetric analyses against a fresh GNU Octave 7.1.0 execution of the frozen V2 source. Thresholds are fixed independently of the Fortran result:

| Quantity | Gate |
|---|---:|
| element matrices | relative error <= 1e-12 |
| global matrices | relative error <= 1e-12 |
| eigenvalues | relative error <= 1e-8 |
| natural frequencies | relative error <= 1e-8 |
| isolated-mode MAC | >= 0.999999 |
| complex response | relative error <= 1e-8 |
| critical speeds | relative error <= 1e-6 |
| whirl/kappa transform | abs/rel <= 1e-10 |

Transient tolerance is frozen from Octave-vs-independent source-oracle discrepancy before the Fortran comparison. The comparator refuses missing authority data and does not relax thresholds after seeing Fortran output.

## G14 book problems

The exact `DRM_problem_scripts.zip` is reconstructed only after verifying SHA256 `8b5db23fa57bc5e41f68ed9e25ab8f1f1a72e4a24b9e11af38dccdd4098501d1`. Inventory is deterministic: 83 cases, with Class A assigned only when the original problem calls a V2 numerical solver/matrix routine. Current classification is 15 A / 68 B.

All 83 original scripts are executed in pinned Octave 7.1.0. Class A final workspaces are then independently sampled through the production `drm_core -> ctypes -> Fortran` path. Class B remains analytical/educational and is not migrated into a competing rotor solver.

## Reproducibility

Formal M7 qualification, Windows G17 and final Stage 1 closure are CI jobs. Final G19 is valid only when the exact PR tree passes source integrity, formal V2 comparison, Python/Fortran regression, G14, legacy runtime probes, all graphical examples and the clean-package qualification.
