# I19 — native API 541 harmonic torsional response

I19 consumes the explicit I17 torsional train and the I18 native modal kernel.

The native Fortran solver evaluates:

`(Kt - omega^2*J + i*omega*C)*theta = T(omega)`

and returns:

- complex angular response at each torsional station;
- complex transmitted torque in each torsional connection;
- the I18 free torsional modes;
- distance between each non-rigid mode and each declared excitation frequency.

Excitations that resolve to the same frequency are summed as complex torques.
Order-based excitations use the declared operating speed; explicit-frequency
excitations use their declared Hz value.

## Separation policy

I19 does not hard-code a numerical torsional separation margin. The result
always reports the fractional distance. PASS/FAIL is produced only when the
caller supplies `required_separation_fraction` as a project criterion.

## Analytic sentinel

For J1=2 kg.m2, J2=3 kg.m2, K=120 N.m/rad, omega=5 rad/s and harmonic
torques +1/-1 N.m, the closed-form response is:

- theta1 = 1/150 rad;
- theta2 = -1/225 rad;
- connection torque = 4/3 N.m.

## Scope boundary

A successful I19 result is:

`PASS_I19_NATIVE_TORSIONAL_HARMONIC_RESPONSE`

It does not qualify transient torque events, shaft/coupling stress or fatigue,
nor a whole-standard API 541 conformity statement.
