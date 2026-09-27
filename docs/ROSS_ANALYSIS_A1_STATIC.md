# A1 Static qualification

A1_STATIC_ROSS_PARITY = BLOCKED (pending same-head CI and both frozen executables).
Local numerical/GUI evidence is PASS. This file defines the committed scope and gates;
the PR records final exact-head run URLs and verdict after CI, without a self-referential
qualification SHA documentation commit. A2 remains BLOCKED_BY_A1.

## 1. A0 closure

Old head: f07dc86b62652bb92cc3d2e0af20c972fec0b67e.
Closure head: 5f8d5e2559f697e24ce0fbeabde8073451d1332b.
Merged PR #22: a44c5aa3f521a84785f9b020db9e119e9d1e25a2.
All 16 applicable workflows passed independently on both old and closure heads.
See PR #22 and ROSS_ANALYSIS_A0_QUALIFICATION.md for the matrix.

## 2. A1 baseline

Main baseline a44c5aa3f521a84785f9b020db9e119e9d1e25a2;
branch feature/ross-analysis-a1-static.
Authority petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d.

## 3. Scope

Single ordered circular shaft chain, solid/hollow, stepped sections; Euler-Bernoulli
and Cowper Timoshenko, optional rotary inertia (legacy types 1..8); multiple disks,
no disks, overhangs and two or more distinct radial supports. Disk types 1..4 are
accepted, including inertial disks with zero inertia as concentrated shaft masses.
Every non-seal legacy support becomes a 1e20 N/m radial penalty in x/y; original
rotational restraints and stiffness/damping are not retained. Type 8 seals are excluded.
External dynamic force definitions are not part of gravity loading. Gravity is fixed.

Out of scope and fail closed: tapered/asymmetric/branched shafts, axial preload,
torque, pre-bend, coaxial models, advanced bearings and linked supports.
Generic ROSS PointMass/housing/link DOFs are not represented by the domain and are
not claimed: the attempted interior PointMass authority case was singular in pinned
ROSS run_static. The separate mass_disk reference uses an actual zero-inertia
DiskElement, not a relabeled PointMass result. No A2 code.

## 4. Source authority

| ROSS source | Method/class | Fortran mapping |
|---|---|---|
| rotor_assembly.py | Rotor.run_static | rd_static.static_solve: gravity, support replacement, load recovery |
| results.py | StaticResults | q/reaction/weight/station/shear/bending output contract |
| utils.py | remove_dofs | existing lateral x,y,alpha,beta assembly |
| shaft_element.py | ShaftElement.M/K | unchanged rd_shaft circular formulas, 24 full-matrix sentinels |
| disk_element.py | DiskElement.M | unchanged assembly; global M and gravity-vector parity |
| bearing_seal_element.py | BearingElement/SealElement | replacement radial supports / seals excluded |

Original A0 golden files are unchanged. Additional static_extended files were produced
only by the pinned ROSS checkout, with source/data SHA256 manifest. CI regenerates
into a separate candidate directory and compares at rtol/atol 1e-12.
Apache attribution/license: third_party/ROSS_NOTICE.md and ROSS_LICENSE.md.

## 5. Fortran implementation

rd_static.f90 forms Fg=M*a, with a_y=-9.8065 m/s², then solves Kp*q=Fg by
rd_lapack.solve_real/DGESV. No inverse. Kp=K0+radial penalties. Reactions are
(K0*q-Fg)_y at support nodes. Shaft/disk weights and repeated-end-station shear and
moment recovery are native. Force/moment balance and infinity-norm backward residual
are returned. test_static.f90 checks analytic simply supported deflection, multiple
disks, stepped/overhung, three supports, seal exclusion, invalid/no supports,
singular one-support topology, NaN and invalid geometry. All legacy source/tests are
byte-identical after removing the additive rd_static_v1 declaration/function; CI proves
this against promoted A0 rather than falsely requiring zero new Fortran files.

## 6. ABI

