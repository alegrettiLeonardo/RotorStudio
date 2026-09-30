# A8 reconciliation and response-first qualification

This record supplements `ROSS_ANALYSIS_A8_CLEARANCE.md`; it does not rewrite the
historical implementation narrative or the immutable reference data. The final
exact-HEAD qualification matrix belongs in PR #33, not a post-qualification
repository commit. Technical qualification does not authorize automatic merge.

## Promoted baseline and preserved branch history

- Frozen ROSS: `6320eab9f890f1b3cc1710d508b446fe063ca68d`.
- Promoted A5 corrective main: `c2073acc0085900e72f0b17ad90cbf1090eec495`.
- Initial A8: `ad394e109fa356015b8ed183c6df246ef6efe586`.
- Initial merge-base: `03fef9b0da65c51b7ea3c9a14911cf7f83bcb015`.
- Initial divergence: 38 A8-only commits, 7 main-only commits.
- Reconciliation: `4a4af096d28fafd35e292c776558581471daeb30`, first parent old A8,
  second parent promoted main. A8's 37 changed paths and main's 24 corrective
  changed paths were disjoint. Exact corrective blobs were reused, with no
  semantic conflict resolution, reset, rebase, squash or force push.
- Main push runs `36650471310`, `36650471287`, `36650471257`, `36650471219`
  completed successfully before reconciliation.

## Demonstrated failures, not speculative rewrites

### Stale GUI test

Run `36691954937`, Ubuntu job `109810979243`, at reconciliation `4a4af096...`:
14/14 CTests passed; clearance had 1 failure and 14 passes. The newly published
GUI test accessed `AnalysisCase.params`, while the existing domain and dialog
use `parameters`. Only test accesses were corrected in `5507f296...`; no domain
alias or GUI workaround was added. Inheritance steps were also moved before A8
so a prior A8 failure could not hide unexecuted A5/A6/A7 gates.

### PR31-only preservation scope on additive A8

Run `36692365279`, Ubuntu job `109812291669`, at `5507f296...`: CTest 14/14;
UCS 63 passed and two preservation assertions failed. A whole-directory equality
against old A7 rejected the existing additive clearance sources/references.

Commit `f21556415f7e41ae325e338134f847eb491d0702` preserves every original
Fortran file and A0-A7 reference, admitting only the exact additive paths and
statuses from frozen snapshots. The pre-reconciliation CMake integration is
pinned separately. PR31 authority, UCS binding/product sentinel and LF rules are
pinned to promoted main; A8's existing golden directory is pinned to old A8.
Negative tests reject historical edits/deletions/renames/type changes and unknown
additions. All actual old/new UCS numerical assertions remain intact.

Run `36693113901` at `f2155641...`, Ubuntu `109814681105` and Windows
`109814680841`, passed all inheritance, existing A8, broad and bearing steps.
This permitted continuing the existing A8 audit; it was not final promotion.

### Demonstrated vector-marshalling defect

Test-only HEAD `7a49c66479034ce22ab2fc1da30d03fdd7732ef9` preserves the failure
before any production fix. Run `36694478618`, Ubuntu job `109819041723`:
14/14 CTests, UCS 74, A6 12 and A7 11 passed. The A8 suite then reported
**6 failed, 15 passed**.

Four tests supply positive-stride NumPy views containing the same logical
values as dense vectors. Valid allocated filler entries between selected values
make a contiguous-memory misread observable without an out-of-bounds access.
The old binding passed `np.asarray` views directly as raw ABI pointers, so node,
angle and clearance data could be interpreted incorrectly. For example, the
radial-clearance sentinel produced diameters `[0.0002,0.004,0.0005]` instead of
`[0.0002,0.0005,0.00024]` metres. Two rank-two arrays were also accepted despite
the vector contract.

The correction is confined to `clearance_backend.py`: check that the supplied
vectors are one-dimensional and create contiguous temporary arrays before
passing pointers. The same validation covers explicit-unbalance vectors. It does
not change equations, global `_ptr`, Fortran sources, ABI, unit conventions,
model persistence, interpolation, goldens or tolerances. The original six
regressions remain unchanged for the after comparison.

## Frozen authority and native source mapping

The runtime report from `validation/a8/qualify_clearance_intermediates.py`
records exact source-file names, start/end lines, SHA256 values and runtime
versions for the following frozen methods:

| Frozen ROSS authority | Existing native/product implementation |
|---|---|
| `Rotor.run_clearance_analysis` | `rd_clearance.f90:clearance_full`, thin `clearance_backend.execute` |
| `Rotor.api617_unbalance` | reused `rd_api617_unbalance:api617_full` |
| `Rotor.run_unbalance_response`, `run_forced_response` | reused `rd_forced_response:forced_response`; synchronous U forces |
| `ForcedResponseResults.data_magnitude`, `Orbit.calculate_amplitude` | native radial projection `2*abs(qx*cos(theta)+qy*sin(theta))` |
| `Orbit`, `_init_orbit` | native major semi-axis from the symmetric 2x2 orbit Gram matrix |
| `ClearanceResults.passed` | strict native `< 0.75*diametral_clearance` |
| `ClearanceResults.speed_at_max_response` | native first `maxloc`; existing zero-response comparison policy |

