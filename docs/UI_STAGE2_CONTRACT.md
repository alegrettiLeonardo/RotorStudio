# Stage 2 UI contract

No desktop UI is implemented in Stage 1. This document only defines the boundary a later PySide6 application may consume.

## Permitted UI dependencies

A Stage 2 UI may depend on public Python Core concepts:

- `RotorProject` / `RotorModel`
- typed components including `Seal`
- `AnalysisCase`
- `AnalysisService`
- immutable analysis result objects
- persistence/report helpers
- Phase 9 figure/data export APIs
- model/project/analysis hashes and result metadata

## Required flow

```text
UI widgets
  -> Python domain/validation
  -> AnalysisService
  -> SolverFacade
  -> ctypes
  -> Fortran 2018
```

The UI must not call the C ABI directly, implement rotor matrices, contain numerical fixes, or parse solver memory layouts. It may execute `AnalysisService` in a worker thread/process because Stage 1 APIs do not depend on widgets.

## Stale-result support

Stage 1 exposes deterministic project/model/analysis hashes plus analysis options and build metadata. Stage 2 may compare those hashes to mark displayed results stale after a model/case edit. Stage 1 itself contains no widget state or stale-result UX.
