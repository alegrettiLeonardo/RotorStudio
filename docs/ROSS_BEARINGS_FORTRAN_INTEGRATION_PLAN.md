# ROSS Bearings in Fortran → RotorStudio Integration Plan

Status: **ROTORSTUDIO COEFFICIENT-PROVIDER INTEGRATION IN PROGRESS; FULL NATIVE THD/TEHD NOT YET CLOSED**

RotorStudio base at plan freeze:

- repository: `alegrettiLeonardo/RotorStudio`
- base: `main@5297c4ac763c60a091d4265eafcee2c46506eaf6`

ROSS source authorities:

- current upstream audit ref: `petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d`
- existing standalone bearing-fortran frozen ref: `petrobras/ross@631a249adbae414d5f5f986479b58f1a4c47935e`

AMB / magnetic bearings are explicitly **out of scope**.

## 0. Execution status at native implementation start

Native implementation branch: `feature/ross-bearings-fortran-integration`.

Current integration branch: `feature/ross-bearings-rotorstudio-20260925`.
See `docs/ROSS_BEARINGS_ROTORSTUDIO_INTEGRATION.md` for the implemented
runtime boundary and explicit remaining blocks.

The first additive standalone target is `libdrmbearings`. It is built beside
`libdrmrotor` but is **not linked into RotorStudio runtime yet**.

Initial implementation gates now present in the branch:

- **BF1** — generic ROSS coefficient interpolation core: constant/1-D/2-D
  semantics, linear mode, PCHIP mode, and linear endpoint extrapolation;
- **BF2** — BallBearingElement and RollerBearingElement formulas reimplemented
  from current ROSS and pinned to current upstream oracle values;
- **BF3** — current ROSS CylindricalBearing closed-form short-bearing model;
- **BF4** — fixed-geometry translators compiled and source-qualified for
  PartialArc / Elliptical / OffsetHalves / MultiLobe / PressureDam / PlainJournal;
- **BF5a** — source-faithful Reynolds Q4 element kernel;
- **BF5band** — banded Reynolds assembly/LU/cavitating solve kernels;
- **BF5film** — rigid/isoviscous baseline film-thickness kernel;
- **BF5cfg** — TiltingPad configuration and initial-position gate;
- **BF7** — SqueezeFilmDamper, including groove, end-seals and combined
  geometry branches with cavitation on/off.

The remaining advanced journal/tilting/thrust work stays standalone until its
native gates are closed. No `drm_core`, SolverFacade, RotorStudio UI, or existing
legacy bearing packet consumes `libdrmbearings` at this stage.

### Coordinate / DOF boundary

ROSS uses x/y as radial directions and z as axial. RotorStudio's qualified
lateral model owns two radial translations plus two rotations per station and
does not currently expose a qualified axial translation DOF in the lateral
assembly. Therefore:

- ROSS x/y radial K/C/M map candidates are in scope for later lateral integration;
- ROSS z/axial coefficients are preserved by the bearing provider but are **not**
  silently injected into a RotorStudio lateral DOF;
- `ThrustPad` is initially a Bearing Performance calculation only;
- any axial rotor-dynamics coupling requires a separate axial-DOF qualification.

### Seal boundary

This plan is for **bearings**. ROSS `SealElement`, `LabyrinthSeal`,
`HolePatternSeal` and `HybridSeal` are adjacent but not automatically pulled
into this scope. RotorStudio's existing qualified seal path remains unchanged.
A separate seal migration gate can be opened later without coupling it to AMB.


## 1. Governing rules

1. Complete and qualify the standalone Fortran bearing library **before** connecting it to RotorStudio.
2. Do not change RotorStudio's qualified legacy bearing path (types 1–8 / 20) merely to fit new ROSS models.
3. Do not place ROSS Python at RotorStudio runtime. ROSS is an oracle/source authority during development and qualification only.
4. Every family receives source audit → native implementation → analytical/oracle qualification → public C ABI → Python facade → only then RotorStudio integration.
5. Preserve SI units internally and keep rotor speed and excitation/whirl frequency as separate variables.
6. Expensive TEHD solvers are never invoked implicitly from GUI painting or result plotting.
7. No bearing family is marked supported merely because its editor exists.

## 2. ROSS non-AMB bearing inventory

### A. Generic dynamic-coefficient bearing

