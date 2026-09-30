# B1 — 6-DOF element matrices: authority audit and execution plan

## Status and promoted baseline

B1_STARTED = YES
B1_STAGE = AUTHORITY_SOURCE_AUDIT_AND_INPUT_CASE_PLAN
B1_6DOF_ELEMENT_MATRICES_ROSS_PARITY = NOT_YET_QUALIFIED

This is the initial B1 audit and case definition, not an implementation or a numerical PASS. No B1 golden output has yet been generated or frozen; no B1 native matrix, ABI, CTest or dedicated workflow has yet been executed. Existing A8 promotion is separate and complete.

- Repository: alegrettiLeonardo/RotorStudio.
- New branch: feature/ross-analysis-b1-6dof-element-matrices.
- Base / promoted main: fcdac252974aeeded6961dbe3310677e234a6495.
- A8 qualified parent: d4c901e1e8b7261f1f175b78179923607789238a.
- A8 merge parents, in order: c2073acc0085900e72f0b17ad90cbf1090eec495 and d4c901e1e8b7261f1f175b78179923607789238a.
- Frozen ROSS: petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d.

A8 was promoted only after all four new-main push workflows completed successfully: M7 36702426397, Stage 1 Final 36702426462, G14 36702426461 and B13-B18 Integrated 36702426500. Project-owner authorization is recorded in PR #33 comments 5909357948 and 5909506096; no independent third-party review is claimed. The B1 branch was created only after this post-merge closure, directly from the promoted main, after checking that the requested branch name did not exist.

## 1. Actual authority sources inspected

These are Git blob IDs returned by the repository for the exact commits, NOT raw-file SHA256 digests. The generator must independently calculate raw SHA256 before freezing the reference.

| Source | Exact revision | Verified Git blob ID |
|---|---|---|
| ross/shaft_element.py | frozen ROSS | df74525956dc3b27d1cb675e0997146b4a835af3 |
| ross/disk_element.py | frozen ROSS | 330e0745a8d2898967f2b098369c6529db758d1f |
| ross/materials.py | frozen ROSS | a15a621fcb8e793e2e73bf08a5fe14657fec11d6 |
| fortran/src/rd_shaft_circular.f90 | promoted RotorStudio main | d554d8618e6bff2c371799c450a4943f0ab4a51c |
| python/tests/test_formal_equivalence_m6.py | promoted RotorStudio main | 6fbef1c0d9fbb0e440d55808c3d08b892dc9751e |

Read coverage includes ShaftElement.__init__, dof_mapping, complete M/K/G/Kst routines, DiskElement.__init__/dof_mapping/M/G/Kdt and Material.__init__. The M6 test identifies the existing validation.equivalence.element_abi.circular entry point for the lateral legacy cross-check. Source inspection is not substituted for matrix execution.

The future manifest must record exact function line ranges using inspect.getsourcelines on the imported frozen checkout rather than hand-maintained line counts. Record and verify the imported module paths, Git commit, Git blob bytes, working bytes and raw SHA256. Include dependencies that actually influence the matrices, at least shaft_element.py, disk_element.py, materials.py, units.py and element.py, plus the generator and this input manifest. No default-branch ROSS source may enter the reference.

## 2. Source-derived findings that constrain the implementation

### 2.1 Shaft geometry and material

The frozen ShaftElement has 12 local DOFs and supports different left/right inner and outer diameters. Missing right diameters default to their left counterparts. Its constructor derives A_l, A_r, Ie_l, Ie_r, the taper coefficients a1/a2/b1/b2/gama/delta, midpoint A/Ie, and phi. Replacing these different geometric quantities by one average section is not equivalent to the source.

Material.__init__ requires exactly two of E, G_s and Poisson, despite the broader wording in its class documentation. B1's explicit mechanical input contract will use rho, E and G_s; derive Poisson=E/(2*G_s)-1 in native geometry preparation. Reference objects must supply only E and G_s, not all three elastic constants. A later unit adapter is not a Python matrix solver.

Cowper and Hutchinson are distinct supported shear-factor branches. phi is controlled by shear_effects alone. rotary_inertia controls the additional lateral rotary mass, not phi. gyroscopic controls G independently. All eight combinations must be tested, not only two named beam presets.

Even with shear_effects=False, G_s is needed for torsional stiffness. The legacy circular path's special G=0 convention must not be carried into the 6-DOF contract. Require positive finite L, E, G_s and rho, and 0 <= inner < outer at both ends. Any material admissibility bound beyond these conditions must be explicitly declared and tested; do not invent a supposedly source-equivalent validation rule.

### 2.2 Shaft M and K

M contains the lateral consistent mass, the optional lateral rotary contribution, and separate axial and torsional blocks. Turning rotary_inertia off does not delete the torsional mass.

