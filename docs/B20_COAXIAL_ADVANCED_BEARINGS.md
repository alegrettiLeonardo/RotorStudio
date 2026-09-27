# B20 — Coaxial Advanced Bearings

BASE_HEAD = c5cb86ab03b73a18ee5ea4c410231fc635e39d55
B19_GATE = B19_NONZERO_ADVANCED_BEARING_MASS PASS
STATUS = AWAITING_SAME_HEAD_QUALIFICATION

## Contract

B20 promotes advanced bearings into the existing qualified coaxial solver without
changing Rotor_Software_v2 coaxial rotor-speed semantics.

The base-flow bearing speed is the **reference rotor speed**, matching the
historical V2 rule already recorded by RotorStudio. The initial B20 coefficient
policy is deliberately:

`COAXIAL_REFERENCE_SPEED_SYNCHRONOUS`

so advanced bearing K/C/M are evaluated at
`(Omega_ref, omega=Omega_ref)`.

This avoids silently substituting a local-rotor whirl-frequency convention that
the legacy coaxial source did not define.

## Assembly

The existing Fortran coaxial solver already assembles `M0+Mb`, `C0+Cb` and
`K0+Kb`, including B19 internal type-9 nonzero M. No coaxial Fortran equation
is changed.

Modal analysis materializes the advanced bearing once at the requested reference
speed. Multi-point coaxial FRF re-materializes every advanced bearing at each
reference speed before invoking the existing one-point native coaxial response.

Type-20 inter-rotor links remain the historical coupling mechanism and are
unchanged.

## Qualified boundary

The B20 gate covers:

- 2-D CoefficientBearing K/C/M;
- B19 nonzero bearing M in coaxial modal and FRF;
- reference-speed re-evaluation across a sweep;
- native PlainJournal physical-provider integration at a synchronous point;
- preservation of the existing V2 coaxial source-oracle tests.

A future local-rotor/excitation-frequency coefficient policy must be explicit and
separately qualified. B20 does not infer it.

Rotating/asymmetric advanced bearings remain B21 scope.