`int rd_static_v1(nn,z,ns,shaft,nd,disk,nb,bearing,q,reaction,sw,dw,shear,bending,station,diagnostics)`.
Counts are by-value C int; all arrays are double pointers. Inputs: z(nn),
shaft(11,ns), disk(6,nd), bearing(34,nb), column-major; ns=nn-1, 2<=nn<=1000.
Shaft columns use existing legacy row order; connectivity is consecutive one-based.
Outputs: q(4*nn), reaction(nn), sw(ns), dw(nd), shear(2*ns), bending(2*ns),
station(2*ns), diagnostics(3). DOFs per node x,y,alpha,beta. Positions/displacements
in m, rotations rad, forces N, moments N m. Weights positive downward magnitudes;
reactions positive y upward; shear/moment signs and duplicated stations follow ROSS.
Diagnostics: sum reaction-total weight; axial moment balance; scaled infinity residual.
Status: 0 success, 10 invalid input, 20 unsupported, 30 singular/solve failure.
Caller must provide valid allocated buffers, including zero-length disk buffers when nd=0.
On failure outputs must not be consumed. Missing native symbol fails closed, no Python fallback.

AnalysisService -> run_static -> SolverFacade -> FortranBackend -> ABI. Python only
validates, marshals and wraps outputs. StaticResult preserves all arrays and solver
version, hashes, build metadata and authority. GUI consumes the service through its
normal worker. NPZ retains every result array and JSON metadata; CSV uses explicit
entity rows (node/station/shaft/disk), NaN for nonapplicable columns. Plot/report exports
follow existing APIs. Project persistence stores inputs/case and recomputes results;
existing hash-based staleness is reused.

## 7. Numerical parity

Machine-readable complete 56-row parity table: validation/reports/a1_static_local.json.
Values shown are the component with largest absolute error per case/quantity; the
maximum relative error is independently taken over the whole array, using atol as
the near-zero denominator floor. Empty disk arrays are explicitly empty, not missing.
CI emits the same report per OS. Tolerances: rtol=1e-8; displacement atol=1e-13 m;
weights/reactions/shear 1e-8 N; moment 1e-8 N m; station 1e-14 m. These retain the
A0 relative bound and add dimensional floors well below engineering resolution.
They are not increased to accommodate failures. Full local errors appear below.
Matrix sentinels use rtol=1e-10, atol=1e-12; assembled K uses atol=1e-7 N/m for
roundoff in summing large entries, with all nonzero terms also bounded relatively.

## 8. Independent physics gates

Force and moment residuals <1e-8 N / N m, scaled backward residual <1e-14.
The 1e20 penalty produces condition numbers about 1.44e15; a tiny backward residual
alone does not demonstrate forward accuracy. Validation separately removes constrained
DOFs and solves the reduced authority K/F system: condition numbers about 5.5e3–6.7e3,
with native versus eliminated vertical displacements differing by <4e-18 m in the
extended cases. This validation-only solve is never a production fallback. These
observations qualify tested geometries, not arbitrary ill-conditioned engineering models.

## 9. Regression

Local: 7/7 CTest; 57 Stage 1 tests; 59 existing UI tests; dedicated Static suite.
All inherited G14, bearings/B13–B18, DyRoBeS, Stage 1/2 workflows are required on the
PR head. A1 dedicated workflow builds Release and tests native parity/service/GUI on
Linux and Windows. Original A0 values/tolerances/authority SHA remain unchanged.

## 10. Platforms

Linux local source/native/GUI PASS. Windows and both frozen executable gates must
pass in CI before final qualification. The existing packaged smoke now additionally
drives Static GUI input -> worker -> plots/exports -> save/close/reopen/recompute ->
staleness, and fails the packaged process if any assertion fails. It emits
PACKAGED_SMOKE.json.static_analysis. No source-tree numerical fallback is permitted.

## 11. Limitations

Scope exclusions above; no generic PointMass/housing/link support. Dense solve and
penalty conditioning limit large or poorly scaled models. No claim of arbitrary-model
forward accuracy. GUI draws native nodal displacement samples without interpolating
an additional beam solution. Weight markers represent resultant element weights.

## 12. Qualification verdict

BLOCKED until same-head Linux/Windows native and frozen CI and inherited gates finish.
Final PR evidence determines PASS/FAIL/BLOCKED for that exact head.

## 13. Next permitted PR

A2 General FRF remains BLOCKED_BY_A1 until A1 is qualified and promoted. Stop at A1.

## Local numerical component evidence

