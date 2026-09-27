# A2 General FRF — implementation and qualification record

A1 promoted by PR #24, qualified head f16133064329d05c7c324dfde65f7d56f70f5e03,
merge/main 1560b7da158b22079a46832f199ae95dd85ee5d6. Seventeen workflows were
revalidated SUCCESS before merge; expected_head_sha guarded the merge. No blockers.
A2 branch feature/ross-analysis-a2-general-frf starts at that promoted main.
A3 remains BLOCKED_BY_A2. A2 status: pending implementation/qualification.

## Authority and convention (audited before implementation)

Frozen petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d.
Source hashes are frozen in validation/ross_parity/frf/authority.json.
Rotor.transfer_matrix forms D=-omega²*M+ j*omega*(C+Omega*G)+K and solves D*H=I.
Rotor._run_freq_response ignores modes in each transfer_matrix call: full order.
Synchronous: Omega=omega; fixed: Omega=speed; free_free overrides both with Omega=0.
free_free does NOT remove bearings. No axial/torsional qualification.
The golden rotor is converted by utils.convert_6dof_to_4dof BEFORE solving, using
run_freq_response on the converted rotor. DOFs [x,y,z,alpha,beta,theta] become
[x,y,alpha,beta] per node. Columns of H are input force/moment DOFs, rows output DOFs.

RotorStudio correspondence: M=M0+Mb; C=C0+Cb; G=C1; K=K0+Kb+Omega*K1.
Declared A2 scope uses zero shaft damping/preload/torque, so C0=0 and K1=0.
D=K0+Kb-omega²*(M0+Mb)+j*omega*(C0+Cb+Omega*C1).
The legacy assemble API returns Ctotal=C0+Cb+Omega*C1; callers MUST NOT add gyro
again to Ctotal. A2 uses primitive assembly directly and adds Omega*C1 exactly once.
Before A2 production coding, test_matrix_authority.py passed all M/C/G/K/Mb/Cb/Kb/D
entries at all sweep points in eight cases using existing native assembly and native
bearing interpolation. This proof is independent of H and prevents hidden cancellation.

## Initial declared scope

Ordered circular Timoshenko shaft chain (type 2), solid/hollow/stepped, geometric or
inertial gyroscopic disks (types 1/2), zero shaft damping/preload/torque. Radial legacy
constant bearings types 3/5 or CoefficientBearing/precomputed maps, including full
2x2 K/C/M, speed axis, frequency axis and 2-D speed-by-frequency axes. B16 native
pchip/linear interpolation is reused; no Python interpolation, no Reynolds/THD/TEHD
solve inside the sweep. Physical bearing objects must first produce an explicit
qualified coefficient table. Rigid constraints, linked/coaxial supports, generic
PointMass, tapered/asymmetric shafts and 6-DOF are outside A2.

The three legacy frequency_response paths retain their names and semantics.
A2 uses general_frf only. It is not an applied-force response (A3).

## Source mapping

| ROSS file | Method | RotorStudio |
|---|---|---|
| rotor_assembly.py | transfer_matrix | rd_dynamic_stiffness + rd_frf_general; ZGESV multi-RHS |
| rotor_assembly.py | run_freq_response / _run_freq_response | native policy 0=synchronous, 1=fixed, 2=free_free |
| rotor_assembly.py | _check_coefficient_axes | existing native interpolation + per-query axis status metadata |
| results.py | FrequencyResponseResults | FrequencyResponseMatrixResult, full complex Hd/Hv/Ha |
| utils.py | convert_6dof_to_4dof | golden conversion before matrix formation and solve |
| bearing_seal_element.py | K/C/M coefficient interpolators | existing AdvancedBearingBackend -> native pchip/linear |

## ABI and memory

