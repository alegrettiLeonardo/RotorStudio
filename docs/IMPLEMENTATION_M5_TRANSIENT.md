# Stage 1 M5 — Phase 8 transient: `time_fdn` + `runup`

M5 starts Phase 8 **from the exact M4 baseline**. It does not revise the already closed M4 stationary, coaxial, or rotating/asymmetric physics. The only production additions are the transient reduction/integration path and the Python/ABI surfaces required to call it.

## Authority and frozen source

The authority remains `Rotor_Software_v2`. The V2 transient sources and corresponding examples are SHA256-frozen under `validation/baseline/transient/SOURCE_HASHES.sha256`.

MATLAB/Octave is not available in the qualification environment. Therefore a true MATLAB `ode45` runtime baseline is **BLOCKED**. M5 adds a clearly separated `SOURCE_DERIVED_REFERENCE`, generated with an independent SciPy generalized eigensystem and high-accuracy DOP853 integration, solely to qualify the new Fortran implementation while the MATLAB gate remains blocked.

## V2 modal reduction preserved

The manual describes Guyan/static reduction, but the V2 implementation actually performs:

```matlab
[eigvec,eigval] = eig(K,M);
[eigval,isort] = sort(diag(eigval));
eigvec = eigvec(:,isort);
Tr = eigvec(:,1:nr);
```

M5 preserves the V2 behaviour. `rd_reduction.f90` uses LAPACK `DGGEV` on `(K,M)`, sorts the real generalized eigenvalues in ascending order for the qualified transient cases, and selects the first `nr` right generalized eigenvectors. It does **not** substitute Guyan reduction.

When `nr <= 0` or `nr >= ncdof`, the full physical coordinate basis is used, matching the V2 no-reduction branch.

For reduced cases whose V2 generalized eigensystem is genuinely complex, M5 returns `RD_ERR_UNSUPPORTED` rather than silently discard the imaginary part. The supplied `time_fdn`/`runup` examples have a real modal basis and are qualified.

## Dormand–Prince integrator

`rd_dp45.f90` implements the standard embedded Dormand–Prince 5(4) pair, i.e. the standard adaptive 4/5 family requested:

- 5th-order accepted solution;
- embedded 4th-order error estimate;
- explicit relative and absolute tolerances;
- deterministic scalar step controller;
- accepted/rejected step counters;
- no `-ffast-math` or altered physics.

Python defaults are explicit: `rtol=1e-3`, `atol=1e-6`. They mirror the conventional `ode45` default tolerance scale, but M5 does **not** claim the internal MATLAB step sequence or interpolation is identical. For `time_fdn`, the adaptive solver is clipped to each requested output time. For `runup`, the returned time vector contains accepted adaptive step endpoints, analogous to the two-point-`tspan` V2 call.

## Compatibility details

`time_fdn` preserves the single-speed matrices, V2 bearing predicate `type > 2 | type < 9`, real foundation amplitudes, half-sine pulse and derivatives, modal truncation, transformed forcing matrices, zero initial conditions and constrained-DOF restoration.

`runup` preserves the constant-bearing restriction, M/K/C/C1 construction, V2 modal truncation, unbalance force/moment phases, `phi(t)=a2*t^2+a1*t+a0`, `Omega(t)=2*a2*t+a1`, and `real(B*(Omega^2-j*alpha_rotor)*exp(j*phi))`. The source mixes `jot` and MATLAB `j`; M5 implements the clean-workspace complex-unit meaning and records this as `LEGACY_SYMBOL_DEPENDENCE_CANONICALIZED`.

## New production modules

```text
fortran/src/rd_reduction.f90
fortran/src/rd_dp45.f90
fortran/src/rd_transient.f90
```

`rd_lapack.f90` centralizes `DGGEV`; `rd_c_api.f90` exports `rd_time_fdn_legacy` and `rd_runup_legacy`. Python adds `TransientResult`, `run_foundation_time_response`, `run_runup`, bindings and CLI routes.

## Example closure

`Example_06_05_01` case (b) executes the full model and V2 10-mode truncation. `Example_06_11_01` executes both acceleration cases with `nr=4`. The M5 smoke campaign therefore has no Phase-8 blocks.
