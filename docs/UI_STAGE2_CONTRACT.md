# UI Stage 2 contract

No desktop UI is implemented in Stage 1.

A future PySide6 desktop shell may depend on:
- `RotorProject` for project state
- `RotorModel` and typed domain objects for editable engineering data
- `AnalysisCase` for reproducible solver options
- `AnalysisService.run(model, case)` as the analysis execution boundary
- immutable/controlled result objects with model/analysis hashes
- persistence and report APIs
- Phase 9 plotting/export functions

UI code must not call `ctypes` or Fortran symbols directly. Long-running calls must be safe to wrap in a worker/thread boundary without modifying scientific routines. Stale-result detection should compare result `model_hash` and `analysis_hash` with current project/case hashes.

Stage 2 may add views, project explorer, editors and workspaces, but may not redefine numerical physics or duplicate the solver in Python.
