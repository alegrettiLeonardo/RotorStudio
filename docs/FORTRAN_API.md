# Fortran C ABI — solver version 0.3.0

The external boundary is `BIND(C)` and caller-owned memory. All physics arrays use IEEE double / Fortran `real64`; model values are SI; fixed-width legacy matrices are column-major.

Exported entry points:

- `rd_version(...)`
- `rd_shaft_element_legacy(...)` — circular, tapered and asymmetric element matrix bridge.
- `rd_assemble_legacy(...)` — stationary `M`, `C0`, `G/C1`, `K0`, `K1`, constrained-DOF mask and bearing eccentricity.
- `rd_modal_legacy(...)` — stationary eigenvalues.
- `rd_modal_full_legacy(...)` — eigenvalues, displacement eigenvectors and bearing eccentricity.
- `rd_frequency_response_legacy(...)` — synchronous `freq_rsp` complex response as separate real/imag arrays.
- `rd_critical_speeds_legacy(...)` — critical speeds plus iterations/convergence.
- `rd_critical_speeds_full_legacy(...)` — critical speeds plus complex mode shapes, iterations/convergence.

Legacy input shapes:

- shaft `(11,nshaft)`;
- disk `(6,ndisc)`;
- bearing `(34,nbearing)`;
- frequency-response force `(5,nforce)`;
- bend `(3,nbend)`.

Complex outputs cross the ABI as separate `real[]` and `imag[]` buffers. Python recomposes them as NumPy complex arrays.

Status codes from `rd_status`:

- `0`: `RD_OK`;
- `10`: invalid/undefined input;
- `20`: unsupported legacy option;
- `30`: LAPACK failure;
- `40`: known legacy-source defect gate;
- `50`: convergence failure/reserved convergence status.
