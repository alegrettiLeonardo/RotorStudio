# A4 — General Time Response F(t)

## Baseline and campaign boundary

Promoted main/base: e2b4a346faf55d5bdb66c826934b829532410fae.
Its second parent is qualified A3 8c522282b2cfd2bb0cf2ffecdfb771eaa1b2925c.
A2/A3 are promoted; no reimplementation or golden regeneration of those stages.
Branch: feature/ross-analysis-a4-general-time-response.
This document records implementation and local evidence, not a remote PASS.
Final exact-head workflow matrix and artifact IDs belong in the PR body, avoiding
an extra documentation-only commit after qualification. Faults remain blocked
until this A4 PR is promoted. No automatic merge is part of this campaign.

## Immutable source authority

petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d.
`validation/ross_parity/time_response/authority.json` freezes the complete source
SHA256 inventory and all case/NPZ digests. `generate_time_reference.py` only imports
that verified checkout; no RotorStudio response is used to create reference data.
Each rotor is explicitly converted from six to four DOFs **before** the ROSS solve.
The call always specifies method="newmark", newmark_type="simple", even for scalar
speed. The default scalar lsim path is not an A4 authority or production solver.

| ROSS source/function | Audited behavior | Native mapping |
|---|---|---|
| rotor_assembly.py:4764 run_time_response | wraps time_response, returns time and q | GeneralTimeResponseResult |
| :3534 time_response | weight force; explicit Newmark dispatch | native gravity, general_time_response |
| :3227 integrate_system | force row per step, full-order identity reduction | explicit F(:,step) |
| :3386 _rotor_system_for_integrate | M once; C/K coefficient queries; Omega G and gradient Ksdt | rd_time_response_general + rd_transient_stiffness |
| :3593 _introduce_weight_force | adds M*g to every force row | native Fe=F+Fg |
| :3190 gravitational_force | g=-9.8065, y DOF | native M*gravity vector |
| :1886 Ksdt | assembled shaft Kst and disk Kdt | assemble_ksdt |
| shaft_element.py:907 Kst | rho*Ie/(15L), nonsymmetric transient stiffness | shaft_kst |
| disk_element.py:260 Kdt | beta-row/alpha-column Ip after reduction | disk_kdt |
| utils.py:736 newmark | gamma .5, beta .25, tol 1e-6, simple path | rd_newmark |
| :905 _converge_simple_newmark | all-zero initial q/v/a, starts at second sample | general_time_response |
| :871 _simple_loop_newmark | reset a, predict, iterate at most 50 corrections | newmark_step |
| :852 _residual_newmark | F-(Ma+Cv+Kq), Euclidean norm convergence | newmark_step |
| :857 _jacobian_newmark | M+gamma*dt*C+beta*dt²*K | newmark_step |
| :862 _update_newmark | acceleration correction and q/v updates | newmark_step |
| tests/test_transient_newmark.py | scalar/history speed and varying coefficients | dedicated matrix/time cases below |

The ROSS tests also contain scopes not claimed here, including model reduction and
shaft damping. Their existence does not confer qualification on A4 extensions.

## Declared scope and force contract

Ordered circular type-2 Timoshenko chain, gyroscopic disks types 1/2, four lateral
DOFs [x,y,alpha,beta] per node. Reuses the qualified native coefficient provider for
constant radial supports and precomputed COEFFICIENT_TABLE/MAP_BACKED bearings.
No direct TEHD/THD/Reynolds solve in time stepping. No rigid/link/coaxial,
asymmetric/tapered/6DOF, axial preload, torque or shaft damping extensions.
Simple Newmark, real explicit F(t), constant scalar Omega or explicit Omega(t),
uniform/nonuniform finite strictly increasing t are supported. No robust Newmark,
nonlinear add_to_RHS, AMB, model reduction, rubbing, crack or misalignment.

F uses [4*nodes,time] in Python/native column-major buffers. ROSS expects
[time,ndof]; the golden generator explicitly transposes at that boundary.
x/y forces are N; alpha/beta moments are N m. q is m/rad, v m/s or rad/s,
a m/s² or rad/s². No implicit unbalance forcing law is imposed.
Optional weight adds M*g with g=-9.8065 at y DOFs. External and effective F are
both returned and exported. No stiffness or mass is silently regularized.