The source uses:

    Ae = (A_l + A_r)/2
    Je = Ie_l + Ie_r
    M[z0,z1] = rho*Ae*L/6 * [[2,1],[1,2]]
    M[theta0,theta1] = rho*Je*L/6 * [[2,1],[1,2]]
    K[z0,z1] = E*Ae/L * [[1,-1],[-1,1]]
    K[theta0,theta1] = G_s*Je/L * [[1,-1],[-1,1]]

The notation above describes 2x2 submatrices, not individual entries. Preserve the source's endpoint-mean convention for tapered elements. For a cylindrical element rho*Ae*L equals the geometric mass. For a conical element it need not equal rho times the exact frustum volume computed elsewhere by the same constructor. Therefore do not impose cylindrical total-mass identities on conical axial blocks and then alter ROSS-derived formulas to make the identity pass. Record this discretization convention explicitly.

K adds the axial-force geometric matrix and the torque matrix to bending, axial-extension and torsional stiffness. At nonzero torque the frozen K is generally NONSYMMETRIC. In zero-based local indexing its same-node torque terms include K[3,4]=-torque/2 and K[4,3]=+torque/2. A global assertion K=K.T is valid only for the applicable torque-free cases. The torque term must not be symmetrized.

Positive-semidefinite stiffness and six free-element rigid motions are appropriate to the unstressed baseline, not arbitrary compressive loads or nonconservative torque. K symmetry and K positive-semidefiniteness are separate checks.

### 2.3 Shaft G and Kst

G is a spin-speed coefficient, not already multiplied by operating speed. It uses phi and the taper-inertia coefficients and returns zeros when gyroscopic=False. Test G=-G.T and v.T@G@v=0 independently for arbitrary real test vectors.

Kst is the coefficient multiplied by angular acceleration in later time-dependent assembly. The frozen routine uses rho, L and (Ie_l+Ie_r)/2. It does not inspect shear_effects, rotary_inertia or gyroscopic. In particular gyroscopic=False makes G zero but does NOT make Kst zero. Kst is not symmetric or skew-symmetric in general. No generic symmetry gate applies to it.

Kst must be implemented independently, not obtained by reusing RotorStudio legacy K1 or by applying an assumed identity to G. The local variable named K1 inside ROSS ShaftElement.K is also not the legacy K1 output; identical names do not establish identical operators.

### 2.4 Disk

Local ordering is [x,y,z,alpha,beta,theta]. At zero-based indices:

    M = diag(m,m,m,Id,Id,Ip)
    G[3,4] = +Ip
    G[4,3] = -Ip
    Kdt[4,3] = +Ip

Every other entry of G and Kdt is zero. Kdt is one-sided and must not be silently completed into an antisymmetric pair. Disk K and C are zero in the inspected source but are outside the requested B1 output list. B1 starts with direct m/Id/Ip inputs, not DiskElement.from_geometry, PointMass, flexible disks or a new bearing model.

## 3. Explicit DOF and storage contract

| Quantity | Python / ROSS indices | Fortran indices |
|---|---|---|
| Left node | 0,1,2,3,4,5 | 1,2,3,4,5,6 |
| Right node | 6,7,8,9,10,11 | 7,8,9,10,11,12 |
| Lateral 4-DOF reduction | 0,1,3,4,6,7,9,10 | 1,2,4,5,7,8,10,11 |
| Axial subblock | 2,8 | 3,9 |
| Torsional subblock | 5,11 | 6,12 |
| Disk lateral reduction | 0,1,3,4 | 1,2,4,5 |

Shaft output: four independent 12x12 matrices M/K/G/Kst. Disk output: three independent 6x6 matrices M/G/Kdt. Store float64/double matrices in column-major order through the ABI. With zero-based row r and column c, buffer offset is r + leading_dimension*c. JSON references may store ordinary nested rows, but their declared indexing must be explicit; convert storage, never transpose the physics.

SI is not a single unit shared by all matrix entries. Translational, rotational and mixed blocks have different dimensions. Use a DOF-length scaling (translation scale L, rotation scale 1) and/or separately scaled physical blocks for residuals and invariant checks. An axial stiffness of large magnitude must not hide a small lateral or gyroscopic coefficient error through one indiscriminate absolute tolerance.

## 4. Input cases now defined — not generated goldens

The adjacent element_cases.json is a deterministic input specification only. It contains 26 shaft cases and 3 disk cases, corresponding to 113 requested matrix outputs after future generation (26*4 + 3*3). No computed reference values are present.

