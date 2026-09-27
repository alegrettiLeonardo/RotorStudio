# A3 — arbitrary complex harmonic forced response

## Campaign boundary

A2 PR #25 was revalidated with 18/18 completed-success workflows, exact HEAD
520923e3959398b44658d422d8354d095791ad12, completed Codex review and no blockers.
It was merged with expected_head_sha protection. Real merge and A3 base:
7b87c422691153fc4be3c1d134af4ffcc0af1678. Its parents are promoted A1
1560b7da158b22079a46832f199ae95dd85ee5d6 and that exact A2 HEAD.
No further A2 branch commit was created.

A3 branch: feature/ross-analysis-a3-forced-response.
A4 = BLOCKED_BY_A3_PROMOTION. No A4, new unbalance feature, API 617/684 placement,
clearance analysis or arbitrary time-force solver is introduced.

This document describes implementation and local evidence. Final qualification
requires all applicable remote workflows and both frozen platforms on one exact
HEAD. The PR body is the canonical final remote record; no documentation-only
commit is required to duplicate its final gate matrix.

## Source authority

petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d; source SHA256 inventory
and golden file digests are in validation/ross_parity/forced/authority.json.

| ROSS source | Semantics | RotorStudio mapping |
|---|---|---|
| rotor_assembly.py: run_forced_response | Hdisp/Hvel/Hacc times F at each frequency | rd_forced_response: direct Dq=F, derivative identities |
| rotor_assembly.py: run_freq_response / _run_freq_response | synchronous or fixed speed; full-order despite modes | A2 preparation plus A3 policy 0/1 |
| rotor_assembly.py: transfer_matrix | complex dynamic stiffness and LU | unchanged rd_dynamic_stiffness plus LAPACK solve_complex/ZGESV |
| results.py: ForcedResponseResults | forced_resp, velc_resp, accl_resp | ForcedResponseResult displacement, velocity, acceleration |
| rotor_assembly.py: _unbalance_force / run_unbalance_response | omega-squared forcing generation and wrapper | audited for context; excluded from A3 |

The frozen source explicitly converts each authority rotor to four DOFs before
run_forced_response. No native/Python production result is used to generate goldens.

## Contract and scope

F is complex [ndof,nfreq], ndof=4*nodes, column-major at the ABI. DOF order per
node is [x,y,alpha,beta]. Real is in-phase; imaginary is quadrature. Physical
motion is Re(q exp(j omega t)). x/y forcing is N, alpha/beta forcing is N m;
q is m/rad, v is m/s or rad/s, a is m/s² or rad/s².
Force can excite any combination of qualified lateral DOFs with independent
phase, multiple nodes and a nonproportional arbitrary spectrum. No omega-squared
restriction and no dependency on legacy ForceDefinition/unbalance exist.
JSON parameters store force_real and force_imag as ordinary real nested arrays.
Absent, nonfinite, complex-valued split buffers and incorrect shapes are rejected.

Same model scope as A2: ordered circular type-2 Timoshenko chain, gyroscopic disks,
constant radial bearings or qualified COEFFICIENT_TABLE/MAP_BACKED K/C/M.
Native A2/B16 interpolation is reused for constant, speed, frequency and 2-D axes.
No direct physical Reynolds/THD/TEHD solve inside the sweep. Rigid/linked/coaxial,
asymmetric/tapered/6-DOF, preload/torque/shaft-damping extensions remain excluded.

Synchronous: Omega=omega. Fixed: Omega is held at speed. The A3 API does not
accept free_free; the native ABI rejects policy 2. Explicit frequency_rad_s is
required: the ROSS automatic modal-derived grid is not qualified. modes, if
provided, is ignored and recorded; no modal reduction. Unbalance metadata/API is
not exposed by this first arbitrary-force implementation.

## Numerical implementation

The sole production D builder is unchanged A2 rd_dynamic_stiffness.f90:
D = K - omega² M + j omega (C + Omega G), with evaluated bearing M/C/K included.
A3 allocates only D/LU work matrices and vector outputs, never H(ndof,ndof,nfreq).
For each point LAPACK ZGESV solves D q=F; v=j omega q; a=-omega² q.
No inverse(D), Python solve, H@F production solver or fallback exists.

After the LU solve, ZGECON estimates reciprocal 1-norm condition. Reject when
rcond <= ndof*epsilon, nonfinite result, invalid input, or scaled residual >1e-12.
Returned condition_estimate=1/rcond; it is an estimate, not an exact 2-norm value.
Residual = ||Dq-F||inf / (||D||inf ||q||inf + ||F||inf).
For exact zero forcing in a nonsingular system, denominator and numerator are
zero and residual is defined as zero. Zero force does not bypass the singularity
check. Overflow/nonfinite denominator also fails closed.

Singular rejection is an intentional engineering deviation from ROSS invalid
NaN-to-zero behavior. No parity is claimed for singular/invalid systems.

## Additive C ABI

rd_forced_response_v1(nn,z,ns,sh,nd,di,nb,nodes,nf,freq,policy,fixed,coeff,
                     fd,ff,fr,fi,qr,qi,vr,vi,ar,ai,residual,condition)

Defined in a separate rd_forced_response_c_api module. Existing rd_c_api.f90,
rd_static_v1, rd_dynamic_stiffness_v1, rd_frf_general_v1 and all legacy ABIs are
byte-preserved.

