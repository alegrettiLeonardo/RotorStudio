# Qualification status — Stage 1 M5

MATLAB/Octave remains unavailable. Source-derived and book-example evidence does not promote MATLAB-equivalence gates to PASS.

| Gate | Status | M5 evidence |
|---|---|---|
| G1 source integrity | PASS | M4 authority retained; `time_fdn.m`, `runup.m`, and transient example sources frozen by SHA256 |
| G2 Fortran Release build | PASS | clean Release build + 5/5 CTest |
| G3 Fortran Debug build | PASS | runtime-check Debug build + 5/5 CTest |
| G4 Python package tests | PASS | delivery package 47/47 pytest |
| G5 element matrices | BLOCKED | prior source/invariant evidence retained; MATLAB matrix baseline unavailable |
| G6 global M/C/G/K | BLOCKED | prior assembly/source evidence retained; MATLAB global baseline unavailable |
| G7 modal equivalence | BLOCKED | stationary modal path plus transient DGGEV reduction execute; MATLAB modal baseline unavailable |
| G8 harmonic response | BLOCKED | prior M4 qualification retained; MATLAB response baseline unavailable |
| G9 critical speeds | BLOCKED | prior M4 qualification retained; MATLAB critical-speed baseline unavailable |
| G10 transient overall | BLOCKED | implementation/source-derived/example qualification PASS; MATLAB ode45 equivalence unavailable |
| G10a transient implementation | PASS | `time_fdn`, `runup`, DGGEV reduction, DP5(4), ABI and Python APIs executed |
| G10b source-derived transient oracle | PASS | independent SciPy eig/DOP853 comparisons PASS; frozen binary references ship in the M5 delivery ZIP |
| G10c MATLAB ode45 equivalence | BLOCKED | MATLAB/Octave not installed; authoritative tolerance not yet measurable |
| G11 coaxial | BLOCKED | M4 implementation/tests retained; MATLAB coaxial baseline unavailable |
| G12 asymmetric rotor | BLOCKED | M4 implementation/tests retained; MATLAB rotating-frame baseline unavailable |
| G13 22 examples | PASS | 22/22 entry points; 33 campaign runs PASS; full transient branches 06_05_01(b), 06_11_01 cases 1/2 execute |
| G14 book problem regression | NOT_EXECUTED | still downstream |
| G15 Python↔Fortran ABI | PASS | transient ABI added and exercised alongside all M4 paths |
| G16 Linux execution | PASS | Release, Debug, pytest, campaign and full transient examples executed |
| G17 Windows execution | BLOCKED | Windows execution unavailable |
| G18 clean package validation | PASS | exact M5 ZIP extract/install/rebuild/CTest/pytest/22-example campaign completed |

## Phase-8 compatibility notes

- `time_fdn` preserves the V2 tautological bearing predicate `type > 2 | type < 9`.
- `runup` preserves the V2 constant-bearing restriction.
- `runup` canonicalizes MATLAB's clean-workspace `j = sqrt(-1)` meaning; user-shadowed `j` is not emulated.
- modal truncation uses V2 `eig(K,M)` semantics, not the Guyan reduction described by Manual V1.
- reduced transient cases requiring a genuinely complex modal basis return an explicit unsupported status rather than silently discard imaginary components.
