# B20 — Coaxial Advanced Bearings

BASE_B19 = e5311ad3168d3906e2cba6a6a1f5c0f626d4961d
STATUS = AWAITING_SAME_HEAD_QUALIFICATION

## Scope

B20 promotes advanced bearings into the existing V2 coaxial solver while
preserving its reference-speed convention.

For a coaxial solve at reference speed Omega_ref:

- advanced K/C/M are evaluated at (Omega_ref, omega=Omega_ref);
- individual RotorDefinition.speed_factor values remain in the existing native
  relative gyro and excitation-speed equations;
- no bearing operating point is silently multiplied by a rotor speed factor.

The additive B19 type-9 bridge carries nonzero 2x2 translational M into coaxial
assembly. Zero-M advanced bearings keep the B12 type-5 path.

## Analyses

Qualified target:

- coaxial modal/eigensystem;
- coaxial synchronous unbalance response over a speed sweep;
- legacy type-20 inter-rotor coupling unchanged.

Speed-dependent advanced bearings are re-evaluated independently at every
reference-speed point in a coaxial FRF sweep.

## Gate

B20 compares advanced-bearing modal roots and every FRF speed point against an
explicit operating-point legacy type-5/type-9 oracle while retaining the
existing source-oracle coaxial regression.

`B20_COAXIAL_ADVANCED_BEARINGS = PASS` only after same-head Linux/Windows
qualification.