| Case | Quantity | ROSS | Fortran | Max abs error | Max rel error | atol | Status |
|---|---|---:|---:|---:|---:|---:|---|
| uniform | displacement_y_m | -0.000308041622 | -0.000308041622 | 5.0415401e-18 | 2.11049732e-14 | 1e-13 | PASS |
| uniform | bearing_reactions_N | 224.90725 | 224.90725 | 3.63797881e-12 | 1.61754626e-14 | 1e-08 | PASS |
| uniform | shaft_weight_N | 225.572533 | 225.572533 | 2.84217094e-14 | 1.25998095e-16 | 1e-08 | PASS |
| uniform | disk_weight_N | 120.61995 | 120.61995 | 0 | 0 | 1e-08 | PASS |
| uniform | shear_force_N | -187.311828 | -187.311828 | 5.00222086e-12 | 1.53830305e-13 | 1e-08 | PASS |
| uniform | bending_moment_Nm | -49.402643 | -49.402643 | 2.43005616e-12 | 4.91887885e-14 | 1e-08 | PASS |
| uniform | x_m | 0 | 0 | 0 | 0 | 1e-14 | PASS |
| stepped_overhung | displacement_y_m | -9.93605442e-06 | -9.93605442e-06 | 8.97854924e-20 | 1.3078345e-13 | 1e-13 | PASS |
| stepped_overhung | bearing_reactions_N | 297.200538 | 297.200538 | 5.68434189e-14 | 2.30734083e-16 | 1e-08 | PASS |
| stepped_overhung | shaft_weight_N | 200.71444 | 200.71444 | 0 | 0 | 1e-08 | PASS |
| stepped_overhung | disk_weight_N | 69.62615 | 69.62615 | 0 | 0 | 1e-08 | PASS |
| stepped_overhung | shear_force_N | -181.724872 | -181.724872 | 2.27373675e-13 | 5.86197757e-06 | 1e-08 | PASS |
| stepped_overhung | bending_moment_Nm | 1.73720926 | 1.73720926 | 7.10542736e-14 | 1.45483146e-13 | 1e-08 | PASS |
| stepped_overhung | x_m | 0 | 0 | 0 | 0 | 1e-14 | PASS |
| three_supports | displacement_y_m | -4.81503466e-06 | -4.81503466e-06 | 5.08219768e-21 | 1.05548517e-15 | 1e-13 | PASS |
| three_supports | bearing_reactions_N | 62.5252962 | 62.5252962 | 4.26325641e-14 | 6.81845057e-16 | 1e-08 | PASS |
| three_supports | shaft_weight_N | 225.572533 | 225.572533 | 2.84217094e-14 | 1.25998095e-16 | 1e-08 | PASS |
| three_supports | disk_weight_N | 120.61995 | 120.61995 | 0 | 0 | 1e-08 | PASS |
| three_supports | shear_force_N | -24.9298741 | -24.9298741 | 2.7000624e-13 | 2.13181647e-14 | 1e-08 | PASS |
| three_supports | bending_moment_Nm | -8.80715461 | -8.80715461 | 1.42108547e-13 | 1.61355799e-14 | 1e-08 | PASS |
| three_supports | x_m | 0 | 0 | 0 | 0 | 1e-14 | PASS |
| timoshenko_hollow | displacement_y_m | -1.01097516e-05 | -1.01097516e-05 | 1.69406589e-20 | 4.36110916e-15 | 1e-13 | PASS |
| timoshenko_hollow | bearing_reactions_N | 291.227646 | 291.227646 | 1.70530257e-13 | 5.85556552e-16 | 1e-08 | PASS |
| timoshenko_hollow | shaft_weight_N | 191.186256 | 191.186256 | 0 | 0 | 1e-08 | PASS |
| timoshenko_hollow | disk_weight_N | 69.62615 | 69.62615 | 0 | 0 | 1e-08 | PASS |
| timoshenko_hollow | shear_force_N | -16.6406361 | -16.6406361 | 8.52651283e-14 | 2.84217094e-06 | 1e-08 | PASS |
| timoshenko_hollow | bending_moment_Nm | 20.6002104 | 20.6002104 | 1.42108547e-14 | 3.67822944e-14 | 1e-08 | PASS |
| timoshenko_hollow | x_m | 0 | 0 | 0 | 0 | 1e-14 | PASS |
| rotary_eb | displacement_y_m | -9.83912843e-06 | -9.83912843e-06 | 6.09863722e-20 | 1.25399758e-13 | 1e-13 | PASS |
| rotary_eb | bearing_reactions_N | 291.227646 | 291.227646 | 1.13686838e-13 | 5.93979045e-16 | 1e-08 | PASS |
| rotary_eb | shaft_weight_N | 191.186256 | 191.186256 | 0 | 0 | 1e-08 | PASS |
| rotary_eb | disk_weight_N | 69.62615 | 69.62615 | 0 | 0 | 1e-08 | PASS |
| rotary_eb | shear_force_N | 5.04404472 | 5.04404472 | 1.0658141e-13 | 2.84217094e-06 | 1e-08 | PASS |
| rotary_eb | bending_moment_Nm | 20.6002104 | 20.6002104 | 6.03961325e-14 | 2.86901896e-13 | 1e-08 | PASS |
| rotary_eb | x_m | 0 | 0 | 0 | 0 | 1e-14 | PASS |
| no_disk | displacement_y_m | -4.15196212e-06 | -4.15196212e-06 | 1.86347248e-20 | 6.92888576e-15 | 1e-13 | PASS |
| no_disk | bearing_reactions_N | 74.6314019 | 74.6314019 | 1.70530257e-13 | 2.28496655e-15 | 1e-08 | PASS |
| no_disk | shaft_weight_N | 191.186256 | 191.186256 | 0 | 0 | 1e-08 | PASS |
| no_disk | disk_weight_N | empty | empty | 0 | 0 | 1e-08 | PASS |
| no_disk | shear_force_N | -63.2457035 | -63.2457035 | 1.84741111e-13 | 7.10542736e-07 | 1e-08 | PASS |
| no_disk | bending_moment_Nm | 1.58086043 | 1.58086043 | 5.86197757e-14 | 3.70809305e-14 | 1e-08 | PASS |
| no_disk | x_m | 0 | 0 | 0 | 0 | 1e-14 | PASS |
| seal_excluded | displacement_y_m | -1.01097516e-05 | -1.01097516e-05 | 1.69406589e-20 | 4.36110916e-15 | 1e-13 | PASS |
| seal_excluded | bearing_reactions_N | 291.227646 | 291.227646 | 1.70530257e-13 | 5.85556552e-16 | 1e-08 | PASS |
| seal_excluded | shaft_weight_N | 191.186256 | 191.186256 | 0 | 0 | 1e-08 | PASS |
| seal_excluded | disk_weight_N | 69.62615 | 69.62615 | 0 | 0 | 1e-08 | PASS |
| seal_excluded | shear_force_N | -16.6406361 | -16.6406361 | 8.52651283e-14 | 2.84217094e-06 | 1e-08 | PASS |
| seal_excluded | bending_moment_Nm | 20.6002104 | 20.6002104 | 1.42108547e-14 | 3.67822944e-14 | 1e-08 | PASS |
| seal_excluded | x_m | 0 | 0 | 0 | 0 | 1e-14 | PASS |
| mass_disk | displacement_y_m | -6.91431539e-06 | -6.91431539e-06 | 3.2187252e-20 | 6.01965116e-15 | 1e-13 | PASS |
| mass_disk | bearing_reactions_N | 139.14939 | 139.14939 | 2.27373675e-13 | 1.63402567e-15 | 1e-08 | PASS |
| mass_disk | shaft_weight_N | 191.186256 | 191.186256 | 0 | 0 | 1e-08 | PASS |
| mass_disk | disk_weight_N | 69.62615 | 69.62615 | 0 | 0 | 1e-08 | PASS |
| mass_disk | shear_force_N | -58.1375415 | -58.1375415 | 2.13162821e-13 | 1.42108547e-06 | 1e-08 | PASS |
| mass_disk | bending_moment_Nm | 20.6002104 | 20.6002104 | 6.03961325e-14 | 2.69679494e-14 | 1e-08 | PASS |
| mass_disk | x_m | 0 | 0 | 0 | 0 | 1e-14 | PASS |
