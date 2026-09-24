# Minimal legacy-defect cases — Stage 1 final runtime characterization

The preserved `reference/matlab_v2` sources are the authority. The minimal cases below are executed with pinned GNU Octave 7.1.0 as a MATLAB-compatible runtime probe. They characterize V2 behavior; they do **not** silently repair authority code.

Runtime evidence is produced by `validation/legacy_cases/run_octave_probes.m`.

| Item | Runtime evidence | Stage 1 treatment | Classification |
|---|---|---|---|
| `shftasym.m` default argument | 8-argument call fails because `AxialForce` remains undefined | compatibility layer does not invent a default for the malformed V2 path | `LEGACY_DEFECT_RUNTIME_CONFIRMED` |
| `shftasym.m` axial branch | nonzero axial load fails because `Kre` is undefined | production asymmetric compatibility path rejects this unsupported branch explicitly | `LEGACY_DEFECT_RUNTIME_CONFIRMED` |
| `shftasym.m` rotary contribution | doubling `rhoI` does not double the rotary `Cs` contribution; probe residual is nonzero | V2 scaling behavior preserved where applicable | `LEGACY_BEHAVIOR_RUNTIME_CONFIRMED` |
| `bearasym.m` type 4 | runtime shows `K1b(3,4)=-7`, `K1b(4,3)=0`, and overwrite at `K1b(2,1)=7` in the probe | reproduced exactly and regression-tested | `LEGACY_DEFECT_RUNTIME_CONFIRMED` |
| `chr_asym.m` output count | one-output and two-output paths produce different eigenvalues because the equations include/omit `K1b` | API preserves the output-dependent path | `LEGACY_OUTPUT_DEPENDENT_BEHAVIOR_RUNTIME_CONFIRMED` |
| `time_fdn.m` / `freq_fdn.m` predicate | `type > 2 OR type < 9` evaluates true for all finite numeric probe bearing types | predicate documented and preserved | `LEGACY_DEFECT_RUNTIME_CONFIRMED` |
| `runup.m` `j` vs `jot` | unshadowed Octave built-in `j` path executes and returns finite transient data | V2 forcing semantics preserved | `LEGACY_BEHAVIOR_RUNTIME_CONFIRMED` |

The runtime probe gate is PASS only when all seven cases execute with the expected V2 characterization. The probe intentionally distinguishes executable legacy behavior from defects that raise an authority-runtime error.
