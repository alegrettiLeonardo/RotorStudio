# Architecture — Stage 1 M2

The executable boundary is:

`Python domain / validation / AnalysisService -> SolverFacade -> ctypes -> ISO_C_BINDING -> Fortran 2018 -> BLAS/LAPACK`.

Python does not contain a rotor eigensolver, FRF solver or critical-speed solver. Fortran owns the qualified numerical path; Python owns typed input, SI-unit boundaries, validation, orchestration, result objects, persistence/CLI hooks and post-processing.

## Fortran ownership in M2

- `rd_shaft_circular`: `shftelem.m`, shaft types 1–8.
- `rd_shaft_tapered`: `taper.m`, shaft types 21–28.
- `rd_shaft_asymmetric`: `shftasym.m`, shaft types 11–18 at element level.
- `rd_bearings`: `bearmtx.m`, types 1–8 and legacy type-20 stationary no-op behavior.
- `rd_assembly_stationary`: stationary shaft/disk assembly corresponding to the migrated `rotormtx.m` scope.
- `rd_eigensystem`: stationary first-order eigensystem.
- `rd_frequency_response`: `freq_rsp.m` synchronous response.
- `rd_critical_speed`: `crit_spd.m` methods 1, 2 and 3.
- `rd_lapack`: centralized BLAS/LAPACK-facing linear algebra.
- `rd_c_api`: C ABI only; internal Fortran types are not exposed.

`rotorasym.m`, `bearasym.m`, `chr_asym.m`, coaxial and transient solvers remain outside the executed M2 scope.

## Python ownership in M2

`RotorModel` supports circular, tapered and asymmetric shaft domain types. Stationary services deliberately reject asymmetric shafts until the rotating-frame solver is migrated. `AnalysisService` provides assembly, modal, Campbell, synchronous frequency response and critical-speed operations without any GUI dependency.

No PySide/PyQt/Tk/wx/web UI package is imported by `drm_core`; this is automatically tested.
