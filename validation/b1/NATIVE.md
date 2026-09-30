# B1 native element implementation candidate

This is an additive, isolated element layer. This document does not assert a
completed build, native parity PASS, Windows qualification or promotion.
Executed evidence belongs to each local source snapshot and exact GitHub HEAD.

## Source authority and attribution

Formulas are translated from petrobras/ross at
`6320eab9f890f1b3cc1710d508b446fe063ca68d`, Apache-2.0, with original copyright
2022 Petroleo Brasileiro S.A. (Petroleo is written without the accent only in
ASCII Fortran headers). The unmodified upstream license, including its actual
copyright text, is copied into `validation/b1/ROSS-LICENSE.md`.

Reviewed source SHA256:

- shaft_element.py: `46d6bdf328dad4958a3b3398c28c8424c6057775ff461a646627339104cb89f6`
- disk_element.py: `6ff37f5188bc8eff9d8961cdd326496f7b8de2255f01a70655894584b6fa3d53`
- materials.py: `fae027debec61926a216916915ee7edb51850727293ced3c8381719b2625b8e8`

Source mapping at the frozen commit: shaft constructor 143-308; M 515-712;
K 714-905; Kst 907-946; G 977-1075. Disk M 198-232; Kdt 260-293; G 321-354.
These are the already executed authority audit's source ranges, not a claim of
new runtime source inspection by the native package.

Changes from the Python authority include a Fortran scalar contract, grouped
four-by-four lateral-plane population instead of twelve-by-twelve literal
Python lists, explicit enum/status validation, transactional output copies and
C-compatible buffer dimensions. Geometry, constitutive coefficients and matrix
arithmetic are native; the production Python module only marshals the ABI.

## Baselines and frozen reference

Native starting branch: `feature/ross-analysis-b1-6dof-element-matrices`.
Native starting HEAD: `ba43bc78f0dc943e34e3a5288b8f27e44923efd7`.
Main: `fcdac252974aeeded6961dbe3310677e234a6495`.
First B1 freeze: `a9a9b529f09958a2795b628535549a78d575dbd9`.
The 194 frozen files, generator, inspector, physical inputs and pre-native
block-specific policy are unchanged. SHA256SUMS.json remains
`86e80775aab32b904ba48a7d7ba64954a3cfabad79cf835e808bf49077ffe847`.
No native run regenerates authority or widens a tolerance.

## Scope and semantics

Per-node order: `[x,y,z,alpha,beta,theta]`.
Shaft: two nodes, M/K/G/Kst of order 12.
Disk: one node, M/G/Kdt of order 6.
Fortran lateral indices `[1,2,4,5,7,8,10,11]`; Python indices
`[0,1,3,4,6,7,9,10]`. Axial indices [3,9], torsional [6,12] in Fortran.

Shaft accepts L, idl, odl, idr, odr, rho, E, G_s, axial_force and torque in SI,
three integer boolean flags and a shear enum: 1=Cowper, 2=Hutchinson. Flags must
be exactly 0 or 1. Enum validity is checked even when shear is disabled.
G_s remains required and positive when shear is disabled because torsion still
uses it. Poisson is derived as E/(2*G_s)-1, with no extra empirical range filter.

The tapered geometry is retained through the source's polynomial coefficients.
Lateral bending uses the source midpoint quantities. Axial/torsional blocks use
Ae=(A_l+A_r)/2 and Je=Ie_l+Ie_r, not exact-frustum integration. The known conical
rigid-axial mass versus geometric-mass difference is not repaired here.

Rotary inertia controls lateral rotary mass only; torsional mass remains.
Gyroscopic controls G only. G is a coefficient, not multiplied by speed.
Kst is computed independently of the flags and G; it is not legacy K1.
K is not symmetrized under torque. Disk Kdt has only (5,4)=Ip in Fortran.

The disk domain is explicitly nondegenerate: finite m>0, Id>0, Ip>0. Rejecting
zero inertia is a declared B1 scope restriction, not a claim that the ROSS
constructor enforces it. No PointMass shortcut or disk-from-geometry is qualified.
There is no imposed physical inequality linking Id and Ip beyond positivity.

## Native integration

The three new modules are added to the existing drmrotor shared library with
`target_sources`. No existing source list item, solver equation, compiler flag
or dispatch is replaced. Old A1-A8 entry points and the legacy 4-DOF path are
unchanged. One CTest executable is added. The native modules do not call the
legacy 4-DOF element routine to manufacture new matrices.

The repeated scalar polynomials in rotary mass and gyroscopic G are evaluated
once independently of both output flags. G is populated from these polynomials,
not inferred from an already returned M. Kst uses its own explicit coefficient
block, never a relationship assumed from G or K1.

## C ABI v1

All real scalar inputs are `real(c_double), value`; flags/enums, leading
dimensions and capacities are `integer(c_int), value`. Functions return c_int.
Outputs are nonoverlapping, writable caller-owned double buffers; ownership is
not transferred. Buffers must not be null. Actual allocation length cannot be
inferred from a C pointer, and overlapping output buffers are outside contract.

