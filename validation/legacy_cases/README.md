# Minimal legacy-defect cases — Stage 1 M3

These cases are anchored to the preserved `reference/matlab_v2` source. MATLAB/Octave is not available in the qualification environment, so **runtime behavior in MATLAB remains BLOCKED**. Static source evidence and new-implementation compatibility tests do not replace that gate.

| Item | Source evidence | M3 treatment | Classification at M3 |
|---|---|---|---|
| `shftasym.m` default argument | function has 9 inputs but uses `if nargin < 8` | nonzero asymmetric axial load is rejected explicitly; no invented `Kre` | `LEGACY_DEFECT_STATIC_CONFIRMED`, MATLAB runtime `BLOCKED` |
| `shftasym.m` axial branch | `Kre(...) = Kre(...) + ...` without initialization in the function | branch not silently repaired | `LEGACY_DEFECT_STATIC_CONFIRMED`, MATLAB runtime `BLOCKED` |
| `shftasym.m` rotary contribution | `Ms` is scaled, then `Cs = rhoI*Ms/(15*L)` | reproduced exactly in compatibility path | `LEGACY_BEHAVIOR_PRESERVED` |
| `bearasym.m` type 4 | writes rotational reverse term into `K1b1(2,1)` and never writes `K1b1(4,3)` | reproduced exactly and asserted numerically | `LEGACY_DEFECT_STATIC_CONFIRMED_AND_PRESERVED` |
| `chr_asym.m` | `nargout==1` includes `K1b`; `nargout==2` omits it | API exposes `want_vectors` and preserves the two paths | `LEGACY_OUTPUT_DEPENDENT_BEHAVIOR_PRESERVED` |
| `time_fdn.m` / `freq_fdn.m` | `type > 2 OR type < 9` is true for every finite numeric type | documented only; transient/foundation migration still deferred | `LEGACY_DEFECT_STATIC_CONFIRMED`, runtime `BLOCKED` |
| `runup.m` | defines `jot` but also uses MATLAB symbol `j` | documented only; run-up migration deferred | `LEGACY_BEHAVIOR_RISK`, runtime `BLOCKED` |

No item above is used to claim MATLAB numerical equivalence.
