# B15 — iRdin / Cryostar Coefficient-Table Import

BASE_HEAD = 111320fbfa80dbbcba8754dbf5bd09d9c4a8ceec
B14_GATE = B14_ASYNC_FIELD_VISUALIZATION PASS at workflow run 36247948328
STATUS = AWAITING_SAME_HEAD_QUALIFICATION

## Scope

B15 converts validated inline historical iRdin `TABLE§...` bearing records into
typed `CoefficientBearing` objects. The intermediate `ImportedBearingTable`
keeps the source speed axis in rpm and the eight K/C columns in source order.

The numerical conversion is deliberately narrow:

- rpm -> rad/s;
- K and C values are copied without scaling;
- Kxy/Kyx and Cxy/Cyx signs are copied without sign correction;
- M remains zero because the source format contains no bearing-mass columns;
- imported tables use the existing qualified `linear` or `pchip` interpolation.

## Fail-closed source contract

The parser rejects empty tables, invalid column counts/header names, NaN/Inf,
duplicate or non-increasing rpm axes, invalid nodes, unknown units, ambiguous
X/Y coordinates and ambiguous cross-coupling conventions.

For the iRdin/VB6 source adapter the explicit contract is:

- speed: rpm;
- stiffness: N/m;
- damping: N*s/m;
- coordinate convention: X/Y;
- cross-coupling: force-row/displacement-column.

## Exact bearing stations

Historical bearing positions need not coincide with section boundaries. B15
inserts exact FE stations at those physical axial locations and splits the
underlying constant/tapered shaft segment without changing its geometry or
material interpolation. No nearest-node snapping is used.

## Granular numerical blockers

Successfully mapped inline bearing tables no longer contribute a global
"bearing coefficient table unmapped" blocker. Other unsupported historical
entities remain independently blocked, including distributed mass/package,
flexible-support and concentrated-mass records.

The real Cryostar fixture therefore contains two real `CoefficientBearing`
objects while remaining `BLOCKED_FOR_NUMERICAL_ANALYSIS` because its
distributed mass/package records are still unmapped.

## Qualification

The dedicated B15 workflow validates Linux and Windows with the real Cryostar
fixture, table-point parity at near machine precision, linear/pchip midpoint
evaluation, save/reopen typed persistence, malformed-input rejection and
granular blocker preservation. B12/B14 regression gates remain mandatory.

The status above is changed only after same-HEAD CI evidence is complete.
