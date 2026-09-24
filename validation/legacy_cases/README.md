# Minimal legacy-defect cases — Stage 1 final qualification

Pinned GNU Octave 7.1.0 now executes the minimal runtime probes against the preserved `reference/matlab_v2` authority. These probes characterize V2 behavior; they do not silently repair the authority.

| Item | Runtime evidence | Stage 1 treatment | Classification |
|---|---|---|---|
| `shftasym.m` default argument | 8-argument call fails with `AxialForce` undefined | compatibility layer does not invent a default for that exact V2 defect path | `LEGACY_DEFECT_RUNTIME_CONFIRMED` |
| `shftasym.m` axial branch | nonzero axial call fails with `Kre` undefined | production asymmetric axial-force branch is rejected explicitly | `LEGACY_DEFECT_RUNTIME_CONFIRMED` |
| `shftasym.m` rotary contribution | measured nonlinear rhoI scaling residual `0.457152` in probe | compatibility behavior retained where applicable | `LEGACY_BEHAVIOR_RUNTIME_CONFIRMED` |
| `bearasym.m` type 4 | observed `K1b(3,4)=-7`, `K1b(4,3)=0`, `K1b(2,1)=7` | reproduced exactly | `LEGACY_DEFECT_RUNTIME_CONFIRMED` |
| `chr_asym.m` output count | one-output and two-output paths differ; probe max eigenvalue delta `90.3488` | API preserves the two legacy paths | `LEGACY_OUTPUT_DEPENDENT_BEHAVIOR_RUNTIME_CONFIRMED` |
| `time_fdn.m` / `freq_fdn.m` bearing predicate | `type > 2 OR type < 9` evaluated true for every finite numeric probe type | preserved and documented | `LEGACY_DEFECT_RUNTIME_CONFIRMED` |
| `runup.m` `j` vs `jot` | unshadowed built-in `j` path executed successfully; probe returned 11 finite points | V2 forcing semantics retained | `LEGACY_BEHAVIOR_RUNTIME_CONFIRMED` |

The executable probe source is `validation/legacy_cases/run_octave_probes.m`. CI uploads the CSV evidence produced by that probe. No item above is used as a reason to relax formal numerical gates.