## Ksdt, speed and coefficient policy

For each circular shaft Ie=pi*(od^4-id^4)/64. Reduced Kst nonzero rows 1,4,5,8
and columns 2,3,6,7 are (one-based):

    [-36, 3L, 36, 3L]
    [-3L, 4L², 3L, -L²]
    [36, -3L, -36, -3L]
    [-3L, -L², 3L, 4L²]

multiplied by rho*Ie/(15L). Disk Kdt(4,3)=Ip. Scatter and sum produces global
Ksdt. It is not assumed symmetric and is not legacy K1. In the declared zero
shaft-damping scope K1 is zero, while Ksdt remains nonzero.
Ceff=C+Omega*G and Keff=K+alpha*Ksdt are constructed separately, exactly once.
Shaft/disk element sentinels span multiple L, diameters, solid/hollow and Ip;
assembled rotors use stepped diameters and nonuniform segment lengths.

For speed histories, native gradient matches numpy.gradient(speed,t): first
forward/backward differences at ends; second-order three-point nonuniform
coefficients at interior points. Scalar speed has exactly zero alpha; an array
is deliberately treated as an array, including a constant-valued array.
C/K use the existing native provider at (Omega(t),Omega(t)), including the diagonal
of a 2-D map. Excitation spectrum is never inferred from arbitrary F(t).
For constant coefficients, the ROSS mean-speed reference yields the same base C/K
because shaft damping is excluded. Signed scalar speeds are tested.

ROSS builds M=self.M() once (bearing mass at zero). Therefore A4 rejects varying
bearing mass coefficients. Constant mass arrays are normalized to their scalar
value before native evaluation; zero/constant mass remains valid. Native code
also rejects any stepwise change of supplied mass coefficients. M from the first
assembly is retained; repeated base assembly checks that it remains identical.

## Newmark and failure semantics

Initial q0=v0=a0=0 even when F(t0) is nonzero. Initial equilibrium is not solved;
its residual is returned but excluded from time-step equilibrium gates.
Defaults gamma=.5, beta=.25, tol=1e-6, at most 50 corrections.
Alternate gamma=.6, beta=.3025 is also frozen and qualified. Inputs require finite
positive gamma/beta/tol; arbitrary positive choices are not promised stable.
For each dt:

    a=0
    v=v_previous+(1-gamma)*dt*a_previous
    q=q_previous+dt*v_previous+(.5-beta)*dt²*a_previous
    r=F-(M*a+Ceff*v+Keff*q)
    J=M+gamma*dt*Ceff+beta*dt²*Keff
    J*da=r
    a+=da; v+=gamma*dt*da; q+=beta*dt²*da

Continue while norm2(r)>=tol. LAPACK DGETRF/DGETRS, no explicit inverse. Reuse
only the factorization within the same step; no cross-step reuse. DGECON checks
reciprocal 1-norm condition > ndof*epsilon, including zero-force steps. Invalid,
singular/nonfinite and nonconverged responses fail closed, with no Python fallback.
This conditioning rejection is a deliberate engineering safeguard beyond the ROSS
valid-system parity contract. Static singular K alone does not imply singular J:
a free rotor with nonsingular mass may have a physically valid transient response.

Absolute residual is norm2(F-Ma-Cv-Kq); scaled residual denominator is
||M||inf||a||inf+||Ceff||inf||v||inf+||Keff||inf||q||inf+||F||inf.
The native convergence contract remains the absolute ROSS tolerance. Tiny forcing
below tol can skip corrections; no incompatible universal scaled-residual cutoff
is added. The declared moderate-amplitude golden cases also satisfy scaled 1e-12.
Condition estimate is for J, not for K, and t0 has no solve (condition=0).

## Additive ABI and resource limits

Separate module rd_time_response_c_api exports rd_general_time_response_v1:

    (nn,z,ns,sh,nd,di,nb,nodes,nt,t,speed,variable,coeff,fd,ft,F,weight,
     gamma,beta,tol,q,v,a,alpha,Fe,iterations,residual,absres,condition,failed_step)

