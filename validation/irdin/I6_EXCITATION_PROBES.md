# I6 — iRdin unbalance and response probes

## Scope

I6 materializes only the semantic contract already frozen in
`SEMANTIC_CONTRACT.md`:

- `[Desbal]`: position [mm], phase [deg], unbalance [g.mm];
- `[Respo]`: position [mm], coordinate 1=X or 2=legacy Z/domain Y,
  orientation [deg].

The native synchronous-response solver remains unchanged. A legacy mass
unbalance becomes existing `Force(1,(node,U_kg_m,phase_rad))`; the Fortran
response path continues to apply `U*omega^2`.

## Exact station policy

Positive bearing, unbalance and response positions are inserted as exact FE
stations before their domain objects are built. This avoids nearest-node
silence. Negative response positions use a historical support-reference
convention that is not required by ST41 and remains fail-closed.

## ST41 sentinels

- unbalance positions: 1370.9 mm and 3045.9 mm;
- source magnitude: 110175.3 g.mm each;
- domain magnitude: 0.1101753 kg.m each;
- source phase: 0 deg;
- probes: X/Z at 550 mm and X/Z at 3977 mm;
- probe orientations: 0 deg.

## Readiness

I6 sets the component gates:

- `unbalance = PASS_I6_LEGACY_UNBALANCE`;
- `probes = PASS_I6_RESPONSE_PROBES`.

It intentionally does **not** make ST41 numerically ready. Distributed-mass
native materialization and the globally coupled support model remain blockers.
