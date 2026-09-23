# Transient baseline status — Stage 1 M5

The authoritative baseline is still MATLAB V2. MATLAB/Octave is not installed in the qualification environment, so **MATLAB runtime baselines are BLOCKED** and no MATLAB-equivalence PASS is claimed.

To make Phase 8 reproducible while that gate is blocked, M5 freezes a **SOURCE_DERIVED_REFERENCE** for two canonical cases. These references are generated independently from the V2 equations using SciPy generalized eigensystems and high-accuracy `solve_ivp(method="DOP853")` integration. They are used only to qualify the new Fortran modal-truncation and Dormand–Prince implementation; they do not replace MATLAB V2.

Files:

- `time_fdn_source_reference.npz` — Example 6.5.1 topology, 10-mode V2-style modal truncation, half-sine foundation pulse.
- `runup_source_reference.npz` — Example 6.11.1 topology, 4-mode V2-style modal truncation, case-2 acceleration over the first 3 seconds.
- `SOURCE_HASHES.sha256` — SHA256 of the V2 routines and example scripts used to define the reference equations.

The production transient calculation remains Fortran. SciPy appears only in the qualification/generation script.
