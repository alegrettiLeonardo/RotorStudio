# Stage 1 M6 — formal equivalence closure framework

M6 does not change the numerical physics validated in M5. It makes the remaining MATLAB-authority closure deterministic and auditable.

The sequence is:

1. execute untouched V2 through `generate_authority_baseline.m`;
2. freeze transient limits from MATLAB-vs-independent-high-accuracy-oracle discrepancy only;
3. run the Fortran/Python comparison against the original fixed gates.

Fixed gates remain: element/global matrices 1e-12 relative; eigenvalues/natural frequencies 1e-8 relative; isolated-mode MAC >=0.999999; complex response 1e-8 relative; critical speeds 1e-6 relative; whirl/kappa 1e-10 absolute.

M6 adds qualification-only C ABI entry points for circular, tapered and asymmetric element matrices. They call the real Fortran element routines directly and do not create another solver.

Current authority status is BLOCKED because neither MATLAB nor Octave is installed. Package-index refresh was also attempted and timed out, so no substitute runtime was installed. No authority output was invented.
