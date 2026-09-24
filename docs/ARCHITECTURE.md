# Stage 1 architecture

RotorStudio Stage 1 separates numerical authority from orchestration:

```text
RotorProject / RotorModel / validation / units
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

The Fortran core owns rotor physics, finite-element matrices, assembly, eigensystems, frequency response, critical speed, transient integration, coaxial analysis and rotating-frame asymmetric analysis. Python owns typed project/domain data, validation, SI conversion, persistence, orchestration, result objects, post-processing, exports, reporting, CLI and examples.

No desktop GUI library is imported by `drm_core`. Phase 9 post-processing is headless by construction. Future UI code must call `AnalysisService` rather than access ctypes directly.

The numerical authority remains `Rotor_Software_v2`. Manual intent never silently overrides executable V2 behavior.
