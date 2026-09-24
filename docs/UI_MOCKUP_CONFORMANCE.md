# Stage 2 mockup conformance

The three supplied mockups are the visual authority for Stage 2. Comparison is structural rather than pixel-perfect because Qt font metrics and platform rendering differ. Screenshots are captured from the real application by `scripts/capture_stage2_ui.py` while `DRMROTOR_LIB` points to the freshly built Fortran library. No mock backend or fabricated plot data is used.

## Mockup 1 — Rotor Model

Implementation screenshot: `validation/reports/stage2_screenshots/rotor_model.png`.

Implemented structure:
- native menu bar and dense icon/text toolbar;
- left Project Explorer;
- central QGraphicsView rotor model;
- right type-sensitive Element Properties dock;
- Analysis Modules launcher row;
- bottom Messages & Results dock;
- status bar with units/model counts;
- synchronized tree/canvas/property selection.

Intentional differences:
- icons are Qt/project-owned assets rather than Dyrobes proprietary assets;
- calculated shaft A/I/J/mass remain absent unless supplied by Core metadata; the UI does not duplicate engineering calculations;
- exact font metrics and title-bar rendering follow the host OS.

UI20 evidence: final workflow generates the screenshot and requires a non-empty file.

## Mockup 2 — Bearing / Seal

Implementation screenshot: `validation/reports/stage2_screenshots/bearing_seal_editor.png`.

Implemented:
- bearing selection from the real project;
- type-sensitive property editor for Stage 1 types 1–8 and coaxial type 20;
- short hydrodynamic bearing F/D/L/clearance/viscosity;
- seal P/R/L/clearance/V/friction;
- full constant K/C variants, including cross-coupling;
- display geometry in mm while storing canonical SI;
- undo/redo and Core validation.

Intentional capability deviation:
- the mockup's tilting-pad, floating-ring, gas-bearing, thrust-bearing, pressure-distribution and thermal-performance concepts are not implemented because Stage 1 contains no such solvers;
- the UI explicitly labels those families `NOT AVAILABLE / FUTURE` and never creates synthetic pressure, temperature, loss or coefficient results;
- therefore the central BePerf-style pad schematic/pressure charts are intentionally absent.

This is a physics-boundary deviation, not an unfinished imitation of unsupported functionality.

## Mockup 3 — Results / Campbell

Implementation screenshot: `validation/reports/stage2_screenshots/campbell_results.png`.

Implemented:
- document-style result workspace;
- Campbell branches using Stage 1 ordering;
- 1X/2X lines configured by the analysis case;
- kappa-derived FW/BW markers only when available;
- Root Locus tab;
- Modes / Orbits tab;
- real mode-shape and orbit post-processing;
- summary table;
- OUTDATED marker when model hash changes;
- rerun/delete result actions;
- plot/data/report exports.

Intentional differences:
- no MAC/Hungarian/new mode-tracking algorithm was added; Stage 1 ordering remains authoritative;
- critical-speed markers are only shown where supplied by a real CriticalSpeedResult rather than inferred graphically;
- exact plot palette is Matplotlib/platform dependent.

## Additional qualification screenshots

- `frequency_response.png` — real synchronous response from the Fortran backend.
- `runup_transient.png` — real run-up result and transient workspace.
- `bearing_seal_editor.png` — real application with supported bearing editor.

The final UI20 gate is PASS only when the final qualification workflow completes and these five screenshots are generated from its exact HEAD.
