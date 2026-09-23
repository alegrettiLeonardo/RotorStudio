# Stage 1 M4 — 22-example stabilization campaign

M4 continues the M3 baseline. It does not start Phase 8 and does not add a desktop UI.

## Scope completed

The 19 MATLAB examples that had not yet been translated were added as deterministic Python entry points. Together with the three previously migrated examples, the repository now contains Python entry points for all 22 supplied book examples.

The campaign exposed two missing Phase-6 stationary frequency-domain paths. They were implemented before any transient work:

- `freq_aux.m` -> `rd_external_response.f90` + `rd_freq_aux_legacy` + Python API;
- `freq_fdn.m` -> `rd_external_response.f90` + `rd_freq_fdn_legacy` + Python API.

No `time_fdn`, `runup`, ODE integrator, Dormand-Prince, or transient solver was implemented in M4.

## Stationary modal hardening

The stationary ABI now has `rd_modal_legacy_vectors`, returning eigenvalues, restored full-DOF eigenvectors and bearing eccentricities. Python `ModalResult` can carry eigenvectors, kappa and eccentricity. Constrained DOFs are restored as exact zeros.

Critical-speed result objects can optionally reconstruct the V2 iterative critical mode shapes by evaluating the Fortran eigensystem at each converged critical and applying the legacy mode-selection rule. Direct-method mode shapes are intentionally not synthesized from the stationary eigensystem because V2 uses a different polynomial eigenproblem in that path.

## Example campaign result

Smoke campaign: 32 runs covering all 22 unique examples and representative menu variants.

- PASS for implemented scope: 30 runs;
- BLOCKED by deliberate Phase-8 boundary: 2 runs;
- FAIL: 0.

At unique-example level:

- 20/22 execute all branches required before Phase 8;
- `Example_06_05_01` executes foundation frequency response, while its `time_fdn` branch is `BLOCKED_PHASE8_TRANSIENT`;
- `Example_06_11_01` executes its stationary modal/Campbell precheck, while `runup` is `BLOCKED_PHASE8_RUNUP`.

Thus all 19 previously outstanding examples are translated and exercised, but G13 remains PARTIAL rather than PASS because two examples contain intentionally deferred transient branches.

## New source-derived tests

M4 adds independent tests for:

- stationary eigenvector ABI and constrained-DOF restoration;
- `freq_aux` forward spinner, backward spinner and vibrator equations;
- `freq_fdn` dynamic stiffness, base-motion RHS and the V2 bearing-selection predicate.

MATLAB/Octave remains unavailable. No source-derived test is used as a substitute for MATLAB numerical equivalence.