The shaft base uses L=0.173 m, idl=idr=0.012 m, odl=odr=0.047 m, E=207e9 Pa, G_s=79.5e9 Pa and rho=7813 kg/m^3. Case overrides cover solid/hollow/thin-wall and larger sections, multiple lengths, independent property sentinels, all eight effect-flag combinations, both shear methods, forward/reverse conical sections, axial force and signed torque. A separate changed cylindrical section is the stepped-parameter sentinel; it does not claim assembly of a stepped rotor.

Disk sentinels use distinct m/Id/Ip values so their six mass-diagonal entries, two gyro entries and single Kdt entry can be traced without ambiguous equal inertias.

Invalid cases belong to native/ABI tests, not to the valid golden set: zero/negative length, negative inner diameter, outer<=inner at either end, zero/negative E/G_s/rho, nonfinite geometry/material/load/inertias, unsupported flag values and shear method, wrong leading dimensions, short capacities and inconsistent shape. Disk zero-inertia/point-mass limits require an explicit declared decision before exposure; they are not implicitly a qualified PointMass path.

## 5. Golden generation and freezing — first executable gate

Planned reference directory: validation/ross_parity/6dof_elements/.

1. Create a validation-only generator and a clean checkout of the exact frozen ROSS SHA. Force core.autocrlf=false and core.eol=lf before checkout; verify raw working bytes equal Git blobs. Check imported module paths and run pip check.
2. Resolve each input case by copying its base and applying the declared shallow overrides; resolve the material key independently. Instantiate actual frozen ROSS Material/ShaftElement/DiskElement objects. Call their methods directly. Do not implement a second Python matrix formula to generate the goldens.
3. Record exact float64 outputs, input/derived geometry metadata, DOF mapping, case IDs, source/function mapping, generator SHA256, input-manifest SHA256, raw source hashes, ROSS commit, Python/NumPy/SciPy/platform and dependency lock/freeze. Record flags and effective right diameters explicitly.
4. Review the source-specific caveats above against actual outputs. Derive and freeze per-block numerical tolerances before the first native implementation comparison. Do not tune them after a failed Fortran comparison.
5. Commit the first immutable B1 reference once, before native formulas. Make later reproduction read-only: generate to a candidate directory and compare; never overwrite a failing reference. Preserve all existing A0-A8 references and source-integrity policies.
6. Add integrity checks for every B1 reference file and the pinned generator/input specification. Use text round-trippable float64 data and/or exact-array archives; serialization bytes and cross-platform numerical reproduction are distinct checks.

At this checkpoint generator execution, SHA256 computation, golden freezing and reproduction are NOT_RUN. The Git object IDs in section 1 do not pretend to satisfy this executable gate.

## 6. Additive Fortran implementation plan

After the reference gate, add rd_shaft_6dof.f90 and rd_disk_6dof.f90 plus versioned C-interoperable wrappers and dedicated native tests. Compute geometry, kappa/phi and all physical matrix coefficients in Fortran 2018 using double precision. Reproduce the observed explicit coefficients and zero patterns without calling the legacy 4-DOF routine to manufacture the new element.

Keep rd_shaft_circular, all existing assembly routines and every A1-A8 execution path unchanged. A shared library may expose additive B1 symbols, or B1 may use an isolated element library; choose the least invasive build integration and document it before publication. Any CMake additions must be exact additive target/source entries. Never replace the legacy global assembly with 6-DOF dispatch in B1.

If existing exact-file preservation guards reject legitimate B1 additions, first preserve the failing evidence. Extend only a reviewed exact path/status allowlist for the new B1 files. Do not weaken assertions on old files, remove A5 before/after tests, permit arbitrary directory-prefix modifications or alter historical snapshot hashes.

Python must remain a thin binding with rank/size/type validation, explicit scalar/flag mapping, contiguous owned output buffers and result containers. No np.linalg, SciPy or copied ROSS matrix formulas in production B1 code. NumPy/SciPy are allowed for independent validation only.

## 7. Proposed versioned ABI

- rd_shaft_6dof_matrices_v1: SI geometry/material/axial-force/torque inputs, explicit flags and shear-method enum; M/K/G/Kst outputs.
- rd_disk_6dof_matrices_v1: m/Id/Ip; M/G/Kdt outputs.

Each output needs an explicit leading dimension and capacity contract: nominal 12 rows / 144 doubles per shaft matrix and 6 rows / 36 doubles per disk matrix. Validate dimensions and capacities before writing; validate finite inputs and finite computed outputs. Define documented success/input/dimension/buffer/numerical status codes using the existing conventions where compatible. Do not change existing ABI layouts or symbols.

ABI guards must be tested with correctly allocated buffers and recognizable guard zones, with failure cases verifying no write outside the allowed region. A raw C pointer's true allocation cannot be inferred from a caller-supplied size; do not claim impossible memory-safety guarantees. The Python binding owns and checks its arrays. Include a column-major sentinel and negative tests for transposed/rank-two/strided input views wherever vector inputs are introduced.

