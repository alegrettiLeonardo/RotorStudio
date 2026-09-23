# Stage 1 M3 implementation

M3 continues the M2 baseline without restarting the migration and intentionally does not enter `time_fdn` or `runup`.

## Stationary qualification hardening

### `bearmtx`

The stationary bearing ABI now exposes `Mb`, `Cb`, `Kb`, the constrained-DOF mask and fluid-bearing eccentricity. Tests independently reconstruct the V2 formulas for bearing types 1 through 8. The short-bearing quartic root calculation was corrected in the migrated code to match the polynomial written in `bearmtx.m`:

`[1, -4, 6-(16-pi^2)/H, -(4+pi^2/H), 1]`.

This was a defect in the M2 translation, not a change to the V2 physics.

For bearing type 7 at exactly zero speed, V2 prints that the model is undefined and then proceeds through divisions by zero. M3 returns a clear input status instead. This is tracked as `LEGACY_UNDEFINED_BEHAVIOR_GUARDED`; it is not claimed numerically equivalent at zero speed.

### `freq_rsp`

Source-derived tests reconstruct the V2 dynamic-stiffness solve

`(-M*w^2 + i*C*w + K) x = f`

including force types 1, 2, 3 and 8, Guyan expansion of the prescribed bend shape exactly as used by `freq_rsp.m`, phase conventions, constrained DOF restoration, and zero-speed unbalance behaviour.

### `crit_spd`

All three V2 methods are implemented:

1. direct complex polynomial/eigenvalue method for constant bearings;
2. iteration by fixed eigenvalue number;
3. iteration selecting the critical estimate closest to the **initial** estimate, preserving the actual V2 implementation.

The extended ABI returns iteration counts and convergence flags. One source-derived fluid-bearing case intentionally demonstrates the V2-style maximum-iteration exit for the first critical while the second converges; the final values match an independent Python implementation of the same source equations.

## Coaxial rotor path

New Fortran module `rd_coaxial_solver.f90` implements the responsibilities of `chr_root_coax.m` and `freq_rsp_coax.m`:

- node ranges per rotor;
- signed rotor speed factors;
- row scaling of `C1`/`K1` through the legacy `RelSpd` transformation;
- bearing type 20 translational inter-rotor coupling;
- excitation speed equal to the speed factor of the rotor carrying the selected unbalance;
- reference-speed treatment for speed-dependent bearings, matching V2.

Python adds `RotorDefinition`, coaxial analysis result objects, SolverFacade/backend methods, CLI routes, and a translated `Example_06_06_01`.

## Asymmetric / rotating-frame path

New `rd_assembly_rotating.f90` and `rd_rotating_solver.f90` implement the responsibilities of `rotorasym.m`, `bearasym.m`, `chr_asym.m` and `freq_asym.m`.

Compatibility decisions are explicit:

- `shftasym` types 11..18 are source-formula tested;
- the V2 `Cs = rhoI*Ms/(15*L)` behaviour is reproduced exactly, including the fact that `Ms` has already been scaled;
- the nonzero axial-force branch is blocked because V2 writes into undefined `Kre`;
- `bearasym` type 4 preserves the V2 write to `K1b1(2,1)` and missing `K1b1(4,3)`;
- `chr_asym` preserves the V2 difference between the eigenvalues-only path (includes `K1b`) and the eigenvectors path (omits `K1b`).

Python adds asymmetric result objects, solver routes, CLI routes, disk types 5/6 support, and a translated `Example_07_06_01`.

## Scope boundary

No `time_fdn`, `runup`, Dormand-Prince, foundation response migration, or desktop UI was added in M3. Those remain downstream of stabilization of stationary/coaxial/asymmetric results.
