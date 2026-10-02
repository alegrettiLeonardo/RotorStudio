# C1 — Misalignment qualification plan

## Entry gate

B3 is promoted on main at `0e9e57b7eed9a598c7001ba5258ce8829894344e` after its mandatory post-merge regressions.

## Frozen external authority

ROSS authority is fixed at:

`petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d`

Primary source:

`ross/faults/misalignment.py`

Source tests:

`ross/tests/test_misalignment.py`

C1 authority must be generated and frozen before any RotorStudio C1 production solver is added.

## Declared C1 scope

The first qualified C1 scope is the promoted one-shaft-line 6-DOF platform:

`[x, y, z, alpha, beta, theta]` per node.

Supported coupling fault models:

- flexible parallel misalignment;
- flexible angular misalignment;
- flexible combined misalignment;
- rigid parallel misalignment with state-dependent reaction evaluated at each Newmark time station.

The fault is attached to one existing circular shaft element. The implementation preserves the ROSS formulas and DOF force placement.

The initial transient scope is deliberately narrower than the complete ROSS API:

- full-order 6-DOF response;
- constant rotor speed;
- zero shaft material damping, consistent with the promoted B2 scope;
- circular B1/B2 shaft elements and supported rigid disks;
- constant radial bearing K/C/M evaluated at the fixed operating point;
- one or more synchronous unbalance inputs;
- simple Newmark only;
- zero initial q/v/a;
- no model reduction;
- no direct Reynolds/THD/TEHD solve inside the time step.

Variable-speed fault transients, model reduction, coaxial/multirotor, asymmetric shafts, flexible disks, gears, foundations and other nonlinear faults are outside this C1 qualification.

## Native design

Create:

- `fortran/src/rd_fault_misalignment.f90`
- `fortran/src/rd_fault_misalignment_c_api.f90`
- `fortran/tests/test_fault_misalignment.f90`
- `python/src/drm_core/solver/misalignment.py`
- `python/src/drm_core/analysis/misalignment.py`

The native solver reuses:

- qualified B2 `assemble_6dof`;
- qualified generic `rd_newmark::newmark_step`.

No NumPy/SciPy production eigensolver or transient solver fallback is permitted.

For the rigid model, ROSS updates the coupling reaction once per time station from the previously converged displacement state before the simple Newmark solve for that station. C1 must reproduce that exact authority behavior; it must not silently replace it with a different nonlinear tangent formulation.

## Authority cases

Frozen cases are defined in `validation/c1/cases.json`:

- C1F01 flexible parallel;
- C1F02 flexible angular;
- C1F03 flexible combined;
- C1R01 rigid parallel;
- C1R02 rigid parallel with torque transfer.

For every case freeze:

- time;
- rotor angle;
- base unbalance force;
- misalignment force history;
- total force history;
- full 6-DOF q(t);
- selected-node orbit;
- selected response DFFT;
- rigid effective stiffness parameters when applicable;
- SHA-256 provenance.

## Qualification hierarchy

1. source provenance and immutable ROSS freeze;
2. direct flexible force-history parity;
3. direct rigid state-force parity;
4. native full-order 6-DOF Newmark response;
5. independent equation residual;
6. q(t) parity;
7. orbit parity;
8. DFFT parity;
9. B1/B2/B3 preservation;
10. Linux + Windows exact-head qualification.

Only after all gates pass on one exact HEAD may C1 declare:

`C1_MISALIGNMENT_ROSS_PARITY = PASS`

and

`ENGINEERING QUALIFIED FOR DECLARED SCOPE`.

C2 rubbing remains blocked until C1 is explicitly promoted and mandatory post-merge main regressions pass.
