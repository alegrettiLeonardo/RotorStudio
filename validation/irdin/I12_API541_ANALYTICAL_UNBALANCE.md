# I12 — API 541 analytical unbalance

I12 closes the analytical-unbalance gap left intentionally open by I11.

Normative source: API 541 Third Edition (1995), lateral dynamic analysis.
For the declared SI scope:

- baseline input unbalance: `U = 6350 W / N` g.mm;
- analytical input shall be **no less than two times** that value;
- `W` is the journal static weight load [kg], or applicable overhung load;
- `N` is the operating speed nearest the critical of concern [rpm];
- unbalance location(s) are chosen to excite the mode most adversely;
- the predicted probe response is scaled, if necessary, until it reaches
  `Lv = 25.4*sqrt(12000/N)` micrometres peak-to-peak.

## Journal static loads

Initial I12 scope is exactly two imported supports. Journal loads are obtained
from static force/moment equilibrium of:

- qualified shaft self-mass;
- I7 materialized disk masses.

For two supports this determines the two vertical reactions uniquely from
total mass and first moment. Multi-support load allocation is not inferred.

## Mode placement

The modal vector is obtained from the native I9 expanded eigensolve at the
critical speed.

- translatory: one analytical unbalance at the largest radial modal
  displacement, based on both journal static loads;
- conical: two analytical unbalances, one in each journal-side region,
  based on the corresponding journal load and 180 degrees out of phase.

Automatic translatory/conical classification uses journal modal phase.
Ambiguous cases fail closed and require an explicit mode override.

## Response scaling

I12 first evaluates the minimum API 541 analytical input, using the native I9
expanded synchronous response. Because the qualified model is linear, all
analytical plane magnitudes are scaled by a common factor only when the
resulting peak-to-peak probe motion is below the API 541 vibration limit.

The source project is deep-copied for every analytical response solve. Imported
legacy forces and support coefficients are not mutated.

## Scope boundary

I12 qualifies analytical-unbalance construction and response only.

It does not yet claim:

- complete API 541 compliance;
- half-coupling identification when the source does not establish it;
- overhung-load substitution for a demonstrated shaft-end bending mode;
- general multi-support static load allocation;
- experimental model correlation.

Those remain explicit subsequent gates.
