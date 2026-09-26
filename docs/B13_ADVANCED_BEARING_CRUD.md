# B13 — Advanced Bearing Engineering CRUD

## Baseline and freeze

B13 is stacked directly on the promoted B12 physical baseline:

`4df7801d7c6d16cabd092ad6e2e802a6626873c8`

PR #14 is still open, therefore the B13 branch is based on that exact commit rather
than an arbitrary newer `main`. B12 physics remains frozen: this gate does not
change the Reynolds, THD/TEHD, perturbation, dynamic-condensation, packed ABI, or
stationary type-5 bridge equations.

Branch:

`feature/b13-advanced-bearing-crud-20260926`

## Scope

B13 promotes the already persisted `RotorModel.advanced_bearings` collection to an
engineering CRUD surface for exactly:

- `CoefficientBearing`
- `PlainJournalPhysicsBearing`
- `TiltingPadPhysicsBearing`

The user workflow is:

`GUI draft -> unit conversion -> complete immutable domain object -> validate_advanced_bearing() -> QUndoCommand -> RotorModel.advanced_bearings -> Project Explorer -> persistence`

No QLineEdit/QTableWidget change mutates a persisted advanced bearing in place.

## Architecture

### AdvancedBearingEditor

`python/src/drm_studio/docks/advanced_bearing_editor.py`

The editor is a dedicated transactional PySide6 dialog. Family is explicit and
non-convertible during Edit. Node is selected only from existing RotorModel nodes.

The native-physics editor is organized as:

- General
- Geometry
- Pads
- Lubricant
- Operating Conditions
- Thermal
- Deformation
- Mesh
- Solver Controls
- Qualification

The coefficient editor exposes constant, speed 1-D, frequency 1-D, and
speed-by-frequency 2-D coefficient data for K/C/M plus pchip/linear
interpolation. Bearing mass M is never silently zeroed.

### Commands

`python/src/drm_studio/commands/model_commands.py`

B13 adds:

- `AddAdvancedBearingCommand`
- `EditAdvancedBearingCommand`
- `DeleteAdvancedBearingCommand`
- `DuplicateAdvancedBearingCommand`

The commands pre-validate a deep-copied candidate model, preserve list position,
and maintain a coherent Project Explorer selection. An accepted editor produces
one logical transaction, including all pad-table edits.

### Project Explorer

`Advanced Bearings (N)` now carries B13 context actions:

- New Coefficient Bearing...
- New Plain Journal...
- New Tilting Pad...
- Edit...
- Duplicate
- Delete...

Unsupported B12 advanced-bearing families remain visible/readable but are not
silently promoted to B13 CRUD.

## Units

Canonical domain storage remains SI.

The B13 editor presents:

- diameter and length: mm -> m
- radial clearance: µm -> m
- angle: degrees -> rad
- temperature: °C -> K
- stiffness: N/m
- damping: N·s/m
- pivot rotational stiffness: N·m/rad
- Young modulus: MPa -> Pa

Sentinel conversion tests include 101.6 mm -> 0.1016 m, 74.9 µm -> 74.9e-6 m,
and 18 deg -> radians.

## Validation and error UX

`validate_advanced_bearing()` remains the domain authority. The editor performs
only input parsing and narrowly scoped user-facing diagnostics before the domain
validator runs.

Invalid blank/text/NaN/Inf data, invalid nodes, mismatched pad arrays, invalid
preload/offset, duplicate axes, incompatible coefficient shapes, and invalid mesh
counts are rejected before a command mutates the model.

Domain preload/offset diagnostics were sharpened to include the received value
without changing the underlying B12 physical contract.

## Persistence

B12 schema-2 typed advanced-bearing persistence is reused. No new project schema
is introduced.

B13 adds representation normalization for coefficient vectors/grids when JSON
lists are restored into the typed domain object. This is persistence
normalization only; coefficient values and physics are unchanged.

The qualification compares reconstructed domain objects after save/reopen rather
than comparing only JSON text.

Legacy projects with no advanced bearings keep the historical canonical payload
and model hash behavior.

## Qualification and provenance security

The Qualification tab is read-only. It can display existing family,
qualification state, ROSS authority SHA, and provider provenance, but the B13
editor never provides a user-editable text field for creating or altering such
claims.

Existing `provenance` is preserved verbatim by Edit. Newly created bearings do
not gain qualification claims merely because a user entered defaults.

Solver bridge release remains controlled by the existing B12 runtime contract,
not by arbitrary UI text.

## Explicit exclusions

B13 does not implement or promote:

- B14 async/QThread/job manager/progress/cancel/pressure/temperature/film plots
- B15 iRdin/Cryostar conversion
- B16 operating-point maps/cache
- B17 matched-whirl/Campbell frequency matching
- B18 advanced-bearing run-up
- ThrustPad or axial DOF
- floating-ring or gas-bearing CRUD promotion
- new seal families
- coaxial advanced-bearing support
- rotating/asymmetric advanced-bearing support
- bearing M assembly

Those paths remain fail-closed exactly as before B13.

## Test matrix

### Domain

`python/tests_bearings/test_b13_advanced_bearing_crud.py`

Covers coefficient scalar/1-D/2-D axes and interpolation, invalid axes/shapes,
PlainJournal thermal/deformation variants, TiltingPad pad-array and mesh rules,
typed serialization, save/reopen, and model hash behavior.

### Commands and GUI

`python/tests_ui/test_ui_b13_advanced_bearing_crud.py`

Covers GUI->SI->domain sentinels, five-pad permutation detection, 2-D K/C/M,
Add/Edit/Delete/Duplicate with Undo/Redo, Cancel with zero model mutation,
read-only provenance, invalid input, persistence round-trip, and Project Explorer
B13 contexts.

### Frozen applications

The existing packaged qualification is extended by
`python/src/drm_studio/b13_qualification.py`. In the clean frozen executable it
constructs all three B13 families through the real PySide6 editor draft,
commits them through B13 commands, exercises Edit/Duplicate/Delete/Undo,
saves, closes/reloads the project model, and compares the resulting engineering
objects.

The dedicated workflow is:

`.github/workflows/b13-advanced-bearing-crud.yml`

It requires Linux and Windows source gates, Stage 1 exactly 57/57, B12 advanced
bearing regression, and clean frozen Linux/Windows B13 CRUD smoke.

## Qualification result

Until all gates succeed on the same final commit:

`B13_ADVANCED_BEARING_CRUD = BLOCKED`

Blocker at implementation commit time: same-head Linux/Windows source and frozen
GitHub Actions evidence has not yet completed.

The exact qualified HEAD is written by the dedicated same-head workflow and will
be recorded here only after the aggregate gate succeeds.
