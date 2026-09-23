# Stage 1 M2 — Qualification Status

This increment continues M1 and does not restart the migration.

## Implemented
- circular shaft (retained from M1);
- tapered shaft types 21–28;
- asymmetric shaft element types 11–18;
- stationary bearing matrix types 1–8 and legacy type-20 handling;
- stationary assembly M, C0, G, K0, K1;
- stationary eigensystem;
- synchronous frequency response;
- critical speed: direct, iterative-by-index, iterative-nearest;
- Python domain/validation/units/solver facade/analysis service/results/CLI/post;
- examples 05.08.01, 06.03.01, 06.08.01 smoke.

## Executed evidence
- GNU Fortran 14.2.0
- CMake 3.31.6
- Python 3.13.5
- NumPy 2.3.5
- Matplotlib 3.10.8
- BLAS: system libblas
- LAPACK: system liblapack
- Release CTest: 6/6 PASS
- Debug CTest: 6/6 PASS
- Python tests: 11 PASS
- clean package: PASS
- Linux execution: PASS

## Internal source-contract metrics
- M symmetry relative residual: 0
- K0 symmetry relative residual: 0
- G skew-symmetry relative residual: 0
- min(diag(M)): 1.829169915657742e-2
- FRF smoke: finite, max |response| = 4.694373601314077e-6
- modal smoke: 24 eigenvalues, finite
- critical direct vs iterative-index max relative difference: 4.515094184254428e-9
- critical direct vs iterative-nearest max relative difference: 3.147674577055436e-14
- iterative critical convergence: all true

These are internal checks only; they are not MATLAB equivalence.

## Gates
| Gate | Status | Evidence / reason |
|---|---|---|
| G1 source integrity | PASS | hashes/inventory retained |
| G2 Fortran Release | PASS | 6/6 CTest |
| G3 Fortran Debug | PASS | 6/6 CTest |
| G4 Python tests | PASS | 11 pytest |
| G5 element matrices | BLOCKED | internal checks executed; MATLAB baseline unavailable |
| G6 global M/C/G/K | BLOCKED | internal invariants executed; MATLAB baseline unavailable |
| G7 modal equivalence | BLOCKED | MATLAB/Octave unavailable |
| G8 harmonic response | BLOCKED | implemented/tested internally; MATLAB equivalence unavailable |
| G9 critical speeds | BLOCKED | implemented/tested internally; MATLAB equivalence unavailable |
| G10 transient | NOT_EXECUTED | pending |
| G11 coaxial | NOT_EXECUTED | pending |
| G12 asymmetric rotor | NOT_EXECUTED | only asymmetric element migrated; rotating-frame solver pending |
| G13 22 examples | NOT_EXECUTED | 3/22 smoke |
| G14 book problems | NOT_EXECUTED | 83 inventoried, campaign pending |
| G15 Python↔Fortran ABI | PASS | ctypes/ISO_C_BINDING exercised |
| G16 Linux | PASS | clean Linux execution |
| G17 Windows | BLOCKED | Windows execution unavailable |
| G18 clean package | PASS | extracted/rebuilt/retested |

## Legacy defects intentionally not hidden
- shftasym non-zero axial-force branch references undefined Kre in V2: explicit legacy-defect gate, no invented physics;
- shftasym Cs/Ms overwrite remains documented pending MATLAB execution;
- hydrodynamic bearing at exactly zero speed is undefined in source expression: ABI rejects the point to avoid NaN/Inf, without claiming equivalence;
- bearasym/chr_asym/freq_fdn/time_fdn/runup issues remain documented and are not silently fixed.
