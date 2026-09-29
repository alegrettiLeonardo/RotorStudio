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

A5 production work will use new additive modules and a versioned ABI. Planned
boundaries are `rd_ucs.f90`, `rd_intersections.f90`, and, if required for exact
Rouch parity, `rd_rouch.f90` or equivalent.

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
Immutable A5 golden freeze: pending the one-time authority workflow.
Production A5 implementation: not started at this commit.
A6: `BLOCKED_BY_A5_PROMOTION`.