`int rd_frf_general_v1(nn,z,ns,sh,nd,di,nb,nodes,nf,freq,policy,fixed,coeff,hr,hi,vr,vi,ar,ai,residual)`.
Integer scalars by value; fixed speed by-value double. Node array C int, one-based.
All other arrays double pointers, Fortran column-major. z(nn), sh(11,ns), di(6,nd)
follow existing legacy element layout; ns=nn-1. coeff(12,nb,nf) contains evaluated
2x2 M, C, K in that order, each flattened column-major. Coefficients are evaluated
by the existing native bearing library at the effective (Omega,omega), never by a
Python interpolation or physical solve. Repeated nodes add contributions natively.
All six response buffers have shape (4*nn,4*nn,nf); each complex response is separate
real/imag buffers. Order is output,input,frequency. residual(nf) is the scaled
infinity-norm DH-I residual. Frequency points retain caller order, including repeated
points. Empty/negative/nonfinite frequency arrays are rejected. No default modal-grid
construction is claimed: frequency_rad_s is required explicitly.

`rd_dynamic_stiffness_v1(nn,z,ns,sh,nd,di,nb,nodes,coeff,speed,w,M,C,G,K,Mb,Cb,Kb,dr,diout)`
exposes the SAME production builder for matrix qualification. The 9 output matrices
are (4*nn,4*nn), with real/imag D separate. G is bare gyro, C excludes gyro; this ABI
never uses legacy Ctotal as if it were bare C.

Status 0=success, 10=input/size/allocation, 20=unsupported scope, 30=complex LAPACK or
nonfinite/numerically failed solve. On any failure discard all output buffers; no
partial result is returned by Python. Native symbol absence fails closed. Native
size limits: 2..128 nodes, 1..10000 frequencies, <=1024 disks, <=2*nn bearings.
Before allocating full responses, Python and Fortran enforce a conservative 512 MiB
budget: 192*(4*nn)^2*nf + 160*(4*nn)^2 bytes, using bounded int64 arithmetic natively.
This includes split response/reconstruction and workspace headroom; external caller
buffers are the caller's responsibility. No selected-only solver replaces full-matrix
qualification. Dynamic force definitions are not consumed; this is receptance, not A3.

## Explicit engineering deviations and limitations

ROSS transfer_matrix replaces NaN H with zeros. RotorStudio rejects singular/nonfinite
systems with status, and explicitly rejects unrestrained zero-frequency rigid motion. ZGECON estimates
reciprocal condition from the existing LU factors; rcond <= ndof*machine_epsilon
is rejected as numerically singular. This catches rigid-body systems that ZGESV
can accept because roundoff leaves tiny nonzero pivots.
This is a deliberate engineering deviation, not strict invalid-case behavioral parity.
An arbitrary near-singular model can still have a small backward error; the solver
has no universal forward-error guarantee. No claim of undamped pole regularization.

The frozen FrequencyResponseResults plotting implementation indexes `[inp,out]`,
whereas the equation D*H=I has output rows and input columns. A2 preserves the entire
ROSS matrix exactly and labels/selects the physical H[output,input] in its GUI/CSV;
it does not claim parity with that plotting argument naming convention. Cross-coupled
cases make this distinction observable. SI units vary with DOF: displacement/rotation
versus force/moment, with velocity/acceleration adding s^-1 / s^-2. Phase is undefined
at zero magnitude and is not treated as a meaningful near-zero scalar comparison.

No axial/torsional modes, direct physical TEHD sweep, modal reduction, rigid/link
supports or applied-force response. Only type-2 Timoshenko shafts are A2-qualified;
A1's broader element acceptance is not silently inherited for dynamic gyro parity.

## Results, GUI and persistence

AnalysisService dispatches only `general_frf` -> SolverFacade -> native ABI. The
legacy frequency_response, auxiliary_frequency_response and foundation_frequency_response
implementations are unchanged. FrequencyResponseMatrixResult preserves three full
complex matrices, both axes, native residual, effective speed policy, DOF convention,
authority, solver version, model/analysis hashes and build metadata. `modes` is recorded
as ignored and the solve stays full-order, matching the authority.

