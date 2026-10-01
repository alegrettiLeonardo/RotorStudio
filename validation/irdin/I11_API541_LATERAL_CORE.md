# I11 — API 541 lateral assessment core

I11 builds on the I9 expanded native rotor-bearing-support solves and the I10
legacy-ready import path.

Implemented in this stage:

- deterministic modal branch tracking by complex-vector MAC;
- critical-speed crossings against declared excitation orders;
- configurable separation checks (15% default for the declared API 541 scope);
- legacy imported unbalance/probe peak summaries;
- support-stiffness sensitivity using temporary scaled support models.

All eigenvalue and synchronous-response solves remain in the native Fortran I9
path. Python performs orchestration and post-processing only.

## Important scope boundary

I11 does **not** fabricate the API 541 analytical unbalance case from the
legacy [Desbal] records. The response summary in this stage is explicitly the
legacy source unbalance response.

Therefore:

- technical gate: PASS_I11_API541_LATERAL_CORE;
- API 541 analytical unbalance: NOT_YET_QUALIFIED;
- full API 541 compliance claim: false;
- global readiness remains LEGACY_NUMERIC_READY until the analytical
  unbalance and final reporting gates are qualified.

## Separation

For a fixed operating speed, the separation fraction is the absolute distance
between the critical speed and the operating speed divided by the operating
speed.

For a declared operating range, a critical inside the range has zero
separation; outside the range, the nearest range boundary is used.

The required fraction is an explicit AnalysisCase parameter. The automatic
ST41 case will use 0.15 only after this core passes on Linux and Windows.

## Support sensitivity

Default engineering factors are:

0.5, 0.75, 1.0, 1.25, 1.5

Only support stiffness is scaled. Support mass, support damping and bearing
coefficients are unchanged. The persisted imported project is never mutated.

This is a sensitivity study, not a substitute for measured support impedance
or modal-test data.
