# Stage 1 architecture

Stage 1 is deliberately split into a Fortran 2018 numerical authority and a GUI-independent Python Core. There is no desktop or web UI in this stage.

```text
RotorProject / RotorModel / AnalysisCase
              |
       AnalysisService
              |
         SolverFacade
              |
            ctypes
              |
         ISO_C_BINDING
              |
      Fortran 2018 core
              |
         BLAS / LAPACK
```

## Numerical ownership

All qualified rotor physics remains in Fortran: shaft elements, assembly, bearing/seal matrices, eigensystems, harmonic response, critical speed, transient integration, coaxial rotors and asymmetric/rotating-frame analyses. Python never introduces a substitute rotor solver.

Python owns domain objects, SI validation, orchestration, project persistence, result metadata, reports, CLI, scientific post-processing, figures and data export. Phase 9 therefore consumes Fortran results rather than recomputing the physical solution.

## Fortran modules

The production core is decomposed under `fortran/src`, including circular/tapered/asymmetric shafts, stationary/rotating assembly, bearing and eigensystem paths, frequency response, critical-speed routines, reduction, adaptive DP5(4), coaxial and asymmetric solvers, LAPACK wrappers and `rd_c_api.f90`.

## Python Core

`drm_core` exposes typed rotor entities, `RotorProject`, `AnalysisCase`, `AnalysisService`, `Seal`, validation, units, the ctypes backend, immutable analysis results, persistence/report helpers and headless Phase 9 post-processing. Project/model/analysis hashes are deterministic over canonical content; runtime metadata records solver/build/options information.

## Future UI boundary

A future Stage 2 desktop UI may call the Python Core only. It must not call Fortran directly, duplicate validation, parse MATLAB arrays, or contain numerical rotor physics.