- `BearingElement`
- constant coefficients
- speed-axis coefficient tables
- excitation-frequency-axis tables
- speed × frequency coefficient grids
- direct and cross-coupled K/C/M
- ground or linked-node semantics

Current ROSS main uses `BearingCoefficient` with PCHIP or linear interpolation and linear endpoint extrapolation.

### B. Rolling-element bearings

- `BallBearingElement`
- `RollerBearingElement`

Standalone Fortran status: already implemented and qualified. These gates remain frozen unless the current ROSS audit identifies a physical change.

### C. Simplified hydrodynamic cylindrical bearing

- `CylindricalBearing`

Closed-form short-bearing model. This is separate from the full TEHD journal engine and needs an explicit ROSS-current parity gate.

### D. Fixed-geometry / journal-fluid-film family

- `FluidFilmBearing`
- `FixedGeometryBearing`
- `PlainJournal`
- `PartialArcBearing`
- `EllipticalBearing`
- `OffsetHalvesBearing`
- `MultiLobeBearing`
- `PressureDamBearing`

The standalone library already owns a qualified journal-film engine through G3–G6. The remaining work here is mainly current-ROSS delta audit plus friendly geometry/configuration wrappers feeding that frozen engine without duplicating physics.

### E. Tilting-pad journal bearing

- `TiltingPad`

Existing standalone state:
- G7.0 source audit: PASS
- G7.1 geometry: PASS
- G7.2 prescribed film / pressure / force / pivot moment: PASS
- G7.3+ pending

Required completion:
- G7.3 pad tilt equilibrium at fixed journal center
- G7.4 journal + pad static equilibrium
- G7.5 unreduced dynamic perturbation fields
- G7.6 exact pad-DOF condensation
- G7.7 reduced synchronous K/C + baseline facade
- G7.8 turbulent model
- G7.9 THD
- G7.10 deformation / compliant pivot options

### F. Thrust bearing

- `ThrustPad`

Independent polar Reynolds/energy solver. Implement separately from the radial journal engine. RotorStudio integration may initially expose it as a bearing-performance calculation result and only couple axial dynamics after the rotor axial DOF contract is explicitly qualified.

### G. Squeeze-film damper

- `SqueezeFilmDamper`

Algebraic short-bearing model with ROSS geometry variants:
- groove
- end seals
- groove + end seals

Implement source behavior first, including documented source quirks where parity requires them; corrected alternatives must be separate opt-in models, never silent changes.

## 3. Rebaseline gate — RB0

Before further Fortran development:

1. Diff ROSS current main `6320eab...` against frozen `631a249...`.
2. Produce `ROSS_BEARINGS_CURRENT_DELTA_AUDIT.md`.
3. Classify each change:
   - numerical/physical;
   - API/axis semantics;
   - persistence;
   - plotting/reporting only.
4. Preserve G1–G7.2 frozen kernels unless an upstream physical change directly affects them.
5. For new work use current ROSS main as the behavioral authority.
6. Add a provenance record to every native result:
   - ROSS commit;
   - native library commit/build;
   - model family;
   - assumptions/capabilities;
   - interpolation mode.

## 4. Standalone Fortran implementation order

### BF1 — current ROSS coefficient-table contract

Implement a native generic coefficient provider before higher-level integration:

- constant K/C/M;
- speed-only 1-D tables;
- excitation-frequency-only 1-D tables;
- speed × frequency 2-D grids;
- strict increasing axes;
- `linear` interpolation;
- shape-preserving PCHIP interpolation;
- linear extrapolation using endpoint slopes;
- synchronous shorthand `frequency = speed`.

This gate is required because modern ROSS separates rotor speed from excitation frequency.

### BF2 — rolling bearings requalification

Do not rewrite formulas. Re-run current-ROSS oracle cases for:
- ball;
- roller.

If current ROSS physics is unchanged, record `FROZEN_COMPATIBLE`.

### BF3 — ROSS CylindricalBearing

Implement/qualify the simplified analytical short-bearing model independently of the full TEHD engine.

Required outputs:
- eccentricity;
- attitude angle;
- Sommerfeld quantities;
- Kxx/Kxy/Kyx/Kyy;
- Cxx/Cxy/Cyx/Cyy.

### BF4 — fixed-geometry wrapper layer

**Current status: IMPLEMENTED / native geometry gate PASS on Linux; cross-platform CI tracked by the branch workflow.**

