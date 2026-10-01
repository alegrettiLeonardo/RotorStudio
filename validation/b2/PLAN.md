# B2 — 6-DOF global assembly + modal + Campbell

B2_BASE_MAIN: d44ad24590f984e3f0655c427fcbf39be94a6da6
B2_INITIAL_HEAD: d44ad24590f984e3f0655c427fcbf39be94a6da6
B1_MERGE_SHA: d44ad24590f984e3f0655c427fcbf39be94a6da6
B1_QUALIFIED_PARENT: 35e8f26937aaa60d1ce3ccbb3a523f3c1e6a6d2f
ROSS_AUTHORITY: petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d

Entry gate: PASS. B1 was merged into main and the four mandatory post-merge
main-push regressions (Stage 1 M7, Stage 1 Final, G14, B13-B18 integrated)
completed successfully before this branch was created.

This stage freezes B2 ROSS authority before any native global solver is added.
Production scope is intentionally absent until authority candidate review/freeze.


## Current exact-head campaign

- Draft PR: #35
- Frozen authority: PASS / immutable
- B2 native implementation present: global M/K/C/G/Ksdt, dense modal, standard Campbell
- Independent gates added: matrix superposition/energy, state-space identities,
  modal scalar/conjugate/repeatability/gyro-split, Campbell station consistency,
  tracking permutation/crossing sentinel, 6DOF-vs-4DOF lateral common-domain cross-check.
- The 4DOF cross-check compares only the positive-imaginary physical eigenvalue
  family, avoiding double-counting the negative-frequency conjugate half.
- Promotion remains NOT AUTHORIZED until one exact HEAD passes Linux, Windows,
  frozen authority, inherited A0-A8, bearings, Qt and Flet qualification.
