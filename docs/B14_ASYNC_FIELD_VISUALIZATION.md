# B14 — Async Bearing Jobs and Native Field Visualization

BASE_HEAD = fe0d6c4b906c31a63bb569adfc07b12ddbdfde24
B12_PHYSICS_AUTHORITY = petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d
STATUS = AWAITING_SAME_HEAD_QUALIFICATION

## Scope

B14 productizes the B12-qualified PlainJournal and TiltingPad native providers for
explicit Bearing Performance evaluation without blocking the Qt GUI thread.
The B12 Reynolds, equilibrium, THD/TEHD, perturbation, condensation equations,
sign conventions and tolerances remain the authority path.

## Architecture

`BearingJobManager` serializes heavy native bearing solves to one worker.  A
`QTimer` polls an additive native job-control ABI; no arbitrary Python callback
enters Fortran.  Native cancellation is cooperative at bounded solver-safe
locations and returns `RB_ERR_CANCELLED`.  A cancelled job never publishes
partial coefficient or field data.

The additive field ABI returns the solved pressure, film temperature, film
thickness and pad deformation arrays.  It also returns pad loads and the Python
provider supplies deterministic theta/axial/pad coordinates from the same
validated immutable bearing input.  Film thickness is copied from the native
hydrodynamic state and is not reconstructed in the GUI.

Bearing Performance provides Summary, Dynamic Coefficients, Pressure,
Temperature, Film Thickness, Deformation, Pads and Convergence views.  A request
carries an immutable selection key so a solve started for bearing A cannot paint
its result onto a subsequently selected bearing B.

## ABI compatibility

The B12 packed coefficient and field symbols remain exported.  B14 adds:
- `rb_job_reset_c`
- `rb_job_request_cancel_c`
- `rb_job_progress_c`
- `rb_plain_journal_multiphysics_fields_v2_pack_c`
- `rb_tilting_pad_multiphysics_fields_v2_pack_c`

## Qualification matrix

Source gates exercise real native fields, cooperative cancellation, progress,
no-partial-publish behavior, Qt event-loop responsiveness, failure propagation,
selection identity and safe shutdown.  The B12 advanced-bearing and frozen ROSS
parity suites remain mandatory regressions.  The clean frozen application must
run the B14 worker against the packaged `drmbearings`, render all field tabs
and write `B14_FROZEN_FIELDS.json`.

## Known exclusions

B14 does not add operating-point maps/cache (B16), matched-whirl rotor analysis
(B17), synchronous map-backed run-up (B18), general transient advanced bearings,
coaxial/rotating advanced bearings, ThrustPad rotor integration or nonzero
bearing-mass assembly.

The status above is intentionally not changed to PASS until the exact commit
containing this document has completed the dedicated Linux/Windows source gates
and Linux/Windows clean-frozen smoke.  CI evidence, not this prose, is the
qualification authority.