## 8. Independent matrix invariants

Required checks in addition to every-entry parity:

- M symmetric and positive definite for the declared nondegenerate element cases; disk mass diagonal and kinetic-energy identity.
- K symmetric when torque=0; independently verify signed nonsymmetric torque terms when torque!=0. Check load contribution linearity rather than incorrectly requiring symmetry.
- G skew-symmetric, zero diagonal and zero real-vector quadratic form. G=0 on gyro-off cases; Kst remains source-equivalent and generally nonzero.
- Unstressed cylindrical K annihilates three rigid translations and three rigid rotations. With the left node at z=0 and right node at z=L, a positive alpha rigid rotation has y1=-L*alpha; a positive beta rotation has x1=L*beta. Test these signs explicitly.
- Cylindrical rigid-translation mass equals rho*A*L. Rigid torsional inertia equals rho*J*L, independently of the lateral rotary flag. Axial/torsional strain energies match EA*(u1-u0)^2/(2L) and G_s*J*(theta1-theta0)^2/(2L).
- For conical axial/torsional blocks, check the actual frozen endpoint-mean convention separately; report its distinction from exact geometric volume/inertia, without claiming a new corrected formulation.
- Density scaling of M/G/Kst; elastic/load scaling of the appropriate K contributions; exact zero blocks; finite entries; index and dimensional consistency. Do not impose stiffness positive-semidefiniteness under arbitrary compressive prestress.

CTest must include independently interpretable sentinels and invalid-input/buffer cases, not only a Python test that calls ROSS. An immutable generated Fortran test-data include may expose reviewed goldens, but it remains test data and must not replace production computation.

## 9. Lateral reduction cross-check

Use the explicit selection P=[0,1,3,4,6,7,9,10]. Compare the ROSS/Fortran 6-DOF lateral submatrices and, in the shared cylindrical Cowper scope, the preserved V2-qualified 4-DOF element exposure from validation.equivalence.element_abi.circular. Preserve the existing M6/formal V2 evidence rather than regenerating its authorities.

The actual promoted legacy flag map is:

| legacy stype | shear | rotary | gyro |
|---:|---|---|---|
| 1 | false | false | true |
| 2 | true | true | true |
| 3 | true | true | false |
| 4 | true | false | true |
| 5 | false | true | true |
| 6 | true | false | false |
| 7 | false | true | false |
| 8 | false | false | false |

Use matching geometry, loads, E/G/rho, flags, order and coefficient convention before judging equality. Source algebra suggests matching M/K/G in this restricted common scope; the numerical check is still NOT_RUN. Hutchinson and tapered cases are not automatically covered by the circular legacy comparator. Record discrepancies explicitly; do not replace 6-DOF formulas or invent transformations to force a PASS.

Do not compare Kst with the legacy K1 as though equality were expected. The inspected legacy K1 scales with E*I and stiffness geometry, whereas frozen Kst scales with rho*I and represents an angular-acceleration coefficient.

## 10. Dedicated qualification workflow and closure

Planned workflow name: ROSS Analysis B1 6DOF Element Matrices Qualification.

Required platforms: Ubuntu 24.04 and Windows 2025/UCRT64. On one exact final HEAD require Release compilation, all CTests, reference integrity, reproduction from frozen ROSS in an isolated dependency-consistent environment, every B1 matrix/case comparison, independent invariants, lateral reduction, ABI negative/guard tests, and the legacy/A0-A8 preservation and regression matrix appropriate to actual integration changes. Keep Stage 1's exact 57-test collection separate from new B1 tests. For integration into the shared native library, rerun inherited A5/A6/A7/A8 and the broader native/product matrix; old-HEAD success cannot close a new-HEAD gate.

Reject empty collections, failures, errors and skipped mandatory cases. Archive the exact HEAD, source/generator/reference hashes, compiler/build flags, environment, JUnit, raw arrays, per-case/per-matrix maximum differences and scaled residuals. The aggregate must verify both platforms and matching provenance; it must not emit unconditional PASS labels.

Only after the complete same-HEAD chain passes may B1 receive B1_6DOF_ELEMENT_MATRICES_ROSS_PARITY=PASS and ENGINEERING QUALIFIED FOR DECLARED SCOPE. B1 promotion is separate from A8 promotion. Do not start B2 global assembly/modal/Campbell, B3 axial/torsional product workflows, misalignment, rubbing, crack or harmonic-balance/fault dynamics here.

## Immediate next executable action

Implement and run the frozen-ROSS reference generator using element_cases.json, inspect its candidate matrices/derived properties, and freeze the reviewed B1 reference. Native element formulas follow that gate, not the reverse. This plan and its case manifest contain no claim that these future executions have already happened.
