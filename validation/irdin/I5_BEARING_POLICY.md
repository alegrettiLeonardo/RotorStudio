# I5 — historical iRdin bearing-table range/interpolation policy

## Authority

The numerical policy is taken from the historical RotorDin source at
`alegrettiLeonardo/frontend_rotordin@647d600bc1d32a05de62ee457942e00285b572e3`:

- `matfun.f90::intlag`: three-point Lagrange through the right interior knot,
  including lower extrapolation when three or more points exist; final
  interval and upper extrapolation use the last two points linearly.
- `rd_commons.f90::com_brgsm`: recommended factors `mrp=[0.75,1.25]`.
- `parmanv.f90::parman/lmvpar`: values remain evaluable outside that range;
  the range is a warning/recommended range, not a coefficient clamp.

For ST41, the table is 500–4000 rpm, so the demonstrated recommended range is
375–5000 rpm. The response request starts at 300 rpm and is therefore explicitly
classified as `EXTRAPOLATED_OUTSIDE_LEGACY_RECOMMENDED_RANGE`.

## Implementation

`RB_INTERP_IRDIN=3` is additive to PCHIP and linear interpolation in the
native bearing library. Imported iRdin TABLE bearings use
`interpolation="irdin_lagrange"`. Other bearing families and existing
PCHIP/linear models are unchanged.

This stage does not clamp Campbell/response grids and does not release the
project's global numerical-readiness blockers. Automatic case construction is
a later stage.
