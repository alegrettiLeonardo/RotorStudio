# Python API

Primary domain objects:
- `RotorModel`, `Node`, shaft element variants, `Disk`, `Bearing`, `Seal`, `Force`, `RotorDefinition`
- `RotorProject`
- `AnalysisCase`
- `AnalysisService`

Compatibility input remains available through `RotorModel.from_legacy_arrays(...)`.

Analysis results include modal, critical-speed, frequency-response, coaxial, asymmetric and transient result objects. Metadata includes solver version, model hash, analysis hash, UTC timestamp, analysis options and build/runtime information.

Persistence:
- `save_project(project, path)`
- `load_project(path)`

Reports:
- `result_summary`
- JSON and Markdown report writers

Phase 9 post-processing:
- `fftscale`
- Campbell, root-locus and eigenvalue plots
- mode shape and orbit plots
- response and FRF plots
- rotor schematic
- PNG/SVG/PDF figure export
- CSV/NPZ numerical export
- metadata JSON export

All plotting uses a headless Matplotlib backend and is independent of desktop UI frameworks.
