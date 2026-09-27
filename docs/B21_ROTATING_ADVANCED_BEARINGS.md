# B21 — Rotating / Asymmetric Advanced Bearings

BASE_HEAD = b158ac2fc76dcaf7ddfd5d54ebf8da542e9f6866
STATUS = AWAITING_SAME_HEAD_QUALIFICATION

## Frame contract

Advanced bearing K/C/M are defined in the stationary X/Y frame. A general
anisotropic stationary support becomes time-periodic after transformation to
rotating coordinates and therefore cannot be represented by RotorStudio's
existing constant-coefficient rotating-frame eigensolver.

B21 promotes only matrices that commute with the planar rotation generator:

`A J = J A`, for `A in {K,C,M}`.

This admits the physically time-invariant planar form `a I + b J`, including
isotropic direct terms and skew cross-coupling. General anisotropic support
matrices fail closed with an explicit diagnostic instead of being frozen at an
arbitrary rotor angle.

## Rotating-frame transformation

With `q_inertial = R(Omega t) q_rotating` and
`J=[[0,-1],[1,0]]`, one invariant advanced bearing contributes:

`M_b`

`C_b + Omega (2 M_b J)`

`K_b + Omega (C_b J) - Omega^2 M_b`

to the rotating-frame second-order equation.

The new advanced terms are kept separate from the historical V2 bearing
`K1b` term. Consequently the existing `chr_asym` nargout-dependent omission
is preserved only for legacy bearings; B21 coordinate-transform physics is never
dropped when eigenvectors are requested.

## Scope

B21 covers rotating/asymmetric modal analysis and synchronous rotating-frame
unbalance response for rotation-invariant advanced CoefficientBearing/map data,
including B19 nonzero M and speed-dependent tables.

Native physical bearing providers may enter this path only when their evaluated
K/C/M satisfy the same invariance gate. Anisotropic PlainJournal/TiltingPad
supports normally do not and therefore remain blocked in this rotating-frame
solver; a future periodic/Floquet formulation is required for that case.
