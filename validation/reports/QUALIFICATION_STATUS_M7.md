# Qualification status — Stage 1 M7

M7 converts the completed local formal-equivalence closure into repository-owned, reproducible evidence and CI. Historical M6 reports are retained unchanged for traceability.

## Qualified baseline

- Qualified implementation head: `224a279a5450f7d6054f639efe2f7ce306aa00e9`
- First main merge containing that exact file tree: `97d482655f363fcc821b10879a3853066d6d6a0b`
- Numerical/behavioural authority: `Rotor_Software_v2`
- Authority runtime used for the frozen local closure: GNU Octave 7.1.0
- Original V2 ZIP SHA256: `bc42d18020013a537da6e7785a3d6b15533cd881939410c5e2a58c8563db5344`
- Frozen local authority baseline SHA256: `a2f8eb6d36dc3db8c9b1b9fd93a18aa9482d8ef16e31c3df95a108aad7432ab3`
- Frozen local transient policy SHA256: `bc2d8ededdb7eb9c4a5206eae2207f90df0d32671ac9f97585612a7c69988af1`

The authority baseline and transient tolerance policy were created before the final Fortran comparison. No threshold was relaxed after observing the Fortran errors.

## Gate status

| Gate | Status | M7 evidence |
|---|---|---|
| G1 source integrity | PASS | V2 ZIP hash frozen; 19 numerical authority sources stored in-repo with canonical LF SHA256 manifest |
| G2 Fortran Release build | PASS | user-executed 5/5 CTest; CI reproduces Release build/test |
| G3 Fortran Debug build | PASS | existing Debug qualification retained; M7 CI reruns Debug with runtime checks |
| G4 Python package tests | PASS | user-executed 49/49 pytest on qualified head; CI reruns full suite |
| G5 element matrices | PASS | max relative error 2.056e-16 |
| G6 global M/C/G/K | PASS | max relative error 3.256e-16 |
| G7 modal equivalence | PASS | eig 1.628e-12; freq 1.147e-12; isolated MAC 1.0; V2 whirl/kappa transform 1.885e-14 |
| G8 harmonic response | PASS | rsp 4.680e-14; aux 1.869e-13; fdn 1.535e-14 |
| G9 critical speeds | PASS | direct 2.595e-12; iterative 5.209e-11 |
| G10 transient overall | PASS | time 8.315e-08; runup 5.266e-07; force 4.441e-16 on the exact frozen comparison DOFs |
| G11 coaxial | PASS | eig 3.880e-14; MAC 1.0; response 3.987e-15 |
| G12 asymmetric rotor | PASS | eig-only 1.522e-13; eig+vectors 3.131e-13; MAC 1.0; response 3.853e-15 |
| G13 22 examples | PASS | 33/33 campaign runs; 22 unique examples |
| G14 book problem regression | NOT_EXECUTED | next engineering-validation milestone |
| G15 Python↔Fortran ABI | PASS | production paths plus formal element qualification ABI exercised |
| G16 Linux execution | PASS | Release/pytest/examples executed on Ubuntu; M7 CI makes this continuous |
| G17 Windows execution | BLOCKED | Windows build/execution qualification not yet implemented |
| G18 clean package validation | PASS | prior clean-package gate retained; M7 CI validates repository checkout directly |
| G19 reproducible formal CI | PENDING_CI | workflow added in M7; pinned Octave 7.1.0 Docker authority, source-integrity check, tolerance freeze, G5–G12 comparator, artifact upload |

## G7 qualification semantics

At zero speed the stationary reference contains repeated/degenerate eigenvalues. Individual eigenvectors inside a degenerate subspace are not unique, so M7 applies individual-vector MAC only to isolated modes. Eigenvalues and frequencies remain end-to-end gates for all modes.

For kappa, the fixed `1e-10` criterion qualifies the legacy V2 `whirl` transformation on the same authoritative eigenvectors. End-to-end kappa is retained as a diagnostic because near-perfect circular orbits and points adjacent to the V2 `|u||v| < 1e-16` guard amplify tiny cross-LAPACK eigenvector perturbations while eigenvalues and MAC remain equivalent.

## M7 CI contract

`.github/workflows/stage1-m7-qualification.yml` runs three independent jobs:

1. Linux Release + Python + 22-example campaign.
2. Linux Debug with Fortran runtime checks.
3. Formal G5–G12 reproduction using the pinned `gnuoctave/octave:7.1.0` container.

The formal job verifies the V2 source manifest, generates the independent transient references, generates a fresh authority baseline with Octave 7.1.0, freezes transient tolerances before the Fortran comparison, runs the formal comparator, and uploads the complete evidence bundle.

The local frozen evidence is recorded in `FORMAL_EQUIVALENCE_M7.json`. CI-generated baseline hashes may differ between runs because the MAT file contains metadata such as generation time and path; the source manifest, engine version, threshold policy algorithm, and numerical gates are the reproducibility anchors.
