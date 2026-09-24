# G14 baseline policy

G14 does not invent a new numerical authority.

For every Octave-compatible problem, the exact supplied `Problem_*.m` source is
executed twice with pinned GNU Octave 7.1.0. If the problem calls
`Rotor_Software_v2`, the frozen V2 source is placed on the Octave path.
All such executions are reported as **Octave probes**, never as MATLAB runs.

`A_SOLVER` cases compare selected V2 outputs with the existing production path:

`AnalysisService -> SolverFacade -> ctypes -> Fortran`.

`A_WITH_ANALYTIC_ORACLE` cases retain the book equations as an independent
oracle and compare the exact corresponding product quantity with the same
Fortran-backed path.

`B_ANALYTICAL` cases remain validation-only. They do not add rotor-solver
physics to `drm_core`. Their deterministic numeric probe is compared between
independent Octave 7.1.0 runs using the strictest already-frozen relative
threshold (1e-12).

`Problem_03_12.m` is the only planned Octave 7.1.0 N/A: the original MATLAB
identifier `do` is an Octave keyword and causes a parser error before
execution. G14 does not edit or silently repair the authority script. A
validation-only source-derived closed-form runner evaluates its published
equations and is checked with the frozen frequency threshold (1e-8).
