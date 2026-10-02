# B3 — dedicated axial / torsional workflows

B3_BASE_MAIN: c23a5e515480fa28fb6dd770fca235b73dd0198a
B2_QUALIFIED_HEAD: 491ae024beeb05a7e08f31ff48ef13c829da88d2
B2_MERGE_SHA: c23a5e515480fa28fb6dd770fca235b73dd0198a
ROSS_AUTHORITY: petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d

Entry gate: PASS.

B2 was engineering-qualified on one exact HEAD, merged with expected-head SHA,
and the mandatory main-push regressions all passed:

- Stage 1 M7 #420 — PASS
- Stage 1 Final #397 — PASS
- G14 Book Problem Regression #339 — PASS
- B13-B18 Integrated Product Qualification #101 — PASS

B2_PROMOTED = YES

## Declared B3 scope

B3 is additive and consumes the already-qualified B2 6-DOF platform.

The dedicated modal families are the invariant 6-DOF subspaces:

- axial: node DOF `z`
- torsional: node DOF `theta`

The initial B3 scope is restricted to the B2 single-shaft-line model family,
for which the axial and torsional subspaces are uncoupled from the lateral
subspace. B3 must fail closed if that block-decoupling contract is violated.

B3 qualifies:

1. axial and torsional extraction from global `M/K/C/G/Ksdt`;
2. reduced axial and torsional modal workflows;
3. axial and torsional modal sweeps over rotor speed;
4. dedicated result objects and thin Python/service exposure;
5. ROSS parity, including a torsional cross-check against
   `ross.utils.convert_6dof_to_torsional`;
6. independent block-decoupling, residual, rigid-mode and speed-invariance gates;
7. Linux and Windows exact-head qualification.

## Explicit exclusions

B3 does NOT add:

- forced response 6-DOF;
- transient/run-up 6-DOF;
- matched-whirl 6-DOF;
- Rouch synchronous 6-DOF;
- gears or multirotor/coaxial models;
- linked/housing/foundation DOFs;
- axial thrust-bearing physics;
- flexible disks;
- asymmetric shafts;
- misalignment, rubbing, crack or harmonic-balance fault dynamics.

Fault work remains blocked until B3 is promoted.

## Authority order

The mandatory order is:

B2 promoted
-> audit frozen ROSS
-> fix B3 cases and tolerances
-> generate Linux/Windows authority candidates
-> compare platforms
-> freeze immutable B3 authority
-> make authority workflow read-only
-> only then add native B3 production code.

PRODUCTION_SOLVER = NOT_STARTED
