# B19 — Nonzero Advanced-Bearing Mass

BASE_MAIN = e2a8b57003edf4b407ea089e92160ce86b30c35c
ROSS_AUTHORITY = petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d
STATUS = AWAITING_SAME_HEAD_QUALIFICATION

## Scope

B19 promotes the already persisted/evaluated 2x2 translational advanced-bearing
mass matrix M into the stationary 4-DOF rotor assembly.

The equation remains:

`[M_rotor + M_b(Omega,omega)] qdd + [C_rotor + C_b(Omega,omega)] qdot +
[K_rotor + K_b(Omega,omega)] q = f`.

No bearing mass is discarded or converted into a point disk.

## Internal bridge

Zero-M advanced bearings keep the B12-qualified internal type-5 K/C bridge.
Nonzero-M evaluations use an internal type-9 row containing K/C/M. Type 9 is
created only after model validation; it is not added to the historical
persisted legacy bearing types 1-8/20.

Ordering is source-faithful:

- Kxx, Kxy, Kyx, Kyy
- Cxx, Cxy, Cyx, Cyy
- Mxx, Mxy, Myx, Myy

## Qualified analyses

B19 targets stationary assembly, modal/eigensystem and stationary frequency
response paths. The same evaluated M table may depend on speed/frequency through
the existing CoefficientBearing interpolation contract.

## Deliberate exclusions

B18 run-up still rejects nonzero M until the time-varying mass term and its
associated `dM/dt` modeling policy are separately specified and qualified.
Coaxial and rotating/asymmetric advanced bearings remain B20/B21 work.
ThrustPad/axial DOF remains a later 6-DOF scope.

PASS requires Linux/Windows native and Python gates plus frozen ROSS modal parity
on the exact same commit.
