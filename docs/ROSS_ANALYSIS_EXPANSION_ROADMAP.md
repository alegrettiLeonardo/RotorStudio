# Delivery gates

1. A0: immutable frozen-source references, integrity tests and two-platform CI.
2. A1: native Static; numerical parity before GUI; complete integration and frozen Linux/Windows.
3. A2 → A3 → A4 → A5 → A6 → A7 → A8: General FRF, forced, transient, UCS, Level 1, unbalance, clearance.
4. B1 → B2 → B3: 6-DOF matrices, assembly/modal/Campbell, axial/torsional workflows.
5. C: misalignment, rubbing, crack variants, linear periodic harmonic balance.
6. D: stochastic deterministic-solver layer, two-rotor linear gears, TVMS, backlash.
7. E: magnetic bearings/controllers, then sensitivity.

Each delivery uses a separate PR. No automatic advancement past failing or
missing gates. No modification to legacy physics merely to accommodate parity.
No Python production solver or fallback. GUI availability requires numerical and
platform qualification at the same source commit.

A0–A6 are promoted and preserved.

Promoted checkpoints:

- A5 UCS qualified HEAD `fa0827e2233620d68a422edf1dc99f6471dc45f3`;
  promoted main `799dd97583425915a2c9e5ec4b823468780e4146`.
- A6 Level 1 qualified HEAD `e7906b6329bab06d6a5a7ea53170485a31869679`;
  promoted main `bae1adf745ffd66742a14c956dbd090524f5737e`.

Current campaign stage: **A7 API 617 unbalance placement** on
`feature/ross-analysis-a7-api617-unbalance`, branched from the exact A6
promoted main. A7 implementation and immutable frozen-ROSS authority are in
place; promotion remains contingent on exact-head Linux/Windows parity,
preservation/regression and clean frozen application gates.

A8 close-clearance analysis remains blocked until A7 is promoted. B1 and later
6-DOF platform work remain blocked until the A-series reaches its planned
boundary.
