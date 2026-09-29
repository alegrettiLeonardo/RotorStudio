# A5 — Undamped Critical Speed Map (UCS)

## Campaign boundary

A4 qualified HEAD: `ec648888800dcc13f337dff4d2a7ffb132d9e374`.
A4 merge / promoted baseline: `6aaf2d18b96bd3adc5fe99c58febd997a7b61559`.
A5 branch: `feature/ross-analysis-a5-ucs`, created from that exact promoted baseline.
Frozen ROSS authority: `petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d`.

A0-A4 are preservation targets. A5 is additive. A6 Level 1 and all fault work remain blocked until A5 promotion.

## Authority audit before production code

The following frozen ROSS sources are the A5 authority and are hashed again in
`validation/ross_parity/ucs/authority.json` when immutable goldens are created:

- `ross/rotor_assembly.py`: `Rotor.run_ucs`, `Rotor.run_modal`, `Rotor._eigen`,
  `Rotor.A`, `Rotor.M(..., synchronous=...)`, `Rotor._remove_housing_bearings`.
- `ross/utils.py`: `convert_6dof_to_4dof`, `intersection`.
- `ross/results.py`: `UCSResults`.
- `ross/bearing_seal_element.py`: `BearingElement` coefficient interpolation.
- `ross/tests/test_rotor_assembly.py`: UCS reference tests, including ordinary and
  Rouch synchronous maps and the explicit 30-point bearing-speed-range contract.

### Frozen semantic mapping

1. `stiffness_range=(start, stop)` is a pair of base-10 exponents and is evaluated
   by `np.logspace(start, stop, num=num)`. It is never a pair of linear N/m values.
2. If no range is supplied, frozen ROSS derives `(p-3,p+3)` from the first bearing
   at `rated_w`, when `rated_w` exists, otherwise it uses `(6,11)`.
3. At every stiffness point ROSS creates an auxiliary rotor: proportional shaft
   damping is zeroed; seals are excluded; remaining supports are replaced by
   isotropic `kxx=kyy=k, cxx=cyy=0`; the authority is converted to 4-DOF; map
   modes are solved at speed zero.
4. For `num_modes=16`, the map result has four branches:
   `num_modes // 2 // 2`. Each column is based on `modal.wn[::2]`, trimmed by
   the authority if its final length is one element too large.
5. The physical bearing curve is the first original non-seal bearing, not one of
   the temporary isotropic supports.
6. Explicit `bearing_speed_range=(start, stop)` becomes exactly 30 linearly-spaced
   points. With no explicit range, ROSS uses the bearing speed axis, otherwise the
   bearing frequency axis, otherwise ten points spanning the map natural-frequency
   range with a 10% lower/upper margin based on `rotor_wn.min()`.
7. A one-argument 2-D coefficient lookup follows the frozen synchronous diagonal:
   speed and excitation frequency are evaluated at the same scalar/vector value.
8. `np.array_equal(bearing0.kxx, bearing0.kyy)` selects only Kxx when exactly
   equal; otherwise both Kxx and Kyy intersection families are processed.
9. Intersection ordering is: modal branch, then coefficient family, then
   intersections returned by `ross.utils.intersection`. No post-sort is part of
   the authority.
10. Every critical intersection is re-solved with isotropic `kcrit` supports at
    the nonzero `speedcrit`; this is distinct from the zero-speed map solve.
11. `synchronous=True` selects Rouch's formulation. Frozen ROSS folds shaft and
    disk gyroscopic terms into `M(..., synchronous=True)`; it is not a bearing
    coefficient lookup option.

## RotorStudio domain audit

The current `RotorModel` has no unambiguous `rated_w`, rated-speed, or equivalent
operating-speed property. A5 therefore **requires an explicit stiffness exponent
range in its initial production scope**. Omitting it must fail closed; RotorStudio
will not invent a rated speed or silently fall back to a heuristic.

The current generic domain also has no qualified generic `PointMass` element and
no ROSS-style housing/link topology. Initial A5 scope is therefore:

- single shaft line;
- qualified 4-DOF shaft/disk model;
- non-linked radial supports;
- no generic point masses;
- seals excluded from the temporary UCS rotor;
- explicit stiffness exponent range;
- constant or qualified coefficient/map-backed bearing curves.

Unsupported linked/housing or PointMass configurations fail closed rather than
being converted into a different physical model.

## Existing native assets and preservation

The existing Fortran core already provides shaft/disk assembly, gyroscopic matrices,
LAPACK eigensolutions, and legacy critical-speed workflows. These are reusable only
where matrix parity is demonstrated. `rd_critical_speed.f90` is not treated as UCS
and its semantics will not be changed.

A5 production is implemented additively in `rd_ucs.f90`,
`rd_intersections.f90`, `rd_rouch.f90` and `rd_ucs_c_api.f90`.  The
versioned native surface is `rd_ucs_required_v1`, `rd_ucs_map_v1`,
`rd_ucs_matrix_v1` and `rd_ucs_v1`; the caller queries result sizes before
allocating variable intersection buffers.  No A1-A4 ABI is changed.

