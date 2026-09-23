# Qualification status — Stage 1 M2 — executed 2026-09-23

Authoritative MATLAB baseline execution: **BLOCKED** — neither MATLAB nor GNU Octave is installed in the execution environment. This blocks equivalence declarations but not independent implementation/build/test work.

| Gate | Status | Evidence |
|---|---|---|
| G1 source integrity | PASS | preserved M1 source hashes/inventory; same baseline continued |
| G2 Fortran Release build | PASS | Release build + 6/6 CTest |
| G3 Fortran Debug build | PASS | Debug build + 6/6 CTest |
| G4 Python package tests | PASS | `python_tests_m2.txt`: 11 passed |
| G5 element matrices equivalence | BLOCKED | circular/taper/asym tests executed; MATLAB/Octave equivalence unavailable |
| G6 global assembly equivalence | BLOCKED | M/C/G/K internal invariants executed; MATLAB/Octave equivalence unavailable |
| G7 modal equivalence | BLOCKED | full eigensystem/ABI executed; MATLAB/Octave equivalence unavailable |
| G8 harmonic response equivalence | BLOCKED | `freq_rsp` implemented and smoke-tested; MATLAB/Octave equivalence unavailable |
| G9 critical speeds equivalence | BLOCKED | direct + iterative methods implemented/tested; MATLAB/Octave equivalence unavailable |
| G10 transient | NOT_EXECUTED | `time_fdn/runup` not migrated in M2 |
| G11 coaxial | NOT_EXECUTED | coaxial solver not migrated in M2 |
| G12 asymmetric rotor | NOT_EXECUTED | `shftasym` element exists; `rotorasym/bearasym/chr_asym/freq_asym` not yet migrated |
| G13 22 examples | NOT_EXECUTED | 3/22 (`Example_05_08_01`, `Example_06_03_01` case 1, `Example_06_08_01` LH1/RH1) execute end-to-end; remaining cases/examples not yet translated/qualified |
| G14 book problem regression | NOT_EXECUTED | 83 scripts remain inventory/validation material |
| G15 Python↔Fortran ABI | PASS | solver v0.3.0: assembly/modal/FRF/critical/element paths exercised through ctypes |
| G16 Linux execution | PASS | GNU Fortran 14.2.0; CMake 3.31.6; Release/Debug, pytest, CLI, example executed |
| G17 Windows execution | BLOCKED | no Windows runtime/cross-build validation performed |
| G18 clean package validation | PASS | extracted candidate rebuilt Release+Debug, installed Python package offline to clean target, 11 pytest, CLI and 3 examples passed; no original-tree dependency |

`M2_QUALIFICATION.md` and `M2_INTERNAL_METRICS.json` contain the supplemental evidence. Internal PASS results never override the BLOCKED MATLAB-equivalence gates.
