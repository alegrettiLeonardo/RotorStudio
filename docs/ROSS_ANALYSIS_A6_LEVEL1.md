# A6 — Level 1 Stability Analysis

## Campaign boundary

A5 qualified HEAD: `fa0827e2233620d68a422edf1dc99f6471dc45f3`.

A5 merge / promoted main baseline:
`799dd97583425915a2c9e5ec4b823468780e4146`.

A6 branch: `feature/ross-analysis-a6-level1`, created from that exact promoted
main commit.

Frozen ROSS authority:
`petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d`.

A0–A5 are preservation targets. Fault analyses remain out of scope.

## Frozen ROSS audit before production code

Primary authority:

- `ross/rotor_assembly.py::Rotor.run_level1`
- `ross/results.py::Level1Results`
- `ross/results.py::ModalResults.whirl_direction`
- `ross/results.py::Shape._calculate_orbits`
- `ross/results.py::_init_orbit`
- `ross/tests/test_plot_results.py::level1_response`
- `ross/agent_skills/ross/ucs_and_level1.md`

### Exact run_level1 semantics

For an existing rotor with `rated_w`:

1. `speed = self.rated_w`.
2. The applied cross-coupled stiffness array is
   `np.linspace(stiffness_range[0], stiffness_range[1], num)`.
3. At each value `Q`, ROSS copies the existing bearing list and appends one
   additional `BearingElement` at node `n` with:
   - `kxx = 0`
   - `cxx = 0`
   - `kxy = +Q`
   - `kyx = -Q`
   - default direct/cross damping and remaining coefficients.
4. Shaft, disk, existing bearings and point masses are otherwise unchanged.
5. ROSS runs its ordinary modal analysis at the rated speed.
6. It computes whirl direction for each returned physical mode from modal
   eigenvectors/orbits.
7. It rejects only modes classified exactly as `"Backward"`.
8. The Level 1 response at that Q is the logarithmic decrement of the **first**
   remaining non-backward mode in the frozen modal ordering:
   `modal.log_dec[modal.whirl_direction() != "Backward"][0]`.
9. `Level1Results` stores only the applied Q array and the selected log
   decrement array.

There is no modal branch tracking across Q in frozen `run_level1`. The selected
mode can therefore switch when the frozen modal ordering/whirl classification
changes.

### Whirl classification

For each lateral mode and node, ROSS forms the x/y orbit from the modal
eigenvector, computes the ellipse minor/major axes and signed kappa, and classifies
that node as Forward when kappa > 0 and Backward otherwise.

A whole mode is:

- Forward when all node orbits are Forward;
- Backward when all node orbits are Backward;
- Mixed otherwise.

Level 1 accepts Forward and Mixed; only Backward is excluded.

### Important stiffness-range detail

The explicit Level 1 range is **linear stiffness in N/m**, not UCS-style
base-10 exponents.

The frozen implementation contains an important default-range behavior:
when `stiffness_range is None`, it derives integer log10 values around the first
bearing stiffness, then passes those integers directly into `np.linspace`.
That behavior is frozen for audit/reproducibility, but the initial RotorStudio A6
production scope will require an explicit physical `stiffness_range_n_m` rather
than silently depending on that ambiguous/default path.

### Rated speed domain gap

Current RotorStudio `RotorModel` has no canonical `rated_w` field.
A6 will therefore require explicit `rotor_speed_rad_s` in the AnalysisCase.
It will not infer rated speed from another analysis, a bearing table or a shaft
nameplate field.

## Initial declared RotorStudio A6 scope

Planned supported scope:

- single shaft line;
- existing qualified 4-DOF lateral shaft/disk model;
- explicit rotor speed;
- explicit cross-coupling application node;
- explicit linear Q range in N/m;
- existing qualified radial bearings / coefficient-map-backed bearings whose
  synchronous coefficients can be evaluated at the explicit rotor speed;
- additive cross-coupled stiffness `Kxy=+Q`, `Kyx=-Q`;
- ordinary modal solve at the fixed rotor speed;
- frozen ROSS first-non-backward log-decrement selection;
- GUI, persistence, plot and data export.

Initial fail-closed scope:

- 6-DOF axial/torsional Level 1;
- linked/housing topology not already qualified in the 4-DOF assembly;
- generic PointMass not represented by the current RotorStudio domain;
- coaxial or asymmetric-rotor Level 1;
- inferred/default rated speed;
- implicit/default Q range;
- fault physics.

## Authority freeze plan

Before production implementation, A6 freezes immutable Level 1 references from
the exact ROSS SHA. The authority set will include:

- zero-speed plot fixture semantics;
- nonzero rated-speed baseline;
- application-node variation;
- anisotropic/damped supports;
- speed-dependent support coefficients;
- 2-D speed×frequency synchronous-diagonal support coefficients;
- stable/no-crossing style range;
- broad range that exercises selected-mode/whirl changes;
- frozen default-range behavior as an audit-only reference.

For every explicit production authority case, validation also stores per-Q
modal eigenvalues, damping/log decrement, whirl directions, selected mode index,
and first/middle/last matrix sentinels. This allows matrix-first and mode-selection
qualification rather than comparing only the final plotted curve.

## Status

A5: PASS / PROMOTED.

A6 authority audit: complete at source level.

Immutable A6 ROSS goldens: pending one-time freeze workflow.

Production A6 implementation: not started at this commit.
