# G14 — 83 DRM book-problem regression

G14 is isolated from the remaining Stage-1 backlog until the gate closes.

The exact supplied `DRM_problem_scripts.zip` is reconstructed losslessly by
`materialize_archive.py`, verified against SHA256
`8b5db23fa57bc5e41f68ed9e25ab8f1f1a72e4a24b9e11af38dccdd4098501d1`,
and materialized only under `reference/drm_problem_scripts`.

## Semantic classification

The classification is based on source review of all 83 scripts, not only on
grep/direct-call detection.

- `A_SOLVER`: **15** cases. The original script calls a V2 numerical solver
  path. Product comparison is forced through
  `AnalysisService -> SolverFacade -> ctypes -> Fortran`.
- `A_WITH_ANALYTIC_ORACLE`: **5** cases. The book problem manually computes
  an exact independent oracle for production beam/bearing physics; the product
  side still uses the existing Fortran path.
- `B_ANALYTICAL`: **63** cases. Educational/analytical cases remain under
  validation and do not add a second rotor solver to `drm_core`.

The executable-code scan finds 17 scripts with direct V2 calls: 15 numerical
solver cases plus 2 post-only `whirl` calls. `Problem_07_02.m` mentions
`whirl()` only in a comment and is deliberately not counted.

## Authority and baselines

Every compatible original problem is executed twice with pinned GNU Octave
7.1.0. These are reported as **Octave probes**, not MATLAB executions. When an
original problem calls V2, the frozen `reference/matlab_v2` authority is on
the path.

`Problem_03_12.m` is the only planned Octave N/A. Its original MATLAB
variable `do` is an Octave 7.1.0 keyword, so the unmodified script cannot be
parsed. The harness does not silently edit the source. Because this is a
`B_ANALYTICAL` case with no V2 solver call, a validation-only source-derived
closed-form runner provides the numeric regression and no Octave-baseline
claim is made.

Like-for-like product comparisons reuse the frozen G5-G12 thresholds. G14 does
not introduce a looser physics tolerance.

## Required evidence

The dedicated `g14-book-problems.yml` workflow emits:

- `problem_inventory.json`
- `problem_inventory.csv`
- `BOOK_PROBLEM_INVENTORY.md`
- `G14_BOOK_PROBLEM_REGRESSION.json`
- `G14_BOOK_PROBLEM_REGRESSION.csv`
- `G14_BOOK_PROBLEM_REGRESSION.md`
- `COMMANDS_EXECUTED_G14.md`
- `G14_ENVIRONMENT.json`
- both Octave runtime/probe directories
- source/archive integrity evidence

G14 is PASS only when all 83 cases have a deterministic validated numeric
regression, all 20 product comparisons pass, there are no unexpected BLOCKED
cases, and the A/hybrid adapters contain no alternate Python solver.