Add source-faithful constructors which only generate input arrays for the already-qualified journal engine:

- PartialArc;
- Elliptical;
- OffsetHalves;
- MultiLobe;
- PressureDam;
- PlainJournal.

No Reynolds/thermal equation is duplicated in wrappers.

### BF5 — TiltingPad rigid/isoviscous completion

**Current partial status:** configuration, baseline film thickness, Reynolds Q4
element and banded linear-solver kernels are implemented. The operating-point
solver is not yet closed.

Close G7.3 → G7.7 before turbulence/THD.

G7.3 source semantics must include:
- sequential per-pad search;
- cold geometry-derived bracket on each call;
- width tolerance `< 1e-8 rad`;
- lower-endpoint final evaluation;
- no moment-magnitude convergence criterion;
- `M >= 0` raises lower bound;
- negative-film retry before pressure solve;
- bounded native stagnation protection reported as a diagnostic, not disguised as ROSS behavior.

G7.4 closes journal-position Newton/load equilibrium.

G7.5–G7.7 close perturbation fields, condensation, and reduced K/C.

### BF6 — TiltingPad advanced physics

After rigid/isoviscous parity:
- turbulence;
- adiabatic/full THD;
- hot-oil mixing;
- pad thermal/mechanical deformation;
- pivot compliance.

Each option is a separate capability flag and qualification matrix entry.

### BF7 — SqueezeFilmDamper

Implement standalone algebraic equations and ROSS parity fixtures. Keep geometry branches explicit.

### BF8 — ThrustPad

Implement in gates:
1. polar geometry/mesh;
2. isoviscous Reynolds;
3. load/equilibrium search;
4. thermal energy equation;
5. Kzz/Czz;
6. result fields and diagnostics;
7. current-ROSS oracle qualification.

No radial 4-DOF RotorStudio coupling is claimed from this gate.

### BF9 — unified native bearing API

Create a stable Fortran API independent of RotorStudio.

Suggested conceptual API:

```text
bearing_create(model_kind, configuration) -> handle
bearing_capabilities(handle) -> flags
bearing_solve_operating_point(handle, speed) -> result
bearing_evaluate(handle, speed, excitation_frequency) -> M,C,K
bearing_get_fields(handle, result_id) -> optional pressure/temperature/film
bearing_destroy(handle)
```

A C binding exposes POD descriptors / opaque handles. Do not use the legacy RotorStudio 34-double bearing row for these models.

## 4.1 Source/license provenance rule

ROSS is Apache-2.0 licensed. Any directly ported algorithm or source-derived
implementation must retain a provenance note identifying
`petrobras/ross@6320eab9f890f1b3cc1710d508b446fe063ca68d` and preserve the
required license/notice obligations. ROSS remains a development oracle, not a
RotorStudio runtime dependency.

## 5. Qualification requirements before RotorStudio integration

Every model family must have:

- exact source/version provenance;
- deterministic clean build;
- debug/FPE-check build;
- unit tests;
- independent analytical reductions where available;
- ROSS oracle fixture(s);
- finite/nonfinite and invalid-input tests;
- dimensional/unit checks;
- matrix symmetry/asymmetry checks appropriate to the model;
- interpolation/extrapolation tests;
- repeatability tests;
- no hidden Python/ROSS runtime dependency.

Acceptance labels:

- `SOURCE_AUDITED`
- `NATIVE_IMPLEMENTED`
- `ROSS_PARITY_PASS`
- `C_ABI_PASS`
- `READY_FOR_ROTORSTUDIO`

No RotorStudio work begins for a family before `READY_FOR_ROTORSTUDIO`.

## 6. RotorStudio integration architecture

Do **not** extend the legacy fixed-size `Bearing.properties` packet to carry the new physics.

Target architecture:

```text
RotorStudio UI
      ↓
drm_core typed bearing domain
      ↓
BearingService / BearingFacade
      ↓
libdrmbearings C ABI
      ↓
standalone ROSS-derived Fortran bearing engine
      ↓
BearingOperatingPoint / BearingCoefficientProvider
      ↓
Rotor assembly / analyses
```

Keep the current path alive:

```text
legacy Bearing type 1–8 / 20
      ↓
existing rd_*_legacy ABI
      ↓
qualified Stage 1 Fortran
```

The two paths coexist during migration.

## 7. RotorStudio typed domain

Add explicit domain objects rather than overloaded numeric tuples, e.g.:

