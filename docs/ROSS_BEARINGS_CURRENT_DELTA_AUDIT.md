# ROSS Bearings — Current-Main Delta Audit

Purpose: rebaseline the standalone Fortran bearing work before RotorStudio integration.

## Authorities

- historical/native frozen ROSS pin: `631a249adbae414d5f5f986479b58f1a4c47935e`
- current ROSS main audited here: `6320eab9f890f1b3cc1710d508b446fe063ca68d`
- current main is 229 commits ahead of the historical pin at the time of audit.
- AMB / MagneticBearingElement is explicitly excluded.

## Material changes relevant to native implementation

### 1. BearingElement coefficient axes are now first-class

Current ROSS introduces a `BearingCoefficient` abstraction with four coefficient kinds:

- constant;
- rotor-speed 1-D;
- excitation-frequency 1-D;
- rotor-speed × excitation-frequency 2-D grid.

For one supplied argument the public API evaluates synchronously. For the 2-D case, the native design must therefore preserve separate rotor-speed and excitation-frequency coordinates.

Interpolation modes:

- `pchip` (default): shape-preserving PCHIP in-range;
- `linear`;
- endpoint extrapolation is linear using the endpoint derivative/slope;
- axes must be strictly increasing.

This is a **behavioral/API change that matters to RotorStudio FRF integration** and is the first new native gate (BF1).

### 2. FluidFilmBearing now supports speed × whirl-frequency campaigns

Current `FluidFilmBearing` accepts a rotor-speed axis and an optional excitation-frequency axis. When both are provided, ROSS solves each speed/frequency pair with whirl ratio `frequency/speed` and stores a 2-D coefficient grid.

Therefore RotorStudio must not collapse:
`rotor_speed == excitation_frequency`
except for explicitly synchronous analyses.

### 3. SqueezeFilmDamper

The current SFD physical equations are materially unchanged from the historical source audit. Current-main changes include solved-table persistence. The native implementation should continue to reproduce the three geometry branches:

- groove;
- end_seals;
- groove-end_seals;

with cavitation on/off and the literal ROSS branch behavior.

### 4. CylindricalBearing

Current ROSS exposes the simplified closed-form short-bearing model as `CylindricalBearing`. Important current behavior:

- every speed must be strictly positive;
- one real equilibrium root `e^2` must lie in (0,1);
- the bearing stores eccentricity, attitude, Sommerfeld and modified Sommerfeld;
- K/C are speed-dependent 2×2 translational matrices.

This receives an explicit native parity gate (BF3), separate from the full TEHD journal engine.

### 5. Journal / fixed geometry / tilting pad

The current public layer consistently uses `speed` as the rotor-speed axis and routes solved fluid-film outputs into the same coefficient-table abstraction. The existing native G3–G6 journal kernels remain valuable and are not reopened unless a current-main source change is shown to alter the governing physics.

Fixed-geometry classes are treated as configuration translators into the shared fluid-film engine; they must not duplicate Reynolds/thermal physics in Fortran.

### 6. ThrustPad

Current-main changes reviewed so far are mainly public-axis/persistence plumbing. The standalone thrust solver remains independent of the journal fluid-film engine and still requires its own native polar Reynolds/energy/equilibrium/dynamic gates.

## Native rebaseline decision

Existing qualified kernels remain frozen unless a physical source delta is demonstrated:

- Ball / Roller: requalification only;
- G3–G6 PlainJournal/TEHD kernels: frozen;
- G7.1–G7.2 TiltingPad kernels: frozen;
- new current-main work proceeds additively.

New mandatory work before RotorStudio integration:

1. BF1 current coefficient-table contract;
2. BF3 CylindricalBearing;
3. TiltingPad G7.3 onward;
4. SFD;
5. ThrustPad;
6. fixed-geometry configuration wrappers;
7. stable native C ABI.

## RotorStudio integration consequence

The existing RotorStudio 34-double legacy bearing packet cannot represent the current ROSS axis semantics or high-dimensional fluid-film configurations. New ROSS-derived bearing models therefore require a separate typed bearing domain + stable bearing C ABI. The legacy RotorStudio types 1–8/20 remain frozen and coexist with the new provider.