C integer counts/flags and double scalar parameters by value; arrays by pointer.
z(nn), sh(11,ns), di(6,nd) retain existing model layout. nodes(nb) are one-based
C ints. coeff(12,nb,nt) contains column-major 2x2 M/C/K per bearing. F(fd,ft)
requires fd=4*nn, ft=nt. q/v/a/Fe(4*nn,nt); speed/t/alpha/residual/absres/condition(nt);
iterations(nt) C int; failed_step C int by reference (one-based, zero on success).
Caller owns valid contiguous buffers. Ignore outputs on nonzero return:
0 success, 10 invalid/budget/allocation, 20 unsupported model, 30 singular/nonfinite,
40 nonconvergence. Error includes failed step, iteration count and residual.

Limits: 2..128 nodes, 2..10000 time samples, <=1024 disks, <=2*nn bearings;
320*ndof*nt+240*ndof² <=512 MiB calculated before native output/work allocation.
Python applies the same guard before marshalling/output allocation. This bound is
for numerical buffers, not JSON or GUI object overhead. Native call is monolithic;
no mid-step cancellation, streaming or restart checkpoint support in this version.

Validation matrix/gradient accessors are separate small native ABIs. A file-based
Fortran driver verified q parity, residual and dt refinement before public time
binding integration. Analytic SDOF is tested directly against the Fortran stepper.

## Local qualification and fixed tolerances

16 immutable cases: harmonic, pulse, arbitrary, multiple_dofs, moment,
cross_coupled, gravity, nonuniform, linear_ramp, nonlinear_speed, speed_axis,
frequency_axis, map_2d, zero_force, constant_mass, alternate_parameters.
Initial measured max q error 2.31e-17; independent absolute equation residual
1.65e-11. Fixed q bounds: rtol=1e-10, atol=1e-12 m and 1e-11 rad, applied by DOF.
Matrix bounds inherit rtol=2e-12, atol=1e-11 except K/Keff atol=1e-7;
alpha atol=1e-8 rad/s²; element Ksdt atol=1e-14. No CI-driven tolerance changes.
ROSS only returns q; v/a are qualified with analytic SDOF, Newmark identities and
independent equation residual, not falsely claimed as ROSS-returned golden arrays.

SDOF: free undamped, free damped, step, sinusoidal force; consistent nonzero initial
states are internal stepper tests, not exposed initial-condition API. Native zero
response and singular-J rejection; 50-iteration failure using below-roundoff tol.
Rotor dt refinement at 321/641/1281 samples over .04 s, constant and variable speed:
coarse-medium / medium-fine history differences about 3.17. Peak/RMS and selected
samples are recorded alongside ratios. Missing/wrong-sign/doubled gyro and omitted
Ksdt versus zero K1 fail independent equation sentinels. All q/v/a initial values
are exactly zero and gravity initialization behavior is explicitly checked.

## GUI, persistence, exports and frozen gates

Distinct General Time Response F(t) action; Foundation Time/Runup remain intact.
Uniform grid or explicit time samples; scalar or sampled speed; force/moment rows
with constant, sine, inclusive pulse or explicit samples. SI CSV import requires
columns time_s,speed_rad_s,F0,...,F(ndof-1). All histories are materialized into
AnalysisCase parameters and its hash, not retained as external-file dependencies.

Selected node/DOF q/v/a history, displacement orbit, one-sided unwindowed DFFT,
speed, effective force, equation residual and Newton iteration plots. DFFT supports
uniform grids only, explicitly labelled unavailable for nonuniform grids; no silent
resampling. Known-frequency/amplitude/DC/Nyquist tests validate scaling. Orbit uses
native x/y samples; no extra dynamics is calculated in the GUI.

NPZ stores every native array, metadata, selection and hashes. Selected SI CSV
stores t, Omega, alpha, force, q/v/a, both residuals and iterations. Reports and
PNG/SVG/PDF plots reuse existing export infrastructure. Initial residual may be
nonzero; residual plot labels its exclusion of prescribed t0.
Packaged smoke exercises GUI input -> AnalysisCase -> real GUI worker -> service
-> native ABI -> Fortran -> plots/exports -> save -> close -> reopen -> recompute
all arrays/hash exact -> staleness and restoration, using variable speed, weight,
force/moment and 2-D bearing coefficients. Required in clean extracted Linux and
Windows executables, together with unchanged A1/A2/A3 and advanced/fluid-film gates.

A4 remains unqualified remotely until dedicated Linux/Windows, A0 reproduction,
all regression workflows, frozen Linux/Windows and review complete on one exact HEAD.
