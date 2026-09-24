# Known legacy issues

The migration distinguishes legacy behaviour from defects and documentation mismatches. No item is silently corrected.

| Area | V2 observation | Stage 1 treatment | GNU Octave 7.1.0 runtime probe |
|---|---|---|---|
| `shftasym.m` default | 9-input function tests `nargin < 8` | compatibility path does not invent a missing axial argument | **LEGACY_DEFECT_RUNTIME_CONFIRMED** — 8-argument call reaches undefined `AxialForce` |
| `shftasym.m` axial force | writes to undefined `Kre` | nonzero asymmetric axial load is rejected rather than silently repaired | **LEGACY_DEFECT_RUNTIME_CONFIRMED** — undefined `Kre` reproduced |
| `shftasym.m` rotary term | `Ms` is scaled before `Cs = rhoI*Ms/(15*L)` | preserved in compatibility translation | **LEGACY_BEHAVIOR_RUNTIME_CONFIRMED** |
| `bearasym.m` type 4 | reverse term overwrites `K1b1(2,1)`; `K1b1(4,3)` remains zero | preserved and numerically asserted | **LEGACY_DEFECT_RUNTIME_CONFIRMED_AND_PRESERVED** |
| `chr_asym.m` | one-output and two-output paths differ in `K1b` use | explicit output-dependent compatibility path | **LEGACY_OUTPUT_DEPENDENT_BEHAVIOR_RUNTIME_CONFIRMED** |
| `freq_fdn.m` / `time_fdn.m` | bearing predicate `type > 2 OR type < 9` is true for every finite numeric type | documented/preserved | **LEGACY_DEFECT_RUNTIME_CONFIRMED** |
| `runup.m` | mixes explicit `jot` with builtin `j` | behaviour preserved and formally compared | **LEGACY_BEHAVIOR_RUNTIME_CONFIRMED** |
| Manual V1 transient reduction | manual states Guyan; V2 calls `eig(K,M)` and truncates modes | `DOCUMENTATION_MISMATCH`; V2 modal truncation preserved | not a runtime defect; formal transient comparison PASS |

The executable probe is `validation/legacy_cases/octave_runtime_probe.m`. The final Stage 1 qualification requires its aggregate `overall=PASS`.
