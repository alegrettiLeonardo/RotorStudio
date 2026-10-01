# I10 — automatic legacy cases and guarded numerical readiness

I10 promotes the ST41 import from a review-only engineering sketch to
`LEGACY_NUMERIC_READY` for exactly two qualified expanded-support paths:

- `irdin_modal_sweep` — Campbell/modal sweep using I9 expanded modal solves;
- `irdin_synchronous_response` — synchronous unbalance/probe response using
  I9 expanded response solves.

Generic RotorStudio analysis kinds remain blocked for an imported project in
this readiness state. This prevents accidental execution through the ordinary
4-DOF grounded-bearing path, which would omit the imported support DOFs.

## Legacy speed-grid authority

The frozen migrated frontend at
`alegrettiLeonardo/frontend_rotordin@647d600bc1d32a05de62ee457942e00285b572e3`
demonstrates:

- `c_div` maps to native CPBSPD, an integer **number of Campbell points**;
- `d_div` maps to the synchronous-response **rpm increment**.

For ST41:

- Campbell: 0..3000 rpm, 25 points;
- response: 300..3000 rpm with 400 rpm increment, producing
  300, 700, 1100, 1500, 1900, 2300, 2700 rpm.

## Scope boundary

`LEGACY_NUMERIC_READY` is not an API 541 compliance claim. Critical-speed
classification, separation margins, API 541 analytical unbalance cases and
support-sensitivity reporting remain subsequent stages.
