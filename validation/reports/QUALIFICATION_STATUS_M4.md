# Qualification status — Stage 1 M4

MATLAB/Octave remains unavailable, so MATLAB numerical-equivalence gates remain BLOCKED regardless of source-derived and example-campaign success.

| Gate | Status | M4 evidence |
|---|---|---|
| G1 source integrity | PASS | authoritative reference tree retained |
| G2 Fortran Release build | PASS | clean Release build + 4/4 CTest |
| G3 Fortran Debug build | PASS | runtime-check Debug build + 4/4 CTest |
| G4 Python package tests | PASS | 40/40 pytest |
| G5 element matrices | BLOCKED | source/invariant tests pass; MATLAB matrix baseline unavailable |
| G6 global M/C/G/K | BLOCKED | source/invariant tests pass; MATLAB global baseline unavailable |
| G7 modal equivalence | BLOCKED | eigenvalues/eigenvectors/kappa/eccentricity paths execute; MATLAB modal baseline unavailable |
| G8 harmonic response | BLOCKED | freq_rsp + freq_aux + supplied two-bearing freq_fdn source-equation tests pass; MATLAB response baseline unavailable and generalized variable-width foundation forcing is not yet claimed |
| G9 critical speeds | BLOCKED | direct/method2/method3 and example campaign pass; MATLAB baseline unavailable |
| G10 transient | NOT_EXECUTED | deliberate Phase-8 hold: time_fdn/runup not implemented |
| G11 coaxial | BLOCKED | translated example + source-oracle pass; MATLAB coaxial baseline unavailable |
| G12 asymmetric rotor | BLOCKED | translated examples + legacy compatibility tests pass; MATLAB rotating-frame baseline unavailable |
| G13 22 examples | PARTIAL | 22/22 Python entry points; 20/22 complete before Phase 8; 2/22 partial due deliberate transient/runup block; campaign 30 PASS, 2 BLOCKED, 0 FAIL |
| G14 book problems | NOT_EXECUTED | still downstream |
| G15 Python↔Fortran ABI | PASS | stationary vectors, freq_rsp, freq_aux, freq_fdn, critical, coaxial, asymmetric exercised |
| G16 Linux execution | PASS | Release, Debug, pytest and 22-example campaign executed |
| G17 Windows execution | BLOCKED | Windows environment unavailable |
| G18 clean package validation | PASS | clean staging install/build/test/campaign PASS; delivery ZIP was then extracted and re-tested without modifying the archive |
