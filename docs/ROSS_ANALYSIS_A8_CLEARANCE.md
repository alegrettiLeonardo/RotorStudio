# A8 — API 617 Close-Clearance Analysis

## Campaign boundary

A7 qualified HEAD: `4d610f0ac78d943092884187aba1e19e7f6aff3e`.

A7 merge / promoted main:
`03fef9b0da65c51b7ea3c9a14911cf7f83bcb015`.

The promoted merge was revalidated on main by the post-merge Stage 1 M7,
Stage 1 Final, G14 and B13–B18 integrated workflows.

A8 branch: `feature/ross-analysis-a8-clearance`. It already existed when A8
was opened, but was **identical** to the promoted A7 main (ahead=0, behind=0);
there was no pre-existing A8 implementation to preserve or reconcile.

Frozen ROSS authority:
`petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d`.

A0–A7 are preservation targets. Phase B / 6-DOF expansion does not begin until
A8 is promoted.

## Frozen ROSS audit

Primary authority:

- `Rotor.run_clearance_analysis()`;
- `Rotor.run_unbalance_response()`;
- `Rotor._unbalance_force()`;
- `Rotor.api617_unbalance()` from promoted A7;
- `ForcedResponseResults.data_magnitude()`;
- `ForcedResponseResults._calculate_major_axis_per_node()`;
- `Orbit.calculate_amplitude()`;
- `Orbit/_init_orbit`;
- `ClearanceResults`;
- clearance tests in `ross/tests/test_results.py`;
- `ross/agent_skills/ross/clearance_analysis.md`.

### Speed axis

ROSS converts the supplied speed axis to a one-dimensional float array and then
applies:

`np.union1d(speed_range, [minimum_allowable_speed, maximum_continuous_speed])`.

Therefore Nma and Nmc are always present and the resulting axis is sorted and
unique.

The required ordering is:

`0 <= Nma <= Nmc`.

### Probes

Only radial probes participate. Axial probes are ignored. At least one radial
probe is required.

For a radial probe at angle theta, ROSS evaluates the complex projected
displacement

`q_probe = qx cos(theta) + qy sin(theta)`.

The stored probe response is peak-to-peak:

`A_probe,pp = 2 |q_probe|`.

`Amax` is the largest probe peak-to-peak amplitude at any radial probe and
speed satisfying `Nma <= speed <= Nmc`.

### Vibration limit and scale factor

With Nmc in rpm:

`Avl = min(25.4, 25.4 sqrt(12000/Nmc)) micrometre peak-to-peak`.

The close-clearance scale factor is:

`Scc = Avl / Amax`.

When `scale_factor_cap` is supplied:

`Scc = min(Scc, scale_factor_cap)`.

An absent cap means no cap. The production API will preserve that distinction;
it will not silently apply six.

### Unbalance source

When explicit unbalance node/magnitude/phase is not supplied, A8 reuses the
promoted A7 API 617 placement at Nmc. When an explicit unbalance is supplied,
mode/mode_index/mode_frequency are not part of the result.

For each unbalance `(node, U, phase)`, frozen ROSS constructs synchronous
complex force:

- x: `U * omega^2 * exp(j phase)`;
- y: `-j * U * omega^2 * exp(j phase)`.

The rotor speed and excitation frequency are the same sweep value.

### Close-clearance response

At each declared close-clearance node and each speed, ROSS constructs the x/y
orbit from the complex forced response and obtains its major semi-axis.

Stored clearance response is peak-to-peak and scaled:

`Aclear,pp = 2 * Scc * major_axis`.

The diametral clearance is:

`Cdiam = 2 * min(radial_clearance)`.

The acceptance limit is:

`Climit = 0.75 * Cdiam`.

Per location:

- `max_clearance_response = max(Aclear,pp)`;
- `speed_at_max_response` is the sampled speed of that maximum;
- PASS only when `max_clearance_response < Climit` (strict inequality).

### ROSS domain-to-RotorStudio adaptation

ROSS discovers clearance locations by scanning bearing/seal elements that carry
`radial_clearance`. RotorStudio's promoted legacy/advanced bearing domain does
not have a single generic radial-clearance field shared by every qualified
support and zero-coefficient seal location.

A8 therefore uses an explicit analysis-local clearance map:

- one-based `clearance_nodes`;
- `radial_clearance_m`;
- optional `clearance_tags`.

This is an input-domain adaptation only. It does **not** alter response physics:
the frozen authority cases carry the same nodes/clearances/tags extracted from
ROSS. A zero-K/zero-C seal used only to declare a clearance is represented by a
clearance-map row rather than by a fictitious support matrix.

Similarly, radial probes are analysis-local inputs:

- one-based `probe_nodes`;
- `probe_angles_rad`;
- optional `probe_tags`.

This avoids mutating promoted model hashes or A0–A7 persistence contracts.

## Initial declared A8 scope

SUPPORTED:

- promoted A7 API 617 unbalance placement or explicit user-supplied unbalance;
- promoted A3 full-order synchronous forced response;
- explicit speed sweep plus Nma/Nmc insertion;
- radial probes at arbitrary angles;
- explicit close-clearance nodes/radial running clearances;
- no scale-factor cap or explicit positive cap;
- constant radial type 3/5 supports;
- qualified coefficient/map-backed supports evaluated synchronously at each
  sweep speed;
- qualified single-shaft type-2 4-DOF platform;
- GUI, persistence and exports.

FAIL CLOSED:

- no axial probe used to form Amax;
- no linked/housing supports;
- no generic PointMass;
- no coaxial/asymmetric A8;
- no direct physical Reynolds/THD/TEHD solve inside the clearance sweep; use a
  qualified coefficient/map-backed support first;
- no 6-DOF A8;
- no implicit running-clearance inference from geometry;
- no fault physics.

## Required A8 qualification order

1. freeze immutable ROSS A8 goldens;
2. qualify speed-axis union semantics;
3. qualify synchronous unbalance-force construction;
4. qualify A3 forced-response reuse point-by-point;
5. qualify radial probe projection and pk-pk convention;
6. qualify Avl / Amax / Scc, including cap semantics;
7. qualify orbit major-axis response;
8. qualify diametral-clearance / 75% limit / strict PASS semantics;
9. qualify A7-generated and explicit-unbalance paths;
10. ABI and bounds;
11. thin Python binding;
12. AnalysisService;
13. GUI;
14. save/reopen/recompute and exports;
15. A0–A7 preservation/regression;
16. frozen Linux;
17. frozen Windows.

No `A8_CLEARANCE_ROSS_PARITY = PASS` statement is valid before those gates
close on one exact HEAD.

## Status

A7: PASS / PROMOTED.

A8 frozen-source audit: complete.

Immutable A8 authority: pending one-time freeze.

Production A8 implementation: not started at this commit.
