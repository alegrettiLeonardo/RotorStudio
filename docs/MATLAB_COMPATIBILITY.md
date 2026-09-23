# MATLAB compatibility authority — M2

Authority remains: `Rotor_Software_v2 > Manual V1 > Examples > Problem scripts`.

M2 continues directly from the M1 preserved source baseline. No historical alternative solver was substituted.

Neither MATLAB nor GNU Octave is available in the execution environment. Therefore a fresh authoritative numerical baseline cannot be generated and every MATLAB↔Fortran equivalence gate remains **BLOCKED**. Internal structural tests, cross-method consistency and source-derived limiting relations are recorded separately and are not labeled equivalence.

Known documentation mismatch retained: Manual V1 describes Guyan/static reduction for `time_fdn` and `runup`, whereas V2 source uses an eigenvector-based modal truncation (`eig(K,M)` then first `nr` eigenvectors). V2 behavior remains the target when these routines are migrated.
