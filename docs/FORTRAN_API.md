# Fortran API

The production core is Fortran 2018 with explicit real64 kinds and BLAS/LAPACK. Public Python access is through `ISO_C_BINDING` exports in `fortran/src/rd_c_api.f90`; Fortran internal derived state is not exposed directly.

Major API families:
- legacy shaft element matrices: circular, tapered, asymmetric
- stationary/global assembly and bearing matrices
- modal eigenvalues/eigensystems
- frequency response, auxiliary response and foundation response
- critical speeds
- coaxial modal/frequency response
- asymmetric rotating-frame assembly/modal/response
- foundation transient and run-up

Arrays passed across the C ABI use explicit dimensions and Fortran-contiguous storage where required. Complex results cross the ABI as separate real/imaginary buffers and are reassembled in Python. Nonzero status codes become `SolverLibraryError`; no Fortran exception is allowed to surface as ambiguous Python output.

The ABI is exercised by production tests and explicit Windows/Linux qualification probes.
