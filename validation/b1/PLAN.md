> Historical authority-freeze plan. The native B1 implementation was subsequently
> published and reconciled with promoted main `0904bf5940a5006a57bb3292b46dcedcab7e3dd5`.
> Current native scope and qualification state are documented in `validation/b1/NATIVE.md`.
> This file remains as provenance for the frozen-authority stage.

# B1 — frozen 6-DOF element authority and remaining native plan

## 1. Scope and current evidence boundary

This continuation executes the FROZEN AUTHORITY GATE ONLY. No native B1 element formulas, C ABI, production Python binding, global 6-DOF assembly, modal/Campbell, B2/B3 or fault dynamics are implemented here. A8 remains promoted independently.

The first immutable authority has been published and its original Linux/Windows data compared successfully. The subsequent read-only two-platform workflow must close on the exact HEAD containing this updated plan and post-freeze guards. That exact HEAD and run results are recorded by CI in job-summary.json, reproduction.json and the aggregate summary; no future run is represented here as already executed.

| Item | Executed state at first freeze |
|---|---|
| B1_AUTHORITY_SOURCE_AUDIT | PASS |
| B1_INPUT_CASE_PLAN | PASS |
| B1_REFERENCE_GENERATOR | PASS |
| B1_GOLDENS | CREATED_AND_FROZEN |
| Initial candidate cross-platform numerical reproduction | PASS |
| B1_NATIVE_IMPLEMENTATION | NOT_IMPLEMENTED / NOT_STARTED |
| B1_ABI | NOT_IMPLEMENTED / NOT_STARTED |
| B1_6DOF_ELEMENT_MATRICES_ROSS_PARITY | NOT_YET_QUALIFIED |

Frozen-source agreement is not native B1 engineering qualification, promotion, experimental validation or full rotor qualification. The next implementation requires a separate explicitly authorized continuation after this authority gate closes.

## 2. Revalidated baseline and exact history

- Repository: alegrettiLeonardo/RotorStudio.
- Existing branch: feature/ross-analysis-b1-6dof-element-matrices.
- Revalidated promoted main: fcdac252974aeeded6961dbe3310677e234a6495.
- Revalidated starting B1 HEAD: 23a7624374418991fe700c2817150f67c5bd48fb.
- Only original B1 additions: this PLAN.md and element_cases.json. No parallel branch advance was found at the starting check.
- Frozen ROSS: petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d.
- Executed generator/audit commit: d8a4cb58f4472f7577bb79f0cf7e47771b10dd11.
- Reviewed policy/verifier commit: a1369ba8066ea40f79c86057b6ec824e5520fbf1.
- First immutable publication commit: a9a9b529f09958a2795b628535549a78d575dbd9, parent a1369ba8066ea40f79c86057b6ec824e5520fbf1.

The first-freeze job revalidated live main and B1 HEAD, used a normal non-force push, and staged only additions inside the new authority directory. It copied the reviewed first Linux candidate rather than regenerating replacement output. No history was reset/rebased and no other B1 branch was created.

The A8 parent d4c901e1e8b7261f1f175b78179923607789238a and A5 corrective main remain inherited. The four previously closed A8 main-push gates are M7 36702426397, Stage 1 Final 36702426462, G14 36702426461 and B13-B18 Integrated 36702426500. They are historical A8 evidence, not B1 authority executions.

## 3. Actual frozen ROSS provenance

The generator requires an explicit --ross-root, checks the exact ROSS HEAD and clean tracked/index state, requires core.autocrlf=false and core.eol=lf, and compares raw working bytes against Git blob bytes before importing the mandatory sources. After actual object execution it inventories all imported ROSS modules, profiles executed ROSS source files and repeats source verification. It does not accept a site-packages ROSS implementation outside the supplied root.

Actual initial import roots:

    Linux:   /home/runner/work/RotorStudio/RotorStudio/_ross_b1
    Windows: D:\a\RotorStudio\RotorStudio\_ross_b1

The generation authority.json contains 52 source/resource records, including the five required Python files, runtime unit definitions, imported transitive modules, material data and dependency declarations. Raw SHA256 is recorded separately from each Git blob ID. Every recorded source has Git blob SHA256 equal to checkout SHA256. Runtime paths are preserved as provenance; cross-platform comparison normalizes only the different root prefixes, not physics or source bytes.

