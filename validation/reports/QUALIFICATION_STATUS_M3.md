# Qualification status — Stage 1 M3

`MATLAB/Octave execution = unavailable`, so no MATLAB equivalence gate is promoted to PASS.

| Gate | Status | M3 evidence |
|---|---|---|
| G1 source integrity | PASS | preserved M1/M2 reference tree and authoritative hashes |
| G2 Fortran Release build | PASS | clean Release configure/build + 4/4 CTest |
| G3 Fortran Debug build | PASS | checks-enabled Debug configure/build + 4/4 CTest |
| G4 Python package tests | PASS | 36/36 tests |
| G5 element matrices | BLOCKED | source-formula tests PASS for circular/taper/asymmetric elements; MATLAB matrix baseline unavailable |
| G6 global M/C/G/K | BLOCKED | assembly/invariant/source-equation tests PASS; MATLAB global matrices unavailable |
| G7 modal equivalence | BLOCKED | stationary modal execution PASS; MATLAB eigenvalue/eigenvector baseline unavailable |
| G8 harmonic response | BLOCKED | `freq_rsp` source-equation qualification PASS; MATLAB complex-response baseline unavailable |
| G9 critical speeds | BLOCKED | direct/method2/method3 source-equation qualification PASS; MATLAB critical-speed baseline unavailable |
| G10 transient | NOT_EXECUTED | deliberately deferred; no `time_fdn/runup` implementation in M3 |
| G11 coaxial | BLOCKED | `chr_root_coax` + `freq_rsp_coax` implemented and source-equation tests PASS; MATLAB coaxial baseline unavailable |
| G12 asymmetric rotor | BLOCKED | `rotorasym/bearasym/chr_asym/freq_asym` implemented with V2 defect compatibility tests PASS; MATLAB rotating-frame baseline unavailable |
| G13 22 examples | NOT_EXECUTED | 3/22 translated/executed (`05_08_01`, `06_06_01`, `07_06_01`); remaining 19 pending |
| G14 book problem regression | NOT_EXECUTED | inventory retained; migration/qualification pending |
| G15 Python↔Fortran ABI | PASS | stationary matrices/modal/FRF/critical + bearing audit + coaxial + asymmetric paths exercised |
| G16 Linux execution | PASS | Release, Debug, pytest and smoke examples executed |
| G17 Windows execution | BLOCKED | Windows execution unavailable in this environment |
| G18 clean package validation | PASS | candidate clean extract/install/build/test/examples PASS; exact final archive is additionally re-tested after packaging |

## Deliberate compatibility guards

- nonzero axial load for the asymmetric `shftasym` path: blocked because V2 uses undefined `Kre`;
- type-7 fluid bearing at exactly zero speed: explicit error status because V2 itself states the model is undefined there and proceeds into singular arithmetic.

Neither guard is used to claim MATLAB equivalence.
