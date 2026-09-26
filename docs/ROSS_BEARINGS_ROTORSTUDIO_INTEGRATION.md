# ROSS-derived Bearings — RotorStudio Integration

Branch: `feature/ross-bearings-rotorstudio-20260925`

RotorStudio base: `main@5297c4ac763c60a091d4265eafcee2c46506eaf6`

ROSS behavioral authority:
`petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d`

AMB / magnetic bearings remain out of scope.

## Promotion status

PlainJournal and TiltingPad native fluid-film physics are **ROSS_PARITY_PASS_B12**
and are promoted to the qualified stationary RotorStudio bearing-provider
boundary.

The qualified native chain is:

```text
geometry / lubricant / operating point
        ↓
generalized Reynolds (Gamma, G)
        ↓
journal / pad equilibrium
        ↓
THD thermal fixed point + hot-oil carryover
        ↓
pad deformation / TEHD when requested
        ↓
unreduced K/C perturbation blocks
        ↓
TiltingPad pad-DOF condensation at (Omega, omega)
        ↓
2x2 translational K/C provider
```

The runtime has no ROSS Python dependency. ROSS is used only as the frozen
development and qualification authority.

## Native Fortran bearing physics

`libdrmbearings` exposes qualified C ABI providers for:

- `BallBearing`;
- `RollerBearing`;
- `CylindricalBearing`;
- `SqueezeFilmDamper`;
- ROSS-style constant / 1-D / 2-D coefficient interpolation;
- `PlainJournalPhysicsBearing`: Reynolds, load equilibrium, THD/TEHD,
  perturbation K/C and field export;
- `TiltingPadPhysicsBearing`: pad tilt equilibrium, journal equilibrium,
  THD/TEHD, unreduced dynamic blocks, independent-whirl pad-DOF condensation
  and field export.

The packed ABI is used for PlainJournal and TiltingPad on Linux and Windows.
The field-export ABI is used only for explicit Bearing Performance calculations.

## Frozen ROSS B12 authority

The checked-in golden-reference generator is pinned to the exact ROSS commit
above and produces four qualification cases:

1. PlainJournal isoviscous;
2. PlainJournal TEHD;
3. TiltingPad synchronous THD;
4. TiltingPad asynchronous sweep with fixed rotor spin and independent whirl
   frequency.

B12 compares equilibrium coordinates, pressure and temperature summaries,
full pressure / temperature fields, deformation where applicable, complete
2x2 K/C matrices and TiltingPad pad angles. The asynchronous case also guards
against an implementation that collapses `omega` to `Omega`.

The exact-head native workflow qualifies Release and Debug/FPE builds and the
packed Python↔Fortran ABI on Linux and Windows.

## Axis contract

Every advanced provider is evaluated as

```text
M_b, C_b, K_b = B(Omega_rotor, omega_excitation)
```

For synchronous modal/response calculations,
`omega_excitation = Omega_rotor`.

Auxiliary/foundation FRF paths preserve independent spin and excitation
frequency and re-evaluate the provider at each requested point.

## Rotor assembly promotion

For the currently qualified lateral 4-DOF stationary RotorStudio assembly, a
native or table-based advanced radial bearing is evaluated first and its 2x2
translational K/C is mapped to the existing qualified type-5 assembly row:

```text
typed advanced bearing
        ↓
libdrmbearings
        ↓
Kxx Kxy Kyx Kyy / Cxx Cxy Cyx Cyy
        ↓
temporary type-5 adapter row at (Omega, omega)
        ↓
existing libdrmrotor stationary assembly / modal / response
```

This is an adapter only. Persisted legacy bearings are not rewritten and the
historical type 1–8 / 20 Fortran implementation is unchanged.

A nonzero advanced-bearing mass matrix remains fail-closed because the
qualified type-5 bridge has no bearing-mass contract.

Native PlainJournal and TiltingPad physical providers no longer require a
manual provenance override to enter this stationary bridge: B12 qualification
is carried by the provider itself as
`qualification=ROSS_PARITY_PASS_B12` with the frozen ROSS SHA.

## Qualified stationary analyses

The promoted provider boundary is used by:

- stationary matrix assembly;
- stationary modal / eigensystem;
- synchronous frequency response;
- auxiliary FRF with independent `Omega` and `omega`;
- foundation FRF with independent `Omega` and `omega`;
- iterative critical-speed calculations;
- direct bearing evaluation through `SolverFacade.advanced_bearing()`.

The existing validation gate still rejects advanced bearings in rotating-frame
and coaxial assembly.

## Bearing Performance

The desktop Bearing Performance workspace recognizes
`RotorModel.advanced_bearings`.

For advanced bearings it provides explicit operating-point controls for rotor
speed `Omega` and whirl/excitation frequency `omega`. The user must press
**Evaluate Native Bearing** before a physical solve is launched. Selection,
painting and normal UI refresh do not invoke the expensive Reynolds/THD/TEHD
engine.

For qualified PlainJournal and TiltingPad models the workspace displays:

- K and C;
- equilibrium coordinates / eccentricity;
- pressure maximum;
- thermal summaries;
- pad deformation summary when present;
- TiltingPad angles;
- B12 qualification and ROSS authority;
- native pressure field summary;
- native film-temperature field summary;
- native deformation field summary.

## Domain and persistence

`RotorModel.advanced_bearings` remains separate from
`RotorModel.bearings`. Project schema 2 persists typed advanced models,
physical inputs, coefficient axes/tables, interpolation mode and provenance.
Schema-1 projects remain loadable.

## Compatibility boundary

The following remain explicitly out of scope until separate qualification:

- native ThrustPad;
- axial ThrustPad coupling into the lateral rotor;
- advanced-bearing run-up / transient policy;
- coaxial advanced-bearing assembly;
- rotating-frame / asymmetric advanced-bearing assembly;
- nonzero advanced-bearing mass terms;
- AMB / magnetic bearings.

There is no silent fallback to constant coefficients for these cases.

## Promotion gates

The integration promotion requires all of the following on the same HEAD:

- B10/B11 packed ABI PASS in Release and Debug/FPE;
- B12 frozen ROSS parity PASS;
- Linux and Windows native-bearing gates PASS;
- frozen Stage-1 regression remains exactly 57/57;
- native PlainJournal and TiltingPad type-5 bridge matrix-equivalence tests PASS;
- Bearing Performance real-native UI test PASS;
- clean frozen Linux and Windows application smoke proves the B12-qualified
  physical bearing can reach normal rotor assembly;
- legacy Fortran core boundary remains unchanged.

When these exact-head gates are green, PR #14 is eligible for Ready for Review.