Shaft argument order:

    rd_shaft_6dof_matrices_v1(
      L,idl,odl,idr,odr,rho,E,G_s,F,T,
      shear,rotary,gyro,method,
      M,ldM,capM,K,ldK,capK,G,ldG,capG,Kst,ldKst,capKst)

Disk argument order:

    rd_disk_6dof_matrices_v1(
      m,Id,Ip,M,ldM,capM,G,ldG,capG,Kdt,ldKdt,capKdt)

For each output of order n, require ld>=n and cap >= (n-1)*ld+n doubles.
The required-capacity multiplication uses c_int64_t to avoid c_int overflow.
Nominal n=12 requires 144 doubles; n=6 requires 36. Padded leading dimensions
require the corresponding larger declared capacity. Element (row,col), C
zero-based, is stored at offset row+ld*col. Padding and trailing guard regions
are not modified.

Status values, specific to these entry points:

| Value | Meaning |
|---|---|
| 0 | SUCCESS |
| 10 | INVALID_INPUT |
| 11 | INVALID_FLAG_OR_ENUM |
| 12 | INVALID_DIMENSION |
| 13 | INSUFFICIENT_CAPACITY |
| 14 | NONFINITE_RESULT |

10 follows the repository's existing invalid-input family. No old status table
or ABI is changed. Dimensions/capacities are checked before writes, scalar
validation and calculation occur in local matrices, and outputs are copied
only after all four/three matrices are valid. Finite inputs that overflow or
create invalid intermediate arithmetic return 14, not silent zero outputs.
The shaft wrapper saves/restores the caller's IEEE status, disabling halting
for invalid/divide-by-zero/overflow only during the isolated calculation so
Debug builds can return an error rather than terminate the process.

## Thin Python interface

`drm_core.solver.sixdof_elements.shaft_matrices` and `disk_matrices` return
named immutable dataclass containers for caller-owned float64 F-order arrays.
The arrays themselves remain mutable, independently allocated between calls.
Scalar/rank/type validation is strict; no vector squeezing, string coercion,
float-to-boolean truncation, matrix formula, NumPy/SciPy solver or fallback is
implemented in this production binding. Native failure is mapped to an
exception carrying the status and input context. The existing library loader
is reused without changing it.

## Preservation adaptation

`native_preservation.py` walks every file of the starting Git tree, comparing
raw bytes. Additions are an explicit file set, not arbitrary directory globs.
Only the exact additive CMake suffix and exact edits replacing the obsolete
whole-production-directory equality gate are permitted. The native workflow
is separately hash-pinned. Existing tests, source functions, old workflows,
V2/M6 and A0-A8 goldens remain byte-preserved. New guard tests exercise legacy
mutation, deletion, path traversal, unauthorized additions, compiler flag edits
and redirection of the existing shaft source.

The separate authority workflow still generates candidates outside the frozen
reference and compares ROSS outputs only. Its summary now explicitly says that
native implementation/ABI are not assessed by that workflow. Its source and
numerical reference generators are not modified.

## Executable qualification

`native_runner.py` runs Release and Debug builds, all CTest, both native Python
suite runs, then inherited A5 historical/corrective, A6, A7, A8, A0-A4/Stage1,
bearings, UI and preserved-authority checks. The Python B1 suite reads the
existing frozen policy for every matrix term and checks exact zero masks.
All 113 primary matrices and all 63 lateral selections are individually
reported, with absolute/relative maxima and zero-based indices per block and
matrix family. The signed-load subtraction floor is read unchanged from the
frozen policy. Independent invariants cover mass positivity/symmetry, gyro
work, conditional K symmetry, cylinder rigid motions/energies, density, all
flags, signed loads and endpoint-mean blocks in each conical case.

The 63 common-domain comparisons call the preserved
`validation.equivalence.element_abi.circular` with its documented stype map.
Kst is never compared with legacy K1. A discrepancy fails the initial gate and
requires diagnosis; no transformations or reference rewrites are automatic.

The dedicated GitHub workflow retains the immutable-authority preflight and
executes real native qualification on Ubuntu 24.04 and Windows 2025/UCRT64.
The separate authority workflow and required PR product workflows must pass on
the same exact final HEAD. Local source-tree results are bound to a full source
SHA256 snapshot, not misreported as qualification of the unmodified base HEAD.

## Publication and stop boundary

`native_publish.py --evidence ...` verifies the successful local Linux evidence,
unchanged source snapshot and remote HEAD/main, stages only explicit paths,
commits on the existing B1 branch, pushes without force and opens a draft PR if
none exists. It does not merge. It does not label B1 technically qualified before
exact-head Linux/Windows, authority and broad product CI evidence is reviewed.

`native_publish.py --status` is read-only. A green workflow inventory alone is
reported as awaiting artifact/log review, never automatic engineering promotion.

B1 does not implement global 6-DOF assembly, bearings, modal/Campbell, axial or
torsional rotor analyses, GUI analyses, transients, faults, or experimental
validation. B2/B3 remain blocked until explicit B1 promotion.
