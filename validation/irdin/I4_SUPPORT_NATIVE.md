# I4 — native bearing-support element kernel

This stage implements and qualifies only the historical radial bearing/support
coupling element. It does not yet augment a complete rotor with support DOFs,
so `IRDIN_FLEXIBLE_SUPPORT_UNMAPPED` remains active.

Authority: `alegrettiLeonardo/frontend_rotordin@647d600bc1d32a05de62ee457942e00285b572e3`,
`matrizes.f90` plus `parmanv.f90::prpkc/prpsp`.

Local order is `[rotor_x, rotor_y, support_x, support_y]`:

```
M = diag(0,0,ms,ms)
K = [[Kb,-Kb],[-Kb,Kb+Ks]]
C = [[Cb,-Cb],[-Cb,Cb+Cs]]
```

I3 already qualified the name-only legacy X/Z -> RotorStudio X/Y mapping.
No coefficient or cross-coupling sign is changed.

Versioned diagnostic ABI: `rd_irdin_support_matrices_v1`.

Non-claims: no full global support assembly, no mass-span solver
materialization, no Campbell/critical/unbalance qualification and no API 541
lateral-dynamics qualification yet.