`rd_clearance_required_v1` and `rd_clearance_v1` remain the versioned entry
points. The size query bounds the declared problem and supplies the caller's
unbalance capacity. The full call validates model/axis/probe/clearance input,
finite values, node ranges, cap and unbalance capacity before solving. As with
an explicit-shape C/Fortran ABI, callers must allocate the documented buffers;
the API cannot discover the allocation size behind an arbitrary raw C pointer.
No explicit matrix inverse or Python fallback was added.

## Numerical contract retained

1. Sort/unique the supplied speed grid and insert both Nma and Nmc exactly.
2. Use explicit U when supplied, otherwise the existing qualified A7 placement.
3. Evaluate synchronous response with Omega=omega and qualified materialized
   bearing coefficients. Do not run Reynolds/THD/TEHD inside the sweep.
4. Project radial probes in metres peak-to-peak; Amax includes only Nma..Nmc.
5. `Avl = min(25.4,25.4*sqrt(12000/Nmc_rpm))*1e-6` metres peak-to-peak.
6. `Scc=Avl/Amax`; apply a cap only when explicitly supplied. None is not 6.
7. For every declared close-clearance point, `diametral=2*radial` and
   `response_pp=2*Scc*major_semi_axis`.
8. Pass only when the maximum over the full sweep is strictly below 75% of the
   diametral clearance. Equality fails.

The existing domain adaptation remains explicit: analysis-local one-based
radial probe nodes/angles and one positive minimum running radial clearance per
location. It is not an inference from unrelated housing/bearing geometry.
Only the previously declared single-shaft 4-DOF support scope is qualified.
This is numerical ROSS parity, not a claim of full normative API 617 compliance.

## Added qualification coverage

`test_clearance_independent.py` exercises the actual Fortran path for:

- Complex U scaling before clearance normalization; explicit nonzero phase.
- Orbit major/minor geometry checked independently with SVD and the native
  peak-to-peak identity; raw complex A3 data are used before magnitude reduction.
- A larger response outside the operating interval which must not set Amax.
- Avl below, at and above 12000 rpm, plus the high-speed branch.
- None-cap behavior above 6, explicit cap, absent automatic-mode metadata for U.
- A constructed exactly representable equality at 75%, then immediately
  distinguishable values on both sides. The decision check is exact, not allclose.
- Zero probe response and NaN/Inf rejection.
- Native sizing rejection and caller-capacity query.

The independent SVD and diagnostic reconstruction live only in validation/tests.

## Response-first parity and its boundary

The new read-only intermediate audit uses all eight existing immutable cases,
including map-backed support, automatic/conical placement, explicit U and speed
insertion. It compares real and imaginary x/y displacement from the shared
native A3 solver with the actual frozen ROSS response before probe projection,
absolute value, orbit reduction, scale normalization or clearance decisions.

Automatic modal placement may differ by a single global phase: node, U magnitude
and relative phases are checked first, and only that measured global phase is
aligned. Explicit-unbalance phase is not normalized away. The report archives
both raw and aligned complex arrays, force arrays, probe arrays, major/minor
axes and final clearance arrays in NPZ, with JSON differences and SHA256.

The A8 v1 ABI itself does **not** export its internal complex q array or minor
axis. The audit transparently exercises the unchanged A3 routine called by A8,
then gates the actual A8 scalar/array outputs. It is not an assertion that those
diagnostic arrays are new A8 ABI outputs.

Original per-quantity tolerances are imported unchanged from the existing A8
parity tests. The strict pass boundary is tested separately without tolerances.
The existing 1e-12 m non-observable argmax policy is retained: zero amplitudes
remain gated; only their physically meaningless argmax speed is not compared.

## Read-only, exact-HEAD reference reproduction

The existing authority workflow used a mutable branch checkout and could commit
new references when missing. The continuation makes it read-only and requires
the already-frozen authority, with exact event-HEAD checkout, separate candidate
output, raw-byte golden/source checks and uploaded candidate/environment evidence.

The historical golden metadata records NumPy 1.26.4 / SciPy 1.14.1 and is not
rewritten. Those old runtime pins are below the frozen ROSS package's declared
requirements (NumPy >=2.2 / SciPy >=1.15). The new reproduction and intermediate
audit install a dependency-consistent isolated ROSS environment and run pip check.
Agreement must still satisfy the existing frozen physical tolerances; changing
runtime is not permission to overwrite the reference or relax a comparison.

## Closing evidence and promotion

The native Linux/Windows workflow runs inherited A5/A6/A7 before A8 and records
separate JUnit reports, exact tested HEAD, A5 before/after evidence, independent
boundary JSON and intermediate numerical archives. It rejects empty collections,
failed tests and skipped tests in the declared native suites.

Final closure additionally requires the existing PR-triggered regression matrix,
GUI/persistence/exports and clean-extracted Linux/Windows frozen product gates on
the same final HEAD. Source-tree smoke is not a replacement for frozen execution.
CI warnings and the offscreen GUI scope must be retained in the final report.

Record the final exact-HEAD matrix in PR #33. Do not add a qualification-only
repository commit after closure. Do not automatically merge A8. B1 6-DOF element
matrices is the next milestone only after explicit A8 promotion; no faults here.