- `CoefficientBearing`
- `BallBearing`
- `RollerBearing`
- `CylindricalBearing`
- `PlainJournalBearing`
- `PartialArcBearing`
- `EllipticalBearing`
- `OffsetHalvesBearing`
- `MultiLobeBearing`
- `PressureDamBearing`
- `TiltingPadBearing`
- `SqueezeFilmDamper`
- `ThrustPadBearing`

Each object persists:
- model family;
- physical inputs;
- speed/frequency axes;
- solver capability flags;
- native-model provenance;
- optional cached solved coefficient table identified by an input hash.

## 8. Rotor-analysis coupling

### Modal / Campbell

At each rotor speed, request the bearing matrices at the declared excitation policy.

Default synchronous evaluation:
`omega_excitation = omega_rotor`

Any non-synchronous policy must be explicit.

### Synchronous response

Use `speed = frequency` by definition of the synchronous response.

### General FRF

Must support **different**:
- rotor speed;
- excitation frequency.

This is why BF1 2-D coefficient semantics are mandatory before integration.

### Critical speeds

Use the same bearing-evaluation contract as the iterative critical-speed solver; no precomputed hidden constant substitution.

### Run-up / transient

First qualified scope should use precomputed/interpolated coefficient tables. Do not run a full TEHD operating-point solve inside every ODE time step.

Document the update cadence and interpolation domain.

### Coaxial / asymmetric

Enable only after each analysis-specific assembly convention has an explicit qualification test with the new provider.

### ThrustPad

Initially expose calculation/results in Bearing Performance. Couple it to rotor dynamics only when RotorStudio has a separately qualified axial DOF path.

## 9. User interface integration

Extend the existing Bearing Performance workspace by model family.

For each implemented family:
- type-sensitive input form;
- operating conditions;
- lubricant;
- speed / excitation-frequency grids;
- compute button calling BearingService asynchronously;
- result table K/C/M;
- eccentricity/attitude where relevant;
- pressure / film / temperature plots only when the native model actually produces them;
- explicit provenance and assumptions panel.

Unsupported models remain disabled; AMB is absent.

## 10. Legacy iRdin / Cryostar bridge

The current iRdin importer preserves `TABLE§rpm|Kxx|Kxy|Kyx|Kyy|Cxx|Cxy|Cyx|Cyy` but blocks numerical execution because Stage 1 has no qualified speed-dependent bearing-table contract.

After BF1 + RotorStudio coefficient-provider integration:

1. map iRdin tables into `CoefficientBearing(speed_axis=...)`;
2. qualify interpolation semantics explicitly;
3. compare table-point matrices exactly;
4. qualify between-point behavior;
5. only then remove the bearing-table portion of the Cryostar numerical-readiness block.

This is a direct engineering benefit of the new architecture.

## 11. RotorStudio integration gates

- **RB1** Stage 1 / Stage 2 baseline integrity
- **RB2** standalone `libdrmbearings` Linux build
- **RB3** standalone `libdrmbearings` Windows build
- **RB4** all selected ROSS bearing families parity-qualified
- **RB5** stable C ABI
- **RB6** Python BearingFacade, no GUI dependency
- **RB7** persistence / save / reopen
- **RB8** constant-coefficient collapse vs existing type 3/5/6 path
- **RB9** speed-dependent 1-D coefficient integration
- **RB10** speed × excitation-frequency FRF integration
- **RB11** Modal / Campbell / Critical Speeds
- **RB12** Synchronous Response
- **RB13** run-up/transient table policy
- **RB14** Bearing Performance UI
- **RB15** real Cryostar iRdin bearing-table qualification
- **RB16** Linux frozen package
- **RB17** Windows frozen package
- **RB18** clean installation
- **RB19** full legacy regression
- **RB20** documentation / provenance / screenshots

Statuses:
`PASS | FAIL | BLOCKED | NOT_EXECUTED | NOT_APPLICABLE`

## 12. Stop conditions

Do not integrate a model into rotor analyses if:
- ROSS parity is not demonstrated;
- unit/axis semantics are ambiguous;
- the native C ABI is still changing;
- numerical result depends on ROSS Python at runtime;
- the model cannot state whether coefficients depend on speed, excitation frequency, or both;
- Stage 1 regression fails.

Do not merge into `main` until the selected integration scope is fully gated and the existing RotorStudio physics remains green.
