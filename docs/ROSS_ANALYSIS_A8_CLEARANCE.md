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

Immutable A8 authority: complete under `validation/ross_parity/clearance/`.

Native Fortran / versioned ABI / thin Python binding / AnalysisService / GUI /
persistence / exports: implemented for the declared scope.

Exact-head promotion qualification: pending. A8 is not promoted until the final
source SHA passes Linux/Windows A8 parity, immutable-authority reproduction,
A0-A7 preservation/regression and clean frozen product gates.


## Implemented native boundary

Production A8 physics is native Fortran 2018:

- `fortran/src/rd_clearance.f90`;
- `fortran/src/rd_clearance_c_api.f90`.

Versioned ABI:

- `rd_clearance_required_v1`;
- `rd_clearance_v1`.

The native path constructs synchronous unbalance forces, calls the promoted A3
full-order forced-response solver, projects radial probes, evaluates Amax/Avl/Scc,
computes x-y orbit major axes, scales peak-to-peak close-clearance response and
applies the strict 75% diametral-clearance check. For the automatic-unbalance
path it calls the promoted A7 native placement implementation at Nmc.

Python performs only scope checks, exact NumPy `union1d` speed-axis semantics,
already-qualified bearing map materialization, ABI marshaling, result objects,
units, plotting, persistence and exports.

## Immutable A8 reference set

The frozen reference set contains:

- `baseline_mode0`;
- `conical_mode1`;
- `high_speed_limit`;
- `cap_6`;
- `operating_speed_insertion`;
- `explicit_20_gmm`;
- `explicit_80_gmm`;
- `map_2d`.

The explicit 20 and 80 g·mm cases independently qualify the uncapped scaling
invariance: multiplying the explicit unbalance by four multiplies Amax by four,
divides Scc by four and leaves the final scaled clearance response unchanged.
An additional native/validation gate exercises an actually active cap below the
uncapped Scc; the `cap_6` golden preserves the common API 617 cap input even
when that particular response does not reach the cap.

After the one-time freeze, every A8 head regenerates a candidate from the exact
ROSS SHA and compares it numerically without rewriting the immutable directory.

## Fixed A8 numerical gates

A8 tolerances are independent from A7:

- speed axis: rtol 0, atol `2e-12 rad/s`;
- A7-generated / explicit unbalance magnitude: rtol `2e-9`, atol
  `2e-13 kg·m`;
- probe and clearance response: rtol `5e-7`, atol `5e-11 m pk-pk`;
- Avl and geometric clearances: near-machine precision;
- Amax: rtol `5e-7`, atol `5e-11 m pk-pk`;
- Scc: rtol `5e-7`, atol `5e-9`;
- A7 selected mode frequency: rtol `3e-8`, atol `3e-7 rad/s`;
- placement nodes, probe nodes, clearance nodes and PASS flags: exact.

For a close-clearance location whose entire conical-mode response is effectively
a numerical node (reference max below `1e-12 m pk-pk`), the argmax speed is not
a physical observable. ARPACK/LAPACK/platform roundoff can move the index of
that ~zero maximum while the response remains zero. A8 therefore gates the
near-zero maximum itself and omits only that meaningless argmax-speed equality.
All observable locations retain direct speed-at-maximum parity.

Validation also reconstructs the explicit synchronous unbalance force outside
the production A8 solver, runs it through the independently promoted A3 forced
response, and compares both radial probe projections and an independently
calculated orbit-major-axis clearance response. This separates the A8
post-processing gate from the native solve that it consumes.

## Desktop product integration

The GUI exposes **API 617 Close-Clearance Analysis** with:

- speed sweep start/stop/point count;
- explicit Nma and Nmc;
- one-based radial probe nodes and angles;
- one-based close-clearance nodes and radial running clearances;
- forward-mode selection for A7 automatic placement;
- optional explicit unbalance override;
- optional explicit scale-factor cap.

The result workspace shows scaled peak-to-peak clearance response versus rotor
speed, the 75% diametral-clearance limit, the Nma–Nmc operating region and the
sampled maximum. Its engineering summary reports radial/diametral clearance,
limit, maximum response, speed at maximum, Avl, Amax and Scc.

The product qualification chain is:

`GUI -> AnalysisCase("clearance") -> SolverJobManager -> AnalysisService ->
rd_clearance_v1 -> Fortran -> ClearanceResult -> plot/export -> save -> close ->
reopen -> recompute -> exact arrays/hash -> staleness`.

Exports include:

- summary CSV, one row per close-clearance location;
- companion long-form `*_response.csv` over location × speed;
- complete NPZ arrays/metadata;
- generic analysis report;
- PNG/SVG/PDF result plot.

The clean frozen Stage 2 Linux and Windows application smoke requires
`rd_clearance_v1`.

## Frozen source hashes

The A8 authority records exact SHA-256 values for:

- `ross/rotor_assembly.py`:
  `c5e6562d092426ffdb44641a1fb2092c6e5df8e3e44be437749b3711f7633c09`;
- `ross/results.py`:
  `0d53a92700228c074145e35e49e31e6f8550f4199efc1e9470b53ca5c5477cc3`;
- `ross/bearing_seal_element.py`:
  `4c1e39b0cfdb4a64dd0992df686f6771e3245fc74c2dc1fca95b684328cc5942`;
- `ross/probe.py`:
  `2e6b1f247893b12787887bd6e927ae950e2ab523a83699e508d35ce08e3adfd4`;
- `ross/utils.py`:
  `08708dc134682b40dcb8259527cdd9586e9f3eac26c0b510eda29355e05eb8d9`;
- `ross/tests/test_results.py`:
  `a8f5e244d0d9165f05bab8998d5ca6e1d101af945851cdb8daf519ddc76fd964`;
- `ross/agent_skills/ross/clearance_analysis.md`:
  `be46a5510689b3ba57ccc77e96f5b0e5772d58b5fe07d48b91c7bdf1f5a7f48e`.