A separate General FRF action exposes synchronous/fixed/free-free policies, excitation
range, input/output DOFs and displacement/velocity/acceleration. Result selectors
plot native matrix components as magnitude, phase and polar response. CSV exports
only the selected pair; NPZ preserves all complex matrices and selected-pair metadata.
Initial setup options and model/case persist; result display selectors are presentation
state, explicitly captured in exported NPZ. Existing project hash staleness is reused.
Source and frozen smoke test real GUI/worker execution, every response export,
complex NPZ equality, plots/report, save-close-reopen-recompute exact equality and
staleness/restoration. Widgets never form D or invert/solve a matrix.

## Tolerance study and numerical gates

Goldens: eight independent cases, six points each, including isotropic synchronous,
fixed Omega, anisotropy, cross-coupling, free_free and independent speed/frequency/2-D
tables. All shafts are hollow Timoshenko with rotary inertia; disk gyro is nonzero.
Zero/low frequency and extrapolated coefficient requests are included. A swapped
Omega/omega test proves K(183,117) != K(117,183); metadata distinguishes constant,
tabulated, interpolated and extrapolated queries. Native pchip handles the 2-D grid.

Matrix comparisons: rtol=2e-12; atol=1e-7 for K/Kb/D and 1e-11 for M/C/G/Mb/Cb.
Large stiffness entries reach approximately 1e8, so the 1e-7 floor addresses a few
floating-point addition ulps without permitting a gyro/coefficient-axis/sign change.
Hd rtol=1e-9, atol=1e-13; Hv atol=1e-10; Ha atol=1e-7, with the same rtol.
Floors are in each entry's SI response/input units; derivative floors account for
omega and omega² amplification across the tested sweep up to 650 rad/s. Real and
imaginary parts are tested separately, not only magnitude. Magnitude has Hd's bound;
wrapped phase error <1e-8 rad is tested only where reference |Hd|>1e-11, avoiding
meaningless phase of near-zero entries. Independent identities Hv-j*omega*Hd and
Ha+omega²*Hd have 1e-12 absolute verification floors; DH-I scaled residual <1e-12.

Local primitive D condition numbers are <=3.545e4. The report additionally studies
0.999/1/1.001 times the first undamped frequency (~330.086 rad/s) at Omega=183,
using the frozen primitive M/C/G/K and an independent validation-only complex solve.
This is a near-resonance numerical study, NOT a Python production fallback or a newly
invented ROSS golden. Every CI OS repeats it; no tolerance is increased on failure.
Machine-readable evidence: validation/reports/a2_general_frf_local.json (720 matrix/
complex component rows, conditions, phase/magnitude and independent residuals).

## Regression and platform gates

Local 8/8 CTest. Stage 1 57 and existing UI 59 remain unchanged. A1 Static 28 tests
pass on the A2 library. Dedicated A2 suite has 35 tests. The legacy-preservation gate
now compares against promoted A1 and strips ONLY the two additive A2 ABI functions,
proving every A1/legacy source and native test remains byte-identical.

ROSS Analysis A2 General FRF Qualification builds Release, runs all dedicated/native/
A1/Stage 1 tests and numerical study on Linux and Windows. Pinned ROSS regeneration
runs separately against immutable goldens. Inherited G14, bearings, B13-B18 and Stage 2
remain required. Both clean frozen executables run General FRF AND Static smoke, with
explicit payload assertions. Exact-head final run URLs and verdict belong to the PR
closure record; this committed document is the pre-CI implementation/evidence snapshot.

## Qualification verdict

BLOCKED pending same-head remote Linux/Windows and frozen gates. The PR final record
will state PASS/FAIL/BLOCKED after all required runs complete. No A2 promotion has
been authorized by this implementation task; A3 stays BLOCKED_BY_A2 until promotion.
