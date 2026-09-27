# B13-B18 Advanced Bearing Qualification Status

Current promoted baseline:

- `main@6aee511024047ff8818f8b4268c82cc46204b5fe`
- integrated qualification head preserved in history:
  `551704a1d089c690e8f9e16dde711c05d494bc6b`

## Gate summary

| Gate | Status | Authority / evidence |
|---|---|---|
| B12 physical advanced-bearing foundation | PASS | `4df7801d7c6d16cabd092ad6e2e802a6626873c8` |
| B13 engineering CRUD | PASS | `fe0d6c4b906c31a63bb569adfc07b12ddbdfde24` |
| B14 async fields | PASS | Linux/Windows source + frozen |
| B15 iRdin coefficient import | PASS | real Cryostar source + fail-closed parser |
| B16 operating map/cache | PASS | direct/map parity + L1/L2/cancel/corruption |
| B17 matched whirl | PASS | frozen ROSS `6320eab9...` + MAC tracking |
| B18 synchronous run-up | PASS | native `rd_runup_coeffmap_legacy` |
| B13-B18 integrated product chain | PASS | `551704a1d089c690e8f9e16dde711c05d494bc6b` |

## Preserved fail-closed boundaries

ThrustPad/axial DOF, coaxial advanced bearings, rotating/asymmetric advanced
bearings, nonzero advanced-bearing mass assembly, general advanced-bearing
transient response, direct Reynolds/THD/TEHD inside the run-up ODE,
reduced-order advanced-bearing run-up and asynchronous 2-D maps inside B18 remain
outside the qualified scope.

## Continuous qualification

The integrated workflow is configured for future pushes to `main`, its QA
branches and pull requests. Future changes to this stack must satisfy the
Linux/Windows source matrix, B12 regression, Stage 1 57/57 contract, frozen
application smoke and integrated aggregate gate.
