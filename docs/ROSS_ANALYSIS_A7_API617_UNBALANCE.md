# A7 — API 617 Unbalance Placement

## Campaign boundary

A6 qualified HEAD: `e7906b6329bab06d6a5a7ea53170485a31869679`.

A6 merge / promoted main:
`bae1adf745ffd66742a14c956dbd090524f5737e`.

A7 branch: `feature/ross-analysis-a7-api617-unbalance`, created from that
exact promoted baseline.

Frozen ROSS authority:
`petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d`.

A0–A6 remain preservation targets. A8 API 617 Clearance is blocked until A7
promotion. 6-DOF platform work and fault analyses remain later campaign phases.

## Frozen ROSS source audit

Primary authority:

- `Rotor.api617_unbalance()`
- `Rotor._journal_bearing_loads()`
- `Rotor._overhung_mass()`
- `Rotor._whirl_ratio()`
- `Rotor.run_modal()` and mode-shape/orbit construction
- `Rotor.run_static()`
- `convert_6dof_to_4dof()`
- API 617 tests in `ross/tests/test_results.py`

### Forward-mode selection

At `maximum_continuous_speed`, ROSS runs modal analysis and evaluates the
amplitude-weighted whirl ratio for each lateral mode:

`sum(kappa_i * major_axis_i) / sum(major_axis_i)`.

A lateral mode is a primary forward candidate when its ratio is greater than
`FORWARD_WHIRL_RATIO = 0.25`. If no mode passes 0.25, ROSS falls back to modes
with positive ratio and warns. The public `mode` input indexes this filtered
forward-mode list, not the raw modal list.

### Antinode/lobe placement

For the selected mode:

1. node orbit major-axis amplitudes are computed;
2. the global maximum-amplitude node defines a reference orbit and its
   major-axis angle;
3. every node orbit is projected onto that reference direction;
4. projection sign defines mode-shape sign; exact zero is replaced by +1;
5. nodes below 2% of the maximum amplitude do not update lobe sign;
6. a lobe boundary is created when a significant node changes sign;
7. each lobe contributes its maximum-amplitude node as a candidate antinode.

Selection thresholds are then:

- inboard antinode: amplitude >= 10% of global maximum;
- outboard antinode: selected when it is the global reference or amplitude >=
  50% of global maximum.

There is no interpolation of antinode location between nodes.

### Static load used for unbalance

ROSS obtains journal static loads from `run_static().bearing_forces` and
converts force to kg using `g = 9.8065 m/s²`.

For one selected inboard antinode, W is the sum of all journal static loads.

For multiple selected inboard antinodes, W is the static load of the nearest
journal bearing in axial position.

For an outboard antinode, W is the rotor mass outboard of the adjacent outer
bearing: full shaft-element masses on that side plus disk/point masses strictly
outboard according to the frozen node inequalities.

### API 617 residual-unbalance equations

ROSS evaluates maximum continuous speed in rpm.

For `Nmc < 25000 rpm`:

`Ur = 6350 * W / Nmc` in g·mm.

For `Nmc >= 25000 rpm`:

`Ur = W / 3.937` in g·mm.

Applied unbalance is `Ua = 2 * Ur`, converted to kg·m.

The returned phase is 0 when the selected antinode has the reference sign and
pi when it has the opposite sign.

Returned fields are node(s), unbalance magnitude(s), phase(s), static load(s),
raw modal index and damped modal frequency.

## Initial A7 RotorStudio scope

A7 production will remain on the promoted qualified 4-DOF lateral platform.

Supported:

- explicit maximum continuous speed in rad/s;
- explicit forward-mode index;
- qualified single-shaft 4-DOF type-2 chain;
- disk types 1/2;
- legacy radial type 3/5 bearings and already-qualified coefficient/map-backed
  bearings evaluated synchronously at Nmc;
- inboard single-antinode, multi-antinode/conical and overhung placement;
- both residual-unbalance equation branches;
- native static-load recovery using the promoted A1 semantics;
- GUI/result/persistence/exports.

Fail closed:

- no inferred Nmc;
- no generic PointMass until the later 6-DOF/platform phase;
- no linked/housing support topology;
- no coaxial/asymmetric rotor API 617 placement;
- no fault dynamics;
- no A8 close-clearance acceptance calculation in A7.

## Authority plan

