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

A0_ROSS_PARITY_INFRASTRUCTURE = PASS at f07dc86 (see
ROSS_ANALYSIS_A0_QUALIFICATION.md). Requalify the documentation closure HEAD,
promote A0, then branch A1 from main. No A1 code belongs in PR #22.
A0's static golden scope is deliberately narrower than full future A1 scope.
