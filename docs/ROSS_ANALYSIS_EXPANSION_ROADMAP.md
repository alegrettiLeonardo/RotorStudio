# Incremental Fortran analysis expansion

This is a dependency plan, not a feature availability declaration. Production
physics stays in Fortran 2018; Python owns orchestration/domain/units/results.

```mermaid
flowchart TD
  A0["A0 Authority and parity infrastructure"] --> A1["A1 Static"]
  A1 --> A2["A2 General FRF"]
  A2 --> A3["A3 Forced response"]
  A3 --> A4["A4 General time response"]
  A4 --> A5["A5 UCS"]
  A5 --> A6["A6 Level1"]
  A6 --> A7["A7 API617 unbalance"]
  A1 --> A7
  A7 --> A8["A8 Clearance"]
  A3 --> A8
  A8 --> B["B1/B2 6-DOF elements and system"]
  B --> C["C Faults and harmonic balance"]
  A4 --> C
  C --> D["D Stochastic and multirotor"]
  D --> E["E AMB and sensitivity"]
```

Arrows include mandatory delivery order as well as numerical prerequisites.
Within D: deterministic samples -> two-rotor constant mesh -> TVMS -> backlash.
Within E: controller/actuator/sensor states -> coupled AMB response -> sensitivity.

Current implementation scope is A0. A1 awaits A0 qualification and reviewed
frozen reference data. No automatic advance to A2. Each feature receives its
own PR, provenance, native/ABI/integration/golden/physics tests, release gates
and explicit PASS, FAIL or BLOCKED verdict. No changing prior production
physics, no Python numerical fallback, and no automatic golden refresh.

See ROSS_ANALYSIS_EXPANSION_AUTHORITY.md for actual inventories and A0/A1
acceptance criteria. Later phases retain the user-requested gate sequence;
their source details must be audited before implementation rather than assumed.