Before production implementation, immutable goldens must freeze both the actual
frozen ROSS result and the declared `convert_6dof_to_4dof` adaptation. Cases
must include first forward mode, conical/multiple antinodes, overhung placement,
the 25000-rpm equation boundary, and unavailable-mode failure.

Per case, freeze modal eigenvalues, whirl ratios, selected raw mode, node-orbit
quantities, journal static loads, selected antinodes and the final API 617
unbalance dictionary.

## Status

A6: PASS / PROMOTED.

A7 frozen-source audit: complete.

Immutable A7 authority: complete under `validation/ross_parity/api617_unbalance/`.

Production A7 native implementation, versioned ABI, thin Python binding,
AnalysisService integration, GUI, persistence and exports: implemented for the
declared scope.

Exact-head promotion qualification: pending. A7 must not be promoted until the
final source SHA passes Linux/Windows A7 parity, immutable-authority
reproduction, A0-A6 preservation/regression and clean frozen product gates.


## Implemented native boundary

Production placement physics is native Fortran 2018:

- `fortran/src/rd_api617_unbalance.f90`
- `fortran/src/rd_api617_unbalance_c_api.f90`

Versioned ABI:

- `rd_api617_unbalance_required_v1`
- `rd_api617_unbalance_v1`

The native solver performs the modal solve at Nmc, amplitude-weighted whirl
filter, node-orbit metrics, lobe segmentation, antinode selection, A1 static
journal-load recovery, overhung mass accounting and API 617 residual-unbalance
equations. Python validates the declared 4-DOF scope, materializes already
qualified coefficient/map-backed supports at the synchronous operating point
and marshals the native result. There is no Python placement-physics fallback.

The frozen ROSS warning path for the case where no mode exceeds whirl ratio
0.25 but positive-whirl modes exist is preserved from the native diagnostic
whirl-ratio vector.

## Immutable authority

The one-time authority is frozen from
`petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d`.
Subsequent branch runs regenerate a candidate from the same exact SHA and
compare it numerically without rewriting the frozen files.

Frozen cases:

- first forward mode at 9000 rpm;
- conical / multiple-antinode mode at 9000 rpm;
- 24999 rpm lower-equation side;
- 25000 rpm exact branch boundary;
- 30000 rpm high-speed branch;
- overhung placement at 6000 rpm;
- speed-dependent support coefficients;
- two-dimensional speed × frequency support maps evaluated synchronously;
- unavailable forward-mode failure.

For each successful case the authority stores both the original ROSS result and
the declared `convert_6dof_to_4dof` adaptation, including modal roots, whirl
ratios, node orbit quantities, journal static loads and final unbalance
placement.

Symmetric conical modes can exchange the numerically tied reference end or an
arbitrary global modal phase. Qualification therefore compares relative
unbalance phase and invariant mode-shape quantities rather than treating a
global pi rotation as a physical difference.

## Product integration

The desktop application exposes **API 617 Unbalance Placement** with explicit
maximum continuous speed, forward-mode number and modal root count. The result
workspace plots the selected mode's normalized node orbit-major-axis amplitude,
marks the selected unbalance nodes and reports Ua, phase, static load, raw mode
index and damped modal frequency.

The qualified product chain is designed as:

`GUI → AnalysisCase("api617_unbalance") → SolverJobManager → AnalysisService →
rd_api617_unbalance_v1 → Fortran → API617UnbalanceResult → plot/export → save
→ close → reopen → recompute → exact arrays/hash → staleness`.

CSV, complete NPZ, generic analysis report and PNG/SVG/PDF plot exports are
wired through the existing result-export surfaces. The Stage 2 clean frozen
Linux and Windows smoke now requires `rd_api617_unbalance_v1`.

## Fixed A7 numerical gates

A7 parity gates are independent of earlier stages:

- final Ua magnitude: rtol `2e-9`, atol `2e-13 kg·m`;
- recovered static loads: rtol `2e-9`, atol `2e-9 kg`;
- selected damped modal frequency: rtol `3e-8`, atol `3e-7 rad/s`;
- whirl ratio: rtol `3e-7`, atol `3e-8`;
- normalized node orbit-major-axis profile: rtol `4e-7`, atol `4e-8`;
- relative selected-unbalance phase: atol `2e-10 rad`;
- placement nodes and raw selected mode: exact integer equality.

The 25000-rpm boundary is gated by evaluating the two equations explicitly,
not by assuming that their numerical values must exhibit a large discontinuity.
