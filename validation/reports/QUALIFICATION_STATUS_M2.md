# Qualification status — Stage1 M2

| Gate | Status | Evidence / scope |
|---|---|---|
| G1 source integrity | PASS | M1 references retained; source hashes unchanged |
| G2 Fortran Release build | PASS | clean Release build executed |
| G3 Fortran Debug build | PASS | checks-enabled Debug build executed |
| G4 Python package tests | PASS | 8 pytest tests |
| G5 element matrices | BLOCKED | structural/invariant checks PASS; MATLAB numeric equivalence unavailable |
| G6 global M/C/G/K | BLOCKED | ABI assembly + invariants PASS; MATLAB matrix baseline unavailable |
| G7 modal equivalence | BLOCKED | M1 modal smoke unchanged; MATLAB baseline unavailable |
| G8 harmonic response | BLOCKED | Fortran/Python freq_rsp smoke PASS; MATLAB complex-response baseline unavailable |
| G9 critical speeds | BLOCKED | direct + iterative smoke PASS; MATLAB critical-speed baseline unavailable |
| G10 transient | NOT_EXECUTED | outside this increment |
| G11 coaxial | NOT_EXECUTED | outside this increment |
| G12 asymmetric rotor | NOT_EXECUTED | element `shftasym` migrated; full rotating-frame assembly/solver not yet migrated |
| G13 22 examples | NOT_EXECUTED | M1 example 05_08_01 still passes; remaining examples pending |
| G14 book problems | NOT_EXECUTED | inventory retained |
| G15 Python↔Fortran ABI | PASS | modal, assembly, FRF and critical-speed calls exercised |
| G16 Linux execution | PASS | current environment |
| G17 Windows execution | BLOCKED | Windows execution unavailable here |
| G18 clean package validation | PASS | clean extract/build/test/example smoke executed for M2 |

`PASS` is not claimed for MATLAB equivalence where MATLAB/Octave execution evidence is absent.
