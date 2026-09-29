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

Immutable A7 authority: pending.

Production A7 implementation: not started at this commit.