| Required source/resource | Raw SHA256 |
|---|---|
| ross/shaft_element.py | 46d6bdf328dad4958a3b3398c28c8424c6057775ff461a646627339104cb89f6 |
| ross/disk_element.py | 6ff37f5188bc8eff9d8961cdd326496f7b8de2255f01a70655894584b6fa3d53 |
| ross/materials.py | fae027debec61926a216916915ee7edb51850727293ced3c8381719b2625b8e8 |
| ross/element.py | 0f64954444aab624aad3f0be78f92e254655ec01e89a9b3e57263cee5d25bd23 |
| ross/units.py | d3bef81b1216e4eeb1a6300ce1a8dc0c16707f37ba45e729d42d6a473a74a39d |
| ross/new_units.txt | b3e6c4e71bb067db02e0c6ecbb9276a7ab9154dd8c2d7007ddc71896871247f9 |

Function ranges were obtained at runtime using inspect.unwrap and inspect.getsourcelines; these are observed ranges, not generator hard-coded authority locations:

| Source | Function | Lines |
|---|---|---|
| shaft_element.py | __init__ | 143-308 |
| shaft_element.py | dof_mapping | 474-513 |
| shaft_element.py | M | 515-712 |
| shaft_element.py | K | 714-905 |
| shaft_element.py | Kst | 907-946 |
| shaft_element.py | G | 977-1075 |
| disk_element.py | __init__ | 56-68 |
| disk_element.py | dof_mapping | 169-196 |
| disk_element.py | M | 198-232 |
| disk_element.py | Kdt | 260-293 |
| disk_element.py | G | 321-354 |
| materials.py | __init__ | 61-101 |

The decorated constructors also record their real runtime wrapper at units.py:130. Dependency evidence includes separate Linux/Windows pip freeze --all and actual pip check PASS. Initial Python versions were Linux 3.12.14 and Windows 3.12.10; both used NumPy 2.5.3 and SciPy 1.18.1 in newly created virtual environments.

The transitive ccp import emitted a REFPROP-unavailable warning and selected HEOS/CoolProp. This warning is retained; it is not claimed that unrelated thermodynamic imports are absent. The reference generator's primary outputs come exclusively from the declared element methods. GitHub Actions also emitted action-runtime deprecation warnings, which were not suppressed to obtain a clean-looking log.

## 4. Generator and unchanged physical inputs

Generator: validation/ross_parity/generate_6dof_elements_reference.py.
I/O/provenance helper: validation/b1/authority_common.py.
Independent output inspector: validation/b1/inspect_candidate.py.
Read-only numerical verifier: validation/ross_parity/verify_6dof_elements_candidate.py.

The generator constructs actual ross.Material objects with name, rho, E and G_s, supplying exactly two elastic constants. Effective Poisson is read from the resulting object, never provided as a third constant. Each shaft copies shaft_base, applies shallow case overrides and resolves its own material; it records effective diameters, actual constructor attributes, unavailable attributes, flags and DOF mapping. Mass is recorded under its real source attribute m. Disk objects are constructed directly with n/m/Id/Ip.

The seven direct source method-call sites are ShaftElement M/K/G/Kst and DiskElement M/G/Kdt. There are no copied ROSS matrix coefficient equations, np.linalg calls, alternate element solver or drm_core/native fallback in the generator. AST tests check the real constructor/method calls and absence of literal NumPy matrix construction. Independent scalar/energy diagnostics use NumPy linear algebra only in the separate validation inspector.

Input specification: validation/b1/element_cases.json, exactly unchanged from starting HEAD 23a7624374418991fe700c2817150f67c5bd48fb. Its execution_status is intentionally retained as a historical initial-specification field so the input hash is not rewritten after generation. Actual execution state belongs to this plan, FREEZE_RECORD.json and CI evidence. No case value was changed because of an inconvenient result.

Executed inventory: 26 shafts x 4 matrices = 104; 3 disks x 3 matrices = 9; total 113 PRIMARY matrices. The existing cases cover all eight independent effect-flag combinations, solid/hollow/thin sections, distinct lengths/materials, Cowper/Hutchinson, forward/reverse cones, signed axial force/torque, combined conical loading and density-only scaling. S25 is a changed cylindrical-section parameter sentinel, not a globally assembled stepped rotor.

## 5. DOF, data storage and lateral preparation

Node order: [x,y,z,alpha,beta,theta]. Shaft local order is this sequence for node 0 followed by node 1. Each shaft output is 12x12; each disk output is 6x6.

| Selection | Zero-based ROSS/Python | One-based future Fortran |
|---|---|---|
| Lateral | 0,1,3,4,6,7,9,10 | 1,2,4,5,7,8,10,11 |
| Axial | 2,8 | 3,9 |
| Torsional | 5,11 | 6,12 |

