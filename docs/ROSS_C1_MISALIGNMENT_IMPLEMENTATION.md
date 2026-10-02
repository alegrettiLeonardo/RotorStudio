# ROSS C1 — Misalignment fault dynamics

## Status

C1 is implemented on top of promoted B3 and is under exact-head qualification.

- promoted B3 / C1 base main: `0e9e57b7eed9a598c7001ba5258ce8829894344e`
- frozen ROSS: `petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d`
- immutable C1 authority freeze: `b45bbaa5ec91ca004643142e83f75d0c13f7a8ea`
- freeze parent: `a82f5aa6bfec0b0b287d0bafcd6dfc5a972c37d5`
- production solver at freeze: `NOT_STARTED`
- frozen arrays: 60

The authority was generated independently on Ubuntu 24.04 and Windows 2025,
compared cross-platform, and frozen before any C1 production solver file
existed. The authority workflow was then converted to strict read-only
reproduction.

## ROSS source mapping

Primary authority is `ross/faults/misalignment.py`. The frozen provenance
also pins:

- `ross/tests/test_misalignment.py`;
- `ross/rotor_assembly.py`;
- `ross/utils.py`.

C1 preserves the ROSS fault-force formulas rather than inferring a generic
misalignment law.

### Flexible coupling

Three ROSS modes are qualified:

- parallel;
- angular;
- combined.

For the parallel component, with coupling radius (r), offsets
(delta_x,delta_y), rotor angle (	heta), and
(a=[0,pi/6,pi/3]), ROSS evaluates three coupling deformations from

[
r^2+delta_x^2+delta_y^2+
2rsqrt{delta_x^2+delta_y^2},f(phi+a),
qquad
phi=arctan(delta_x/delta_y)+	heta.
]

The resulting radial forces are resolved in x/y and placed as equal and
opposite translational forces at the two nodes of the selected shaft element.
The flexible angular component uses ROSS' three-arm bending-force law

[
F_a =
left|k_b rsqrt{2-2cosalpha}sinalpha,
sin(	heta+4a)ight|.
]

Combined misalignment is exactly the ROSS sum of parallel and angular force
vectors.

### Rigid coupling

ROSS derives effective lateral and torsional stiffnesses from the global
stiffness matrix at the two coupling nodes. At each new time station the
misalignment angle is updated from the previously converged displacement state.
The resulting force is therefore state dependent in time.

A source-level detail is important: ROSS simple Newmark obtains the RHS once
at the beginning of each time station from the previous converged state and
holds that RHS fixed during the Newton correction loop. C1 reproduces that
behavior literally. It does not replace it with a different fully nonlinear
tangent iteration.

## Dynamic equation

C1 uses the promoted B2 full six-DOF ordering

[
[x,y,z,alpha,eta,	heta]
]

at every node and the promoted B2 global matrices. For constant spin speed,

[
Mddot q + (C+Omega G)dot q + Kq =
F_u(t)+F_{mis}(t,q_{prev}).
]

For flexible coupling, (F_{mis}) is prescribed by the ROSS angular position
law. For rigid coupling, it uses the previous converged state exactly as
described above.

The synchronous unbalance authority uses

[
F_x=UOmega^2cos(phi+	heta),qquad
F_y=UOmega^2sin(phi+	heta)
]

for the qualified constant-speed scope.

Time integration reuses the already-qualified native
`rd_newmark::newmark_step`. No Python integration fallback is present.

## Declared scope

Qualified target scope for C1:

- one consecutive shaft line;
- promoted B1/B2 circular shaft elements;
- promoted rigid disks;
- promoted radial bearing K/C/M evaluated at the fixed operating point;
- full-order six DOF per node;
- constant rotor speed;
- simple Newmark;
- zero initial q/v/a;
- synchronous unbalance;
- one selected shaft element carrying the misalignment;
- flexible parallel/angular/combined coupling;
- rigid parallel coupling;
- optional ROSS input/load torque terms.

Explicitly outside C1:

- model reduction;
- variable-speed misalignment transient;
- direct Reynolds/THD/TEHD inside the time step;
- coaxial/multirotor;
- gears;
- foundation DOFs;
- asymmetric shafts;
- flexible disks;
- rubbing;
- cracks;
- harmonic balance;
- other fault interactions.

## Native implementation

Fortran:

- `fortran/src/rd_fault_misalignment.f90`
  - flexible ROSS force law;
  - rigid ROSS state-dependent force law;
  - synchronous unbalance history;
  - B2 matrix assembly;
  - full-order simple Newmark integration;
  - diagnostic force histories and residuals.
- `fortran/src/rd_fault_misalignment_c_api.f90`
  - `rd_misalignment_required_v1`;
  - `rd_misalignment_response_v1`.
- `fortran/tests/test_fault_misalignment.f90`
  - action/reaction;
  - parallel + angular = combined;
  - zero-angle angular limit;
  - rigid zero-offset torque sentinel.

Python:

- `python/src/drm_core/solver/misalignment.py`
  - strict input validation;
  - B2 descriptor reuse;
  - ABI marshalling;
  - typed `MisalignmentResult`;
  - orbit and one-sided DFFT helpers.
- `python/src/drm_core/analysis/misalignment.py`
  - application/service wrapper.
- `SolverFacade.misalignment_6dof`.
- service-only `AnalysisCase.kind="misalignment"`.

The new service kind is intentionally not inserted into the legacy 21-contract
Flet GUI inventory during C1. GUI exposure is not claimed by this first C1
scope.

## Frozen authority cases

- C1F01 — flexible parallel;
- C1F02 — flexible angular;
- C1F03 — flexible combined;
- C1R01 — rigid parallel;
- C1R02 — rigid with input/load torque transfer.

Each case freezes time, rotor angle, base unbalance force, misalignment force,
total force, full six-DOF response, selected orbit, response DFFT and rigid
parameters where applicable.

## Qualification

The fixed tolerance policy is
`validation/c1/TOLERANCE_POLICY.json` and was committed before production
code. It must not be relaxed in response to CI.

Required gates:

1. immutable source provenance;
2. read-only authority reproduction on Linux and Windows;
3. direct force-history parity;
4. native full-order q(t) parity;
5. orbit parity;
6. DFFT parity;
7. rigid parameter parity;
8. independent action/reaction checks;
9. native Newmark equation residual;
10. CTest and ABI validation;
11. promoted B1/B2/B3 byte-preservation;
12. inherited analysis/product regressions;
13. same exact HEAD on Ubuntu 24.04 and Windows 2025/UCRT64.

Only one exact HEAD may receive:

`C1_MISALIGNMENT_ROSS_PARITY = PASS`

and

`ENGINEERING QUALIFIED FOR DECLARED SCOPE`.

C2 rubbing remains blocked until C1 is explicitly promoted and mandatory
post-merge main regressions pass.
