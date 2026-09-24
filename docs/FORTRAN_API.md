# Fortran 2018 API

The production solver is built as a shared library (`libdrmrotor.so` on Linux, `drmrotor.dll` / `libdrmrotor.dll` on Windows). Physics uses explicit real64 precision. BLAS/LAPACK provide dense linear solves and eigenproblems; no custom eigensolver is used.

## C ABI

`rd_c_api.f90` exposes flat C-compatible entry points consumed only through `drm_core.solver.ffi`. Complex results cross the ABI as separate real/imaginary arrays and Python reconstructs complex NumPy arrays.

The configured production entry points include:

- `rd_modal_legacy`, `rd_modal_legacy_vectors`
- `rd_assemble_legacy`, `rd_bearings_legacy`
- `rd_freq_rsp_legacy`, `rd_freq_aux_legacy`, `rd_freq_fdn_legacy`
- `rd_crit_spd_legacy`, `rd_crit_spd_legacy_ex`
- `rd_coax_modal_legacy`, `rd_coax_freq_rsp_legacy`
- `rd_asym_assemble_legacy`, `rd_bearasym_legacy`
- `rd_asym_modal_legacy`, `rd_asym_freq_rsp_legacy`
- `rd_time_fdn_legacy`, `rd_runup_legacy`

Arrays are transferred as contiguous column-major buffers where the Fortran routine expects matrices. Ownership remains with the caller; Fortran fills caller-allocated buffers. Every ABI routine returns a status integer and Python raises `SolverLibraryError` on nonzero status.

## Build modes

CMake keeps Release and Debug trees separate. The qualification workflows record compiler/CMake/BLAS information, run CTest in both configurations and explicitly load the shared library through ctypes. Windows dependency lookup is hardened with `os.add_dll_directory`.
