# Known legacy issues

The migration distinguishes legacy behaviour from defects and documentation mismatches. No item is silently corrected.

| Area | V2 observation | Stage 1 treatment |
|---|---|---|
| `shftasym.m` default | 9-input function tests `nargin < 8` | runtime probe; compatibility path does not invent a missing axial argument |
| `shftasym.m` axial force | writes to undefined `Kre` | runtime probe; nonzero asymmetric axial load rejected rather than silently repaired |
| `shftasym.m` rotary term | `Ms` is scaled before `Cs = rhoI*Ms/(15*L)` | preserved in compatibility translation |
| `bearasym.m` type 4 | second reverse term overwrites `K1b1(2,1)`; `K1b1(4,3)` stays zero | preserved and numerically asserted |
| `chr_asym.m` | one-output and two-output paths differ in `K1b` use | explicit output-dependent compatibility path |
| `freq_fdn.m` / `time_fdn.m` | bearing predicate `type > 2 OR type < 9` is a tautology for finite numeric types | documented/preserved |
| `runup.m` | mixes explicit `jot` with builtin `j` | pinned-Octave runtime probe and formal transient comparison |
| Manual V1 transient reduction | manual states Guyan; V2 calls `eig(K,M)` and truncates modes | `DOCUMENTATION_MISMATCH`; V2 modal truncation preserved |

The executable probe is `validation/legacy_cases/octave_runtime_probe.m`. The final qualification report records the observed GNU Octave 7.1.0 results; until that run is green, this document does not promote a runtime observation to PASS by assertion alone.
