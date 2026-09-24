# Python Core API

`drm_core` is independent of every desktop UI toolkit.

## Domain and project

Core domain classes include `RotorModel`, `Node`, circular/tapered/asymmetric shaft elements, `Disk`, `Bearing`, `Seal`, `Force`, `BendPoint`, `RotorDefinition`, `RotorProject` and `AnalysisCase`. `RotorModel.from_legacy_arrays(...)` remains available for traceable migration of V2 examples.

`Seal` is a typed Python representation of the V2 bearing type 8 contract and converts to the same solver-facing bearing row; it does not introduce new seal physics.

## AnalysisService

`AnalysisService.execute(project, case)` dispatches to the existing production analysis functions and therefore to `SolverFacade -> Fortran`. Supported case kinds cover modal/eigensystem, stationary/auxiliary/foundation responses, critical speeds, foundation transient, run-up, coaxial modal/response and asymmetric modal/response.

Every execution carries deterministic `analysis_hash`, project/model hash context, build metadata, solver version, timestamp and options. `save_project` / `load_project` provide JSON persistence and `write_analysis_report` emits machine-readable JSON plus a Markdown summary.

## Phase 9 post-processing

`drm_core.post.phase9` provides:

- `fft_scale`
- root-locus and eigenvalue-trace plots
- 3-D mode-shape and orbit plots
- synchronous response and FRF amplitude/phase plots
- `export_figure` for PNG/SVG/PDF
- `export_csv`, `export_npz`, and `export_bundle`

All plotting is headless-capable with Matplotlib Agg and never invokes a second physical solver.
