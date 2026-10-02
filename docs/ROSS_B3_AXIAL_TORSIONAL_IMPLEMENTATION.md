# ROSS B3 — Dedicated axial / torsional 6-DOF workflows

## Status

B3 is implemented on top of the promoted B2 6-DOF platform and is awaiting
exact-head Linux/Windows qualification.

- B2 qualified HEAD: `491ae024beeb05a7e08f31ff48ef13c829da88d2`
- B2 promoted main / B3 base: `c23a5e515480fa28fb6dd770fca235b73dd0198a`
- frozen ROSS authority: `petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d`
- immutable B3 authority freeze: `e4fda44cba1dd29696c67be449fa560440d9ebc0`

The authority was frozen before any B3 production solver existed. The freeze
record states `production_solver = NOT_STARTED`, and the post-freeze authority
workflow is read-only.

## Physical / numerical scope

The qualified B2 nodal order is

[
[x,;y,;z,;alpha,;eta,;	heta].
]

B3 defines two dedicated invariant subspaces:

- **Axial:** the `z` degree of freedom at every node, indices `2 + 6n` in
  zero-based Python indexing.
- **Torsional:** the `theta` degree of freedom at every node, indices
  `5 + 6n`.

For the declared single-shaft-line B2 model family, the frozen authority proves
that these two subspaces are uncoupled from their complementary degrees of
freedom. B3 does not approximate a coupled model: if an M/K/C/G/Ksdt cross block
is larger than the frozen relative Frobenius gate, execution fails closed.

For a selected family (mathcal D), B3 extracts

[
M_r=M[mathcal D,mathcal D],quad
K_r=K[mathcal D,mathcal D],quad
C_r=C[mathcal D,mathcal D],quad
G_r=G[mathcal D,mathcal D],quad
K_{sdt,r}=K_{sdt}[mathcal D,mathcal D].
]

The initial frozen authority has

[
C_r=0,qquad G_r=0,qquad K_{sdt,r}=0
]

for both dedicated families. Therefore the native workflow solves the real
generalized eigenproblem

[
K_r q = lambda M_r q,qquad
omega_n=omega_d=sqrt{lambda},
]

using LAPACK `DGGEV` through the existing `rd_lapack.generalized_eig_real`.
No explicit matrix inverse and no NumPy/SciPy production eigensolver are used.

One rigid family mode is removed by the same physical-frequency cutoff family
used in the B2 campaign; for an N-node free axial/torsional chain, B3 expects
exactly N-1 positive elastic modes. The native residual is evaluated from

[
r_j=K_rq_j-lambda_jM_rq_j
]

and normalized by matrix/vector norms. Eigenvectors are unit-normalized with a
deterministic sign convention.

## Frozen authority

The authority contains 94 arrays from real frozen ROSS. Cases are fixed in
`validation/b3/cases.json`:

- axial modal: AX01, AX02, AX03;
- torsional modal: TOR01, TOR02, TOR03;
- axial sweep: AXC01;
- torsional sweep: TORC01.

The freeze reproduced on Ubuntu 24.04 and Windows 2025. Frozen evidence records
zero family-to-complement coupling for the declared cases and modal residuals
below (9	imes10^{-16}).

Torsional authority additionally cross-checks the extracted `theta` matrices
against `ross.utils.convert_6dof_to_torsional`. In the frozen cases the
matrix differences are exactly zero.

## Native implementation

Fortran modules:

- `fortran/src/rd_axial_torsional.f90`
  - invariant-family extraction;
  - cross-block decoupling diagnostic;
  - generalized modal solve;
  - rigid-mode removal;
  - normalized mode vectors and residuals;
  - fail-closed scope enforcement.
- `fortran/src/rd_axial_torsional_c_api.f90`
  - `rd_axial_torsional_required_v1`;
  - `rd_axial_torsional_modal_v1`.

The ABI first assembles the already-qualified B2 global matrices, then invokes
the B3 reduced-family kernel. B1/B2 element and global solvers are not changed.

## Python / service API

Thin native adapters:

- `run_family_modal_6dof(..., family="Axial"|"Torsional")`;
- `run_axial_modal_6dof`;
- `run_torsional_modal_6dof`;
- `run_family_sweep_6dof`;
- `run_axial_sweep_6dof`;
- `run_torsional_sweep_6dof`.

`SolverFacade` exposes corresponding B3 methods. `AnalysisService` accepts:

- `axial_modal`;
- `torsional_modal`;
- `axial_sweep`;
- `torsional_sweep`.

The sweep is orchestration over native fixed-speed family solves. It does not
introduce a Python eigensolver. Project save/reopen and generic analysis-report
serialization use the existing application infrastructure.

## Qualification gates

The exact-head B3 gate requires:

1. immutable frozen ROSS authority reproduction on Linux and Windows;
2. all Fortran Release CTests;
3. axial/torsional matrix, eigenvalue, scalar and eigenvector parity;
4. MAC >= 0.9999 for selected family vectors;
5. reduced second-order residual <= 1e-8;
6. family-to-complement relative Frobenius coupling <= 1e-12;
7. axial/torsional speed invariance within 1e-7 rad/s for the frozen model;
8. torsional ROSS conversion cross-check;
9. cross-check against qualified B2 full 6-DOF family modes;
10. B1/B2 byte-preservation and exact additive CMake integration;
11. service dispatch and project round-trip tests;
12. same exact source HEAD on Ubuntu 24.04 and Windows 2025.

## Explicit limitations

This B3 stage does **not** qualify:

- axial thrust-bearing coefficients or thrust-bearing physics;
- damped axial/torsional subspaces;
- lateral-axial or lateral-torsional coupling;
- 6-DOF matched-whirl or Rouch synchronous formulations;
- gears, multirotor/coaxial coupling or foundation DOFs;
- flexible disks or asymmetric shafts;
- 6-DOF forced response;
- 6-DOF transient/run-up;
- misalignment, rubbing, cracks, harmonic balance or other fault dynamics.

Those exclusions are fail-closed scope boundaries, not silently approximated
features.

## Promotion rule

B3 may be declared `ENGINEERING QUALIFIED FOR DECLARED SCOPE` only when one
exact HEAD passes the complete Linux/Windows B3 qualification and inherited
preservation gates. Fault work remains blocked until B3 is merged and mandatory
post-merge main regressions pass.
