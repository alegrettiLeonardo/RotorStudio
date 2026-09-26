# B18 — Synchronous Advanced-Bearing Run-up

BASE_HEAD = 5c0f76a11499f75b5ced0a3a893fbe0e835604f0
STATUS = AWAITING_SAME_HEAD_QUALIFICATION

## Qualified design target

B18 is deliberately limited to:

- FULL_ORDER (all unconstrained physical rotor DOFs; no modal reduction);
- SYNCHRONOUS_COEFFICIENT_POLICY, omega(t)=Omega(t);
- MAP_BASED advanced bearings;
- NO_TEHD_IN_ODE.

The pre-existing legacy run-up ABI remains unchanged. B18 adds
`rd_runup_coeffmap_legacy`. Python materializes only coefficient maps before
entering native integration; the native Dormand-Prince RHS interpolates K/C
and never calls Python, Reynolds, THD or TEHD.

## Coverage and fail-closed rules

Every speed-dependent advanced bearing must be a synchronous one-dimensional
CoefficientBearing with complete coverage of the run-up speed interval.
Extrapolation is rejected before integration and again in the native
interpolator. All nonconstant maps in one run must currently share the same
speed axis and interpolation policy. Constant CoefficientBearing is supported
for the fundamental legacy type-5 equivalence gate.

The following remain blocked:

- advanced-bearing run-up with nr > 0;
- direct PlainJournalPhysicsBearing/TiltingPadPhysicsBearing in the ODE;
- asynchronous 2-D maps in B18;
- nonzero advanced-bearing M;
- coaxial or rotating/asymmetric advanced-bearing run-up;
- general transient advanced-bearing response.

## Native equation

At each native RHS evaluation,

M qdd + [C0 + Cb(Omega) + Omega G] qdot
      + [K0 + Kb(Omega)] q = F(Omega,t)

with the map interpolation performed entirely in Fortran. The gyroscopic
coefficient remains tied to rotor speed Omega.

## Qualification matrix

The B18 gate checks:

1. constant advanced CoefficientBearing versus legacy constant type-5 run-up;
2. variable synthetic speed map versus an independent SciPy DOP853 oracle;
3. coverage and reduced-order fail-closed behavior;
4. PlainJournal and TiltingPad B16 synchronous maps;
5. time-step/tolerance and map-resolution convergence;
6. Stage 1, B12 and B14-B17 regressions;
7. Linux and Windows native builds and source tests.

The document status changes to PASS only on a same-HEAD green qualification.
