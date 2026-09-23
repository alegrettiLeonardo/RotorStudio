# Stage 2 UI contract (documentation only)

A future desktop UI may construct `RotorModel`, call validation and analysis services, and consume immutable/controlled result objects. It must not call Fortran directly or duplicate solver physics. Long-running calls can later be wrapped by UI worker threads because the Python Core has no widget dependency.

No GUI library or desktop shell is implemented in Stage 1.
