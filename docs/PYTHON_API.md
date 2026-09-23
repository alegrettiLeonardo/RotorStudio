# Python Core API — M2

Primary domain types:

- `RotorModel`, `Node`;
- `ShaftElement`, `TaperedShaftElement`, `AsymmetricShaftElement`;
- `Disk`, `Bearing`, `Force`, `BendPoint`.

`RotorModel.from_legacy_arrays(...)` provides a migration path from MATLAB-style definitions. Stationary validation enforces sequential node numbers because the V2 stationary source indexes definitions by node number.

Primary analysis functions:

- `run_assembly(model, speed_rad_s)` -> `AssemblyResult`;
- `run_modal(model, speed_rad_s)` -> `ModalResult`;
- `run_campbell(model, speeds_rad_s)` -> `CampbellResult`;
- `run_frequency_response(model, speeds_rad_s)` -> `FrequencyResponseResult`;
- `run_critical_speeds(...)` -> `CriticalSpeedResult`.

`AnalysisService` exposes the same functions as a GUI-independent application service for future Stage-2 worker/thread integration. Every analysis routes through `SolverFacade -> FortranBackend -> ctypes`; there is no alternate Python rotor solver.

Canonical model units are SI. `rpm_to_rad_s` and `rad_s_to_rpm` are provided at the boundary.
