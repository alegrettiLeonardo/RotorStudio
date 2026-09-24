# Qualification status — Stage 1 final closure

Stage 1 is qualified for the declared migration scope: Fortran 2018 numerical core plus GUI-independent Python Core, validation, pre/post-processing, plots, persistence, reports, CLI, examples and qualification infrastructure.

The numerical/behavioural authority remains `Rotor_Software_v2`. GNU Octave 7.1.0 is used only where explicitly identified as an Octave authority/probe; no MATLAB execution is claimed where MATLAB was not used.

## Final gate matrix

| Gate | Status | Final evidence contract |
|---|---|---|
| G1 source integrity | **PASS** | exact V2 ZIP SHA256 and 19 required numerical sources verified against the frozen canonical-LF manifest |
| G2 Fortran Release build | **PASS** | Release configure/build and CTest 5/5 |
| G3 Fortran Debug build | **PASS** | Debug configure/build and CTest 5/5 with runtime checks |
| G4 Python package tests | **PASS** | 57/57 pytest on Linux; 57/57 on qualified Windows UCRT64 job |
| G5 element matrices | **PASS** | frozen formal equivalence threshold `<=1e-12` reproduced |
| G6 global M/C/G/K | **PASS** | frozen formal equivalence threshold `<=1e-12` reproduced |
| G7 modal equivalence | **PASS** | eigenvalues/frequencies/MAC/whirl gates reproduced with the frozen policy |
| G8 harmonic response | **PASS** | complex response gate `<=1e-8` reproduced |
| G9 critical speeds | **PASS** | direct/iterative critical-speed gate `<=1e-6` reproduced |
| G10 transient | **PASS** | frozen one-way transient tolerance policy reproduced; no post-comparison relaxation |
| G11 coaxial | **PASS** | eigenvalue/MAC/response formal comparison reproduced |
| G12 asymmetric rotor | **PASS** | one-output/two-output compatibility plus modal/response formal comparison reproduced |
| G13 22 examples | **PASS** | 33/33 deterministic campaign runs, 22 unique examples, plus 22/22 headless graphical coverage |
| G14 book problem regression | **PASS** | 83/83 inventoried and semantically classified; 83/83 deterministic regressions; 20/20 A/hybrid product comparisons; 0 unexpected BLOCKED; solver-duplication audit PASS |
| G15 Python↔Fortran ABI | **PASS** | ctypes/ISO_C_BINDING production paths exercised; explicit element ABI probe PASS |
| G16 Linux execution | **PASS** | Release, Debug, Python, examples, formal Octave, G14 and clean-package qualification executed on Ubuntu |
| G17 Windows execution | **PASS** | UCRT64 Release/Debug CTest 5/5, raw DLL load, production loader, ABI probe, 57/57 pytest and 33/33 example campaign |
| G18 clean package validation | **PASS** | generated Stage 1 ZIP extracted into an empty temporary tree; Fortran rebuilt; isolated Python venv installed; 5/5 CTest, 57/57 pytest, 33/33 examples, 22/22 graphics and 83/83 G14 inventory; no source-tree dependency |
| G19 reproducible formal CI | **PASS** | corrected fail-closed workflow reproduces authority integrity, Linux Release/Debug, pinned GNU Octave 7.1.0 G5–G12 and Windows G17 on the same PR tree |

## G14 closure

The final semantic split is:

- `A_SOLVER`: 15
- `A_WITH_ANALYTIC_ORACLE`: 5
- `B_ANALYTICAL`: 63

The two independent GNU Octave 7.1.0 book-problem passes produce 82 PASS + one planned `NOT_APPLICABLE` (`Problem_03_12.m`, whose MATLAB variable `do` is an Octave keyword). That single case uses a validation-only source-derived analytical oracle and does not claim an Octave or MATLAB baseline.

The three G14 infrastructure defects found during closure were corrected without changing qualified Fortran physics or relaxing thresholds:

1. MATLAB `Model.bend` nnode-by-1 vectors collapsed by SciPy loading are restored to the exact legacy row semantics before model construction.
2. The one-plane Euler beam oracle is compared against the structurally paired x/y degeneracy of the isotropic rotor model using the existing frozen frequency threshold.
3. Eigenvalue comparisons reuse the already-qualified G7 offline mode association rather than elementwise ordering at crossings.

## Legacy runtime probes

Pinned GNU Octave 7.1.0 runtime probes confirm the documented V2 behaviours/defects:

- `shftasym.m` 8-argument default path: legacy defect reproduced.
- `shftasym.m` nonzero axial branch: undefined `Kre` defect reproduced.
- `shftasym.m` rotary contribution: legacy behaviour reproduced.
- `bearasym.m` type-4 reverse index: defect reproduced and preserved.
- `chr_asym.m` output-count-dependent `K1b` behaviour: reproduced.
- foundation bearing predicate tautology: reproduced.
- `runup.m` use of MATLAB/Octave `j`: runtime behaviour reproduced.

No legacy defect is silently corrected in the production compatibility path.

## Stage 1 closure rule

A Stage 1 delivery is accepted only when the exact PR head has all three workflows green:

1. **Stage 1 M7 Qualification** — G1, G2–G17 formal/regression coverage including Windows.
2. **G14 Book Problem Regression** — the independent 83-problem campaign.
3. **Stage 1 Final Qualification** — Phase 9/Python Core tests, 22 graphical examples, legacy probes, documentation, delivery ZIP and G18 clean-package qualification.

Historical milestone reports remain unchanged for traceability. The historical M7 run that masked an authority-verifier failure through a pipeline without `pipefail` is not used as G19 evidence; only the corrected fail-closed workflow is valid.