Scalars nn/ns/nd/nb/nf/policy/fd/ff: C int by value; fixed: C double by value.
nodes(nb): C int, one-based node IDs. Other arrays: C double, caller allocated,
column-major and contiguous. z(nn), sh(11,ns), di(6,nd) retain A2 model layouts.
coeff(12,nb,nf) packs 2x2 M, C, K blocks, each in column-major order. Each bearing
block is evaluated by the same native coefficient provider at (Omega,omega).
fr/fi(fd,ff) require fd=4*nn and ff=nf; q/v/a split arrays have shape (4*nn,nf).
residual(nf) and condition(nf) are dimensionless.

Caller must provide valid allocated buffers of the declared sizes; outputs must
be ignored for any nonzero return status. Return 0=success, 10=invalid input or
allocation failure, 20=unsupported model from the A2 builder, 30=singular,
ill-conditioned, nonfinite solution or residual rejection.
Limits: 2..128 nodes, 1..10000 frequencies, <=1024 disks, <=2*nn bearings.
Conservative numerical-buffer budget: 320*ndof*nf + 160*ndof² <=512 MiB, calculated
in int64 after dimension caps. It excludes GUI objects and JSON container overhead.
Only the shared A2 preparation function gains an opt-in vector budget; its
existing default behavior and all A2 output semantics remain unchanged.

## Evidence and tolerances

Thirteen cases: single_x, quadrature_xy, fixed_speed, pure_moment, multiple_nodes,
multiple_dofs, cross_coupled, anisotropic, speed_axis, frequency_axis, map_2d,
phase_sentinel, near_resonance. Nonproportional frequency-varying force includes
137+41j, -23+89j, 17-31j, -11-7j sentinels with independent variation.
Near-resonance axis is frozen near 0.999,1,1.001 times the first undamped mode,
with damping retained and fixed Omega=183 rad/s; no exact singular pole is used.

Initial local complex absolute errors (including near resonance): q <=1.011e-15,
v <=3.338e-13, a <=1.103e-10; A2 H@F q difference <=2.264e-18.
Native scaled residual <=1.402e-16. Sampled native 1-norm condition estimate
<=58401.51. Independent 2-norm condition and both residuals are recorded per point.
These measured errors informed fixed dimensional bounds, not copied A2 matrix
bounds. Components are compared separately (real and imaginary), with rtol 1e-10:

| Quantity | Translational atol | Rotational atol |
|---|---|---|
| q | 1e-13 m | 1e-12 rad |
| v | 1e-11 m/s | 1e-10 rad/s |
| a | 1e-8 m/s² | 1e-7 rad/s² |

Absolute floors cover near-zero components, below declared engineering response
resolution; relative bounds control nonzero components. No tolerance is adjusted
after CI to force a pass. D retains its already-qualified A2 matrix tolerances.

156 real/imag component comparisons cover ROSS and A2 H@F independently, plus
Dq-F, derivative identities, superposition, complex scaling, phase rotation,
zero force, invalid shapes/NaN/Inf, missing ABI, singular zero-force rejection,
axis-swapping sentinel and deterministic project persistence.
Native test includes all unit-force/moment columns, a known single-coordinate
solution reconstructed from D, both speed policies and invalid native dimensions.

## GUI, exports, persistence and frozen

Separate Forced Response action/dialog. Enter node, force/moment DOF and real/imag
components as constants or comma-separated samples. Duplicate entries add. The
specified frequency grid is visible, never silently generated by a modal solve.
All inputs are SI as explicitly labelled; global display-unit preferences do not
change this dialog's contract.
Results: selected node/DOF displacement, velocity or acceleration Bode and polar;
x/y displacement orbit at a selected frequency. Orbit convention is tested at
phase 0 and pi/2. Angular probe projection, deflected-shape interpolation,
bending-moment reconstruction and unbalance overlays are deferred.

NPZ includes frequency/effective speed, full complex F/q/v/a and their explicit
real/imag arrays, native residual, condition estimate, metadata, selection and
hashes. CSV exports one selected response DOF, unit-labelled force at that same
DOF, selected amplitude/phase and q/v/a real/imag; it does not imply that one local
force is the sole contributor to the global response. Full forcing is in NPZ.
JSON/Markdown reports and PNG/SVG/PDF plots use the existing export infrastructure.

Packaged smoke executes the real GUI worker/AnalysisService/native ABI path using
2-D bearings, force and moment entries and arbitrary spectra; checks exports,
closes/reopens the saved project, recomputes F/q/v/a/residual/condition and hashes
with exact equality, and verifies staleness/restoration. Hooked into the existing
clean frozen Linux/Windows qualification alongside Static A1, General FRF A2,
advanced bearings and fluid-film bridge. Source-tree smoke alone is insufficient.

The previously observed Stage 2 GITHUB_SHA metadata defect is corrected here:
source HEAD (event.pull_request.head.sha) now labels both frozen platforms and
aggregate evidence, matching their explicit source checkout rather than the
synthetic PR merge event SHA.

## Preservation and final gates

verify_a2_preservation.py compares every promoted native source/test and A0/A1/A2
golden byte-for-byte (text CRLF normalized only). Legacy Python routes stay
unchanged; regression tests cover their behavior. 9 CTest and 215 Python tests
(A3 36, A2 35, A1 28, Stage 1 57, existing UI 59) passed locally.
Final PASS remains blocked until the exact PR HEAD passes dedicated A3 on both
systems, A0/A1/A2, Stage 1/2, G14, bearings, B13-B18, DyRoBeS and frozen Linux/Windows.
