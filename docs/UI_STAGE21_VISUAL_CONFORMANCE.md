# Stage 2.1 — Visual Conformance

Stage 2.1 is a presentation-layer revision over the functionally qualified Stage 2 desktop application.

Baseline:

- `main@a20385319f550761e62c02ca5f5f6a21923b610e`
- no Fortran source changes are permitted;
- `drm_core`, `AnalysisService`, `SolverFacade` and the existing Fortran numerical paths remain the engineering authority.

## Visual authority

The three Stage 2 mockups remain the UI authority for window structure, pagination, toolbar hierarchy, Project Explorer, result workspaces, right-side inspector and bearing workspace.

The additional 3-D mode-shape reference supplied for Stage 2.1 defines the visualization language for modal shapes:

- black undeformed shaft reference;
- red deflected real-phase centerline;
- red mode stations;
- magenta whirl-orbit loops along the shaft;
- X/Y lateral directions and Z axial direction.

The 3-D renderer consumes the existing complex eigenvector. It does not calculate eigenvalues, matrices, critical speeds, response or any new rotor physics.

## Stage 2.1 implementation

### Iconography

`QtAwesome` provides an open, consistent icon vocabulary for:

- New / Open / Save;
- Model / Analysis / Results / Repeat / Report;
- Zoom / Fit / Pan / Help;
- modal, Campbell, critical speeds, response, foundation, run-up, coaxial, asymmetric and bearing actions;
- Project Explorer nodes.

Qt standard icons remain the fallback when QtAwesome is absent. Core-only installation remains GUI independent because QtAwesome is part of the `studio` optional dependency.

### Main-window proportions

The default workspace targets the mockup proportions:

- Project Explorer: approximately 260 px;
- Results / Element Properties: approximately 360 px;
- Messages & Results: approximately 175 px;
- central document workspace receives the remaining width.

User-customized QSettings layouts remain restorable, subject to useful minimum dock widths.

### Document pagination

Default central pages:

`Rotor Model | Bearing Performance | +`

Result documents are inserted before the `+` page.

Campbell result pagination is:

`Campbell | Root Locus | Modes | Orbits | FRF | +`

The FRF page inside a Campbell result is intentionally disabled because frequency response is a separate real result object. No synthetic FRF is generated to satisfy the mockup.

### Context inspector

The right dock switches between:

- `Element Properties` for model editing;
- `Results Properties` for result documents.

Results Properties exposes case, analysis kind, status, backend and analysis hash together with real export/rerun/report actions.

### Bearing Performance

The central bearing workspace exposes Stage 1 physics only:

- rigid short / long;
- constant K/C variants;
- full K/C;
- short hydrodynamic bearing;
- seal;
- coaxial coupling where applicable.

Unsupported conceptual BePerf families remain disabled. Pressure and temperature tabs are shown but disabled because no qualified pressure-field or thermal bearing solver exists.

### 3-D mode shapes

`drm_core.post.modes.plot_mode_3d()` is a visualization-only API. The legacy `plot_mode()` contract is retained unchanged.

The new renderer is used by the Stage 2.1 modal and Campbell workspaces.

## Qualification

Workflow:

`Stage 2.1 Visual Conformance`

It requires:

- zero Fortran diff against `a20385319f550761e62c02ca5f5f6a21923b610e`;
- 57/57 Stage 1 Python regression;
- full Stage 2 UI test suite with no skipped real-Fortran tests;
- structural visual tests for toolbar icons, dock widths, document pagination and bearing tabs;
- real modal result feeding the 3-D mode-shape renderer;
- real application screenshots:
  - `rotor_model.png`
  - `campbell_results.png`
  - `bearing_seal_editor.png`
  - `mode_shape_3d.png`
  - `frequency_response.png`
  - `runup_transient.png`

Visual comparison remains structural/human-reviewed rather than pixel-perfect because Qt platform chrome and font rasterization vary.