## Immutable authority policy

`validation/ross_parity/generate_ucs_reference.py` may create
`validation/ross_parity/ucs/` only when that directory does not exist. The freeze
workflow refuses to overwrite an existing authority. Later qualification regenerates
a candidate from the same ROSS SHA and compares it to these immutable files; it does
not rewrite them.

The authority set covers constant isotropic/anisotropic bearings, speed-axis,
frequency-axis and two-dimensional coefficient tables, explicit bearing range,
the explicit logspace gate, no-intersection behavior, synthetic intersection
sentinels, the ROSS no-rated-speed default, and a Rouch synchronous authority case.

## Status

Authority audit: complete.
Immutable A5 golden freeze: complete.
Frozen-authority candidate reproduction: required on every later A5 head.
Production Fortran/ABI/thin binding/AnalysisService/GUI/persistence/export implementation: complete for the declared scope.
Final exact-head Linux/Windows, frozen executable and full PR regression closure: pending.
No PASS verdict is recorded in this source document before those exact-head gates complete.
A6: `BLOCKED_BY_A5_PROMOTION`.


## Implemented product contract

Production physics remains Fortran 2018. The UCS map construction, temporary
undamped system, Rouch mass fold, stiffness sweep, curve intersections and
critical-point modal solves are native. Python is limited to scope validation,
marshaling, the already-qualified native bearing coefficient provider, result
objects, units, plotting and persistence.

The GUI exposes a separate **UCS / Undamped Critical Speed Map** analysis.
Stiffness inputs are explicitly labeled as exponents (for example, 6 means
10^6 N/m). The result workspace uses logarithmic stiffness and speed axes and
shows rotor branches, original-bearing Kxx/Kyy curves, intersections and a
selected critical-point numeric summary. The current A5 ABI does not export
critical eigenvectors, so the GUI does not invent a mode-shape result.

The product qualification path is:
`GUI -> AnalysisCase("ucs") -> SolverJobManager -> AnalysisService ->
rd_ucs_v1 -> Fortran -> UCSResult -> plot -> CSV/NPZ/report/PNG/SVG/PDF ->
save -> close -> reopen -> recompute -> exact arrays/hash -> staleness`.
The same smoke is required in the clean frozen Linux and Windows application.

CSV exports UCS branches in long form and writes a separate intersection table.
NPZ contains the complete numeric UCS arrays and metadata.

## Intersection provenance

`fortran/src/rd_intersections.f90` is derived from frozen
`ross.utils.intersection()`, whose source documents derivation from the
Sukhbinder Singh intersection project. The MIT notice is preserved in the
Fortran source and in `NOTICE-A5-INTERSECTION-MIT.txt`. Generation order is
modal branch -> coefficient family -> returned segment intersection. There is
no post-sort or undocumented de-duplication.

## Fixed A5 numerical gates

A5 does not copy A4 tolerances. The pre-closure tolerances are M/G
rtol=2e-12, atol=2e-12; K rtol=2e-12, atol=1e-6; production modal wn
rtol=2e-8, atol=2e-6 rad/s; original bearing curves rtol=2e-10,
atol=1e-5 N/m; intersection stiffness rtol=2e-7, atol=2e-2 N/m;
intersection speed rtol=2e-7, atol=2e-5 rad/s; and critical modal wn
rtol=3e-8, atol=3e-6 rad/s. Independent gates require exact C_UCS=0,
scaled generalized-eigen residual <=1e-9 and scaled intersection-polyline
residual <=2e-7.

The dedicated `logspace_gate` is an exponent/grid semantic sentinel. Its
pass/fail quantity is the stiffness grid itself, including the exact frozen
ROSS grid and [1e6,1e7,1e8,1e9,1e10] expectation. Full modal branch parity is
separately required by the constant, anisotropic, coefficient-map and Rouch
production cases, avoiding a second tolerance decision inside the logspace-only
sentinel.

## Frozen source hashes

The immutable A5 authority records these source hashes:

- rotor_assembly.py: `c5e6562d092426ffdb44641a1fb2092c6e5df8e3e44be437749b3711f7633c09`
- utils.py: `08708dc134682b40dcb8259527cdd9586e9f3eac26c0b510eda29355e05eb8d9`
- results.py: `0d53a92700228c074145e35e49e31e6f8550f4199efc1e9470b53ca5c5477cc3`
- bearing_seal_element.py: `4c1e39b0cfdb4a64dd0992df686f6771e3245fc74c2dc1fca95b684328cc5942`
- tests/test_rotor_assembly.py: `39f542a7d7fb4aa7fbd8a0966206c7280c0204e19dde1eacf3a47acf77bc5df4`

One additional frozen semantic detail is qualified explicitly: a
`synchronous=True` UCS map uses the Rouch mass formulation and the frozen
eigenvalue admissibility/order rules, while critical-point modal re-solves use
the standard non-Rouch modal path at nonzero critical speed, exactly as
`Rotor.run_ucs()` does.
