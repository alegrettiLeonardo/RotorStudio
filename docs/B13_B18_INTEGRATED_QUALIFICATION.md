# B13-B18 Integrated Product Qualification

Baseline main before this qualification branch:

`ffab658d6c0820cf92174807fa5d483c0f6fc399`

Preserved qualified engineering heads:

- B12: `4df7801d7c6d16cabd092ad6e2e802a6626873c8`
- B13: `fe0d6c4b906c31a63bb569adfc07b12ddbdfde24`
- B14-B18: `ebf2c2f938a9a5e3a797f9a1904a6c581b4ed111`
- frozen ROSS authority: `6320eab9f890f1b3cc1710d508b446fe063ca68d`

This branch adds **qualification infrastructure only**. It does not reopen the
B12 Reynolds/THD/TEHD equations or change the qualified B13-B18 production
physics.

## Integrated frozen chain

The packaged application now executes one additional clean-process smoke:

`real Cryostar iRdin TABLE -> typed B15 CoefficientBearing -> B16 synchronous
operating map/cache -> B17 matched-whirl -> B18 native full-order synchronous
run-up`.

This is additive to the existing packaged B13 CRUD and B14 native-field smokes.

The frozen smoke verifies:

- the real `EST-12735185-CRYOSTAR_V2.txt` fixture maps both inline coefficient
  tables and preserves the explicit no-sign-transform contract;
- unrelated iRdin numerical-readiness blockers remain granular and are not
  silently removed;
- B16 map generation is synchronous and a repeated lookup resolves from L1;
- map K/C equal the direct imported-table provider at a tabulated point;
- B17 matched-whirl converges using the B16 map;
- B18 reaches final time through `rd_runup_coeffmap_legacy` with exact scope
  `FULL_ORDER|SYNCHRONOUS_COEFFICIENT_POLICY|MAP_BASED|NO_TEHD_IN_ODE`;
- all responses remain finite and the requested run-up speed envelope is
  covered without extrapolation.

## Integrated CI gate

The dedicated workflow builds native Release on Linux and Windows, runs native
CTest, requires Stage 1 to remain exactly 57/57, runs the B13-B18 source suites,
runs the final integrated-chain test, creates clean frozen Linux/Windows
packages, and requires the packaged JSON evidence to contain PASS for B13,
B14, and the B15-B18 integrated chain.

Linux additionally re-runs the B17 frozen ROSS authority comparison.

No PASS is valid until both platform jobs and the aggregate gate succeed on the
same commit SHA.


## Promoted integrated baseline

PR #17 was merged to `main` with merge commit:

`6aee511024047ff8818f8b4268c82cc46204b5fe`

The exact integrated qualification head preserved as an ancestor of `main` is:

`551704a1d089c690e8f9e16dde711c05d494bc6b`

The pull-request qualification matrix was fully green across B13, B14, B15,
B16, B17, B18, ROSS Bearings Native, Stage 1, Stage 2, G14, DyRoBeS and visual
conformance.

`B13_B18_INTEGRATED_PRODUCT_QUALIFICATION = PASS`
