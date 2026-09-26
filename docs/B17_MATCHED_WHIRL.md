# B17 — Matched-Whirl Modal / Campbell

BASE_HEAD = a40c4869059a1295779d37fc3f6617ab00981735
ROSS_AUTHORITY = petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d
STATUS = AWAITING_SAME_HEAD_QUALIFICATION

## Policies

RotorStudio now exposes three explicit bearing-coefficient policies for stationary
modal/Campbell analyses:

- SYNCHRONOUS_COEFFICIENTS: bearing omega = rotor Omega;
- FIXED_WHIRL: bearing coefficients at (Omega, omega_fixed);
- MATCHED_WHIRL: per-mode fixed point omega <- abs(Im(lambda)).

The rotor-speed argument passed to the stationary Fortran eigensolver remains
Omega for every policy. Therefore the gyroscopic term remains Omega*G; the
bearing frequency only controls K_b(Omega,omega) and C_b(Omega,omega).

## Mode tracking

Matched-whirl starts from the synchronous eigensystem. At every inner iteration
the candidate mode is selected by complex Modal Assurance Criterion (MAC), not
by eigenvalue index. Diagnostics record iteration count, final whirl frequency,
last MAC, convergence and the coefficient-table/map interpolation status.

Campbell applies a second, outer MAC assignment between successive rotor-speed
points. Branches are therefore not connected by ascending frequency order.

## B16 map integration

B16 map-backed CoefficientBearing objects are consumed without recomputing THD/TEHD.
Metadata distinguishes tabulated, interpolated and extrapolated axis evaluation.
Direct physical bearings remain supported but are intentionally more expensive.

## Frozen ROSS authority

The implementation follows the frozen ROSS run_modal contract at
6320eab9f890f1b3cc1710d508b446fe063ca68d: fixed frequency changes bearing/seal
coefficient frequency while gyro keeps rotor speed; matched_whirl performs a
per-mode fixed point tracked by MAC with whirl_rtol/whirl_max_iter.

Known exclusions remain unchanged: coaxial/rotating advanced bearings, general
transient advanced bearings, nonzero bearing-M assembly and B18 run-up.
