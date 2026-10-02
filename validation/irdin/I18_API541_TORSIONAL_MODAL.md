# I18 — native API 541 torsional matrices and free modes

I18 consumes only the explicit I17 torsional train contract.

Implemented natively in Fortran:

- inertia matrix J;
- torsional damping matrix C;
- torsional stiffness matrix Kt;
- generalized free-mode eigenproblem Kt*phi = omega^2*J*phi;
- deterministic ascending frequency order;
- explicit retention of the rigid-body zero-frequency mode.

The initial topology remains a serial train. The native kernel does not infer
missing stations, driven equipment, coupling data or excitations from the ST41
lateral iRdin file.

## Analytic sentinel

For two inertias J1=2 kg.m2 and J2=3 kg.m2 connected by K=120 N.m/rad,
the non-rigid natural frequency is:

`omega = sqrt(K*(1/J1 + 1/J2)) = 10 rad/s`

The native Fortran CTest and Python binding qualification require this result.

## Scope boundary

A successful I18 result is:

`PASS_I18_NATIVE_TORSIONAL_MODAL`

It does not qualify:

- harmonic torque response;
- transient start/reclose response;
- shaft/coupling stress or fatigue;
- separation assessment against the declared torsional excitations;
- whole-standard API 541 compliance.

Those are later torsional gates.