Arrays are individual deterministic NPY v1.0 files with little-endian float64 and Fortran-contiguous storage. Row/column indices retain the physical DOF order; converting storage never transposes a physical matrix. Each file and its raw F-order values have separate SHA256 hashes. NaN/Inf, wrong dtype/shape, missing/duplicate/unexpected cases or matrices fail closed.

For the 21 eligible cylindrical Cowper cases, direct M/K/G lateral selections are stored separately: 63 supplementary arrays. Therefore there are 176 NPY files, but only 113 primary element matrices. No Hutchinson or conical equality with legacy circular elements is claimed. No V2/M6 golden was altered and no native legacy numerical cross-check has yet been executed. Kst is not compared with legacy K1.

## 6. Candidate inspection: actual output, not assumptions

Initial execution on both platforms passed 670 independent checks per candidate, with zero failures. The machine-readable inspection.json contains per-case matrix minima/maxima, finite/dtype/shape/nonzero counts, symmetry/skew residuals, structural zero violations, length-scaled rank/eigenvalue diagnostics, derived geometry, source/output hashes and every individual check.

Observed behavior:

- All M symmetry residuals and G skew residuals were exactly zero. M was positive definite for the declared nondegenerate fixtures after the documented coordinate scaling.
- Torque-free K was symmetric. Loaded torque cases remained nonsymmetric; the signed same-node terms K[3,4]=-T/2 and K[4,3]=+T/2 were checked rather than symmetrized.
- G was exactly zero with gyroscopic=False. Kst remained nonzero and identical across otherwise-equivalent flag combinations S02-S09. Kst is neither assumed symmetric nor replaced by legacy K1.
- Removing the lateral rotary mass or shear effect did not remove the torsional mass/stiffness blocks. Effective phi followed the actual shear flag.
- S20/S21 and S22/S23 verified signed axial/torque additions. S26 versus S02 verified density scaling of M/G/Kst and unchanged K.
- Disk mass diagonal, two signed gyro entries and the single Kdt[4,3]=Ip entry matched their independent direct-input identities.
- The unstressed cylindrical baseline passed three rigid translations, rigid torsion and the two lateral rigid rotations (positive alpha gives y1=-L*alpha; positive beta gives x1=L*beta), with six elastic directions. Axial/torsional energy identities and rigid translation mass passed.

The actual conical source uses endpoint-mean area and polar section moment in its axial/torsional blocks. Independent validation retained that convention, rather than substituting exact-frustum integration:

| Cases | Axial rigid-motion mass kg | Constructor geometric mass kg | Ratio |
|---|---:|---:|---:|
| S17 | 2.8333640719196955 | 2.7137590942365613 | 1.0440735428347894 |
| S18/S19/S24 | 2.6077777604611208 | 2.509581366061506 | 1.0391285956006768 |

These differences were inspected before freeze. They are documented source discretization behavior, not a generator repair or physical validation of all possible geometries. Positive-semidefinite K and unstressed rigid-motion expectations were not indiscriminately imposed on compressive/torque-loaded cases.

## 7. Pre-native tolerance policy

Reviewed template: validation/b1/TOLERANCE_POLICY.json.
Immutable copy: validation/ross_parity/6dof_elements/tolerances.json.
Policy commit a1369ba8066ea40f79c86057b6ec824e5520fbf1 precedes first freeze and every native B1 implementation/comparison.

Every entry is compared independently by abs(candidate-reference) <= atol + rtol*abs(reference), with exact zero/nonzero masks separate. There is no global absolute tolerance set by the axial stiffness.

| Blocks | rtol | atol |
|---|---:|---:|
| Shaft M lateral; K lateral; G; Kst | 9.094947017729282e-13 (4096 epsilon) | 0 |
| Shaft M axial/torsional; K axial/torsional | 1.1368683772161603e-13 (512 epsilon) | 0 |
| Shaft axial-load addition | 9.094947017729282e-13 | 0 + entrywise subtraction floor |
| Shaft torque addition | 1.1368683772161603e-13 | 0 + entrywise subtraction floor |
| Disk M/G/Kdt direct assignments | 0 | 0 |
| Constructor-derived numeric metadata | 5.684341886080802e-14 (256 epsilon) | 0 |

The load-addition floor is fixed in advance as 16*epsilon*(abs(K_loaded_reference[i,j])+abs(K_base_reference[i,j])). It applies only to the corresponding lateral entries of the loaded-minus-baseline comparison, not to a norm of the full matrix. Input values, flags, names and DOF maps are exact.

