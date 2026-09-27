# B19 — Nonzero Advanced-Bearing Mass Assembly

BASE_MAIN = e2a8b57003edf4b407ea089e92160ce86b30c35c
STATUS = AWAITING_SAME_HEAD_QUALIFICATION

## Scope

B19 promotes the already-supported CoefficientBearing M matrix into stationary
RotorStudio assembly without reinterpreting it as disk mass and without
discarding cross-coupled inertia.

The additive internal legacy row is bearing type 9:

`[9,node,Kxx,Kxy,Kyx,Kyy,Cxx,Cxy,Cyx,Cyy,Mxx,Mxy,Myx,Myy]`

Historical bearing types 1-8 and 20 are unchanged.

Zero-M advanced bearings continue to use the B12-qualified type-5 K/C bridge.
Only an evaluated nonzero M selects type 9.

## Qualified target

B19 covers stationary:

- global M/C/K assembly;
- modal/eigensystem;
- synchronous FRF;
- existing advanced-bearing critical-speed path through stationary modal solves.

Speed/frequency-dependent CoefficientBearing M is evaluated at the same
operating point as K/C.

B19 deliberately does not yet promote nonzero M into B18 run-up, coaxial,
rotating/asymmetric or general transient analysis. Those are subsequent blocks.

## Gate

The dedicated test compares the advanced-bearing path against an explicit
type-9 oracle for assembly, modal eigenvalues and FRF, including speed-dependent
M and off-diagonal Mxy/Myx.

`B19_NONZERO_ADVANCED_BEARING_MASS = PASS` only after same-head Linux and
Windows qualification.
