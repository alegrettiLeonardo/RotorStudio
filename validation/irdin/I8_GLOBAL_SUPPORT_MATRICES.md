# I8 — global rotor/bearing/support matrix composition

I8 is matrix-first only. It appends two radial support DOFs per imported
bearing support and composes the already-qualified local I4 blocks into an
expanded global M/C/G/K system.

Rotor matrices are supplied without grounded bearing coefficients. For each
support station the native kernel adds bearing K/C between rotor and support
DOFs, support K/C to ground, and the imported support mass. New support
rows/columns in G are zero.

I8 does not solve eigenvalues or responses and does not change A0-A8 dispatch.
The project remains BLOCKED_FOR_NUMERICAL_ANALYSIS until an iRdin-specific
expanded-system modal/response solver path is independently qualified.