The JSON distinguishes kg / kg*m / kg*m^2 inertial entries and N/m / N / N*m stiffness entries by generalized row and column. Bounds reserve binary64 scalar-arithmetic headroom for these reviewed finite fixtures; they are not a uniform conditioning proof for degenerate geometry. A future native failure requires diagnosis, never automatic tolerance widening.

## 8. Immutable first freeze and hashes

Directory: validation/ross_parity/6dof_elements/.
First publication: a9a9b529f09958a2795b628535549a78d575dbd9.
Actual freeze time: 2026-09-30T11:55:34.365716+00:00.

194 files were added: 113 primary NPY arrays, 63 lateral NPY arrays, authority/case/input metadata, requirements and pip-check evidence, inspection, frozen policy and review, the freeze record, seven initial-reproduction/Windows-provenance files, local .gitattributes and SHA256SUMS.json. The NPY files are marked -text; evidence retains its recorded bytes. Each frozen file except the checksum index itself is listed in that index. Post-freeze tests pin the index's own SHA256 and compare every frozen path to the first-publication Git commit.

| Identity | SHA256 |
|---|---|
| Data bundle (input/cases/array inventory) | 5601990610bd1a06cec124c1f071d5d13d3768d24760e98581952ae86f335ce0 |
| authority.json, original Linux first candidate | 1c5819b06df134bbaaa374c2106fa0bc695be6f131a7ab12a554045479d1d03b |
| SHA256SUMS.json | 86e80775aab32b904ba48a7d7ba64954a3cfabad79cf835e808bf49077ffe847 |
| tolerances.json | 882e323801379435d18cefed92db302424a37016b2d4de8e742c1e289a51a96c |
| Generator | 8ba45b99eca02d10959118aa7fd8448e9cb2ef8b8fd6ec46d444bdc96d24e074 |
| element_cases.json | 8b4b21c2450b46082a6915d89a911e06491a9d9f7bb04b28d4a367b6c06d4d0e |
| Independent inspector | 3fda0f3a1ea7077d1d5483c7124220d313819bafb8196f3134d787c3c91bfc06 |
| FREEZE_REVIEW.json | 3a562b6e2114b72a9b533a997e55c38f8a8271c4bc1c0bfcfef4c47e8dac496c |

The publication-only workflow was retired after the successful first freeze. The retained freeze script refuses an existing authority before accessing a token or downloading anything. The regular authority workflow has read permissions only and cannot commit, push, regenerate in place or overwrite goldens.

## 9. Executed generation, review and publication evidence

| Run | Exact workflow HEAD | Actual result/scope |
|---|---|---|
| 36710089212 | d8a4cb58f4472f7577bb79f0cf7e47771b10dd11 | Linux/Windows candidate generation, inspection, 21 tests per platform, independent repeat and aggregate PASS |
| 36711495149 | a1369ba8066ea40f79c86057b6ec824e5520fbf1 | Two-platform candidate-only comparison workflow and aggregate completed/success; this HEAD predates the committed frozen directory |
| 36711495229 | a1369ba8066ea40f79c86057b6ec824e5520fbf1 | First reviewed-copy publication job 109874114771 PASS, 38 tests passed, commit a9a9b529f09958a2795b628535549a78d575dbd9 published |

Initial candidate jobs: Linux 109869533976, Windows 109869533673, aggregate 109870461937.

Reviewed Actions artifacts were downloaded and their actual ZIP bytes checked before extraction/copy:

| Artifact | ID | SHA256 of outer artifact ZIP |
|---|---:|---|
| Initial Linux | 11093976663 | 23ce276fd2b59e5f557d00bcd4e164b37e424bcf734e7f5adf79f507f2b8f687 |
| Initial Windows | 11093482540 | a0959edbdf4fe43b3be49916c867d598ea99d316ee5c45323277c170df7c7be2 |
| First-freeze execution evidence | 11094257985 | 6c9714004362a23d3031a4ea52fd27f4704515e90a3f7ad28240a1f2fca0f209 |

Actual reviewed first Linux versus Windows comparison, both independent repeats, and the post-copy frozen-versus-Windows comparison passed. All 113 primary matrices and 63 lateral selections had equal NPY bytes and equal raw F-order value bytes. Maximum absolute and relative differences were 0.0 in every compared block and signed-load addition; physics metadata and 52-source/12-function provenance matched. Environment/timestamp/root-path provenance is recorded separately and is not required to have identical JSON bytes.

The first Linux authority.json and all of its candidate files were copied without modification. The frozen initial_reproduction reports are historical comparison evidence on a1369ba..., not fabricated fresh execution on a later HEAD. The exact post-publication workflow results must be read from that later run's artifact summaries.

## 10. Read-only CI and negative guards

Workflow: .github/workflows/b1-6dof-authority.yml, named Freeze / Reproduce B1 6DOF Element Authority. It checks out the exact B1 SHA and exact ROSS SHA on Ubuntu 24.04 and Windows 2025, creates a clean venv, runs pip check, generates separate candidates, audits actual matrices, runs nonempty JUnit-checked tests, independently repeats generation, verifies immutable integrity and compares every matrix. The aggregate downloads both matching-HEAD artifacts, verifies run/HEAD provenance and compares the actual Linux/Windows arrays again.

Post-publication tests require the frozen directory, pin SHA256SUMS.json, check all frozen files against the first-publication commit and reject corrupt/missing/extra data, tolerance/provenance edits and self-consistently rewritten auxiliary evidence. The numerical-comparison tests already demonstrated rejection of transposed Kst, a 1e-300 forbidden zero entry, small torsional errors hidden by a deliberately unsuitable global bound, torque sign errors, disk inertia swaps, inconsistent or self-consistently forged source metadata, imported modules outside the ROSS root and changed derived phi. Permitted rounding and signed-zero byte differences are not misclassified as physical failure.

A valid reproduction must leave both frozen reference and generated candidate unchanged. The generator refuses immutable output paths; the verifier refuses reference-overwriting report paths. A failed comparison never updates a golden or changes a tolerance.

All files present in promoted main, including A0-A8 references, Fortran, Python production/tests, V2/M6 inputs and existing workflows, remain unchanged. Only additive B1 authority/validation work and the existing B1 plan are changed relative to its starting branch. The Stage 1 exact 57-test collection is not expanded or falsely reported as rerun by this authority-only task.

Commands used inside the checked-out CI workspace are reproducible without a native library:

    python validation/ross_parity/generate_6dof_elements_reference.py --ross-root _ross_b1 --out b1-evidence/candidate
    python validation/b1/inspect_candidate.py b1-evidence/candidate
    B1_CANDIDATE=b1-evidence/candidate python -m pytest validation/b1/tests -q
    python validation/ross_parity/verify_6dof_elements_candidate.py --candidate b1-evidence/candidate --report b1-evidence/reproduction.json

These commands describe GitHub execution, not execution on Leonardo's local host. The chat runtime was unavailable, so no local execution claim is made.

## 11. Remaining native plan — NOT_STARTED

After the authority gate is closed and a separate continuation is authorized, implement additive Fortran 2018 shaft/disk element modules, their geometry/material preparation and versioned rd_shaft_6dof_matrices_v1 / rd_disk_6dof_matrices_v1 exposures. Do not call the legacy 4-DOF routine to manufacture the new matrices or replace any existing 4-DOF assembly/path. Choose and document the least invasive additive build integration; no CMake or production change is made in this authority-only task.

Future ABI inputs remain explicit SI scalars/flags/shear method. Each shaft output needs 12x12 doubles and each disk output 6x6, with declared leading dimensions, capacities, column-major order, status and finite-input/output checks. Tests must use actually allocated guard buffers; a raw pointer does not reveal its true allocation to the callee. Future Python remains a thin checked binding, not a second matrix solver.

Retain exact ROSS geometry distinctions (end areas/inertias, midpoint properties, taper coefficients), independent flags, endpoint-mean axial/torsional convention, signed nonsymmetric torque and independent Kst. Do not carry the legacy G_s=0 no-shear convention into torsional stiffness. Document any input-domain restriction beyond the observed source contract, including zero-inertia limits; PointMass, disk-from-geometry and flexible disks are not implicitly covered.

The future native qualification must compare every matrix to these immutable references, run independent invariants and native CTest/ABI guards on the same exact Linux/Windows HEAD, then compare the common cylindrical Cowper lateral scope with the preserved V2-qualified circular element exposure. The existing stype map is 1=(no shear,no rotary,gyro), 2=(shear,rotary,gyro), 3=(shear,rotary,no gyro), 4=(shear,no rotary,gyro), 5=(no shear,rotary,gyro), 6=(shear,no rotary,no gyro), 7=(no shear,rotary,no gyro), 8=(no shear,no rotary,no gyro). Kst is not legacy K1. Any discrepancy must be explained, not forced away by a transformation or changed golden.

Only that complete native chain may receive B1_6DOF_ELEMENT_MATRICES_ROSS_PARITY=PASS and ENGINEERING QUALIFIED FOR DECLARED SCOPE. Global 6-DOF assembly/modal/Campbell (B2), axial/torsional product workflows (B3), misalignment, rubbing, cracks and harmonic-balance/fault work remain outside this task.
