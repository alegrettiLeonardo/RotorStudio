# MATLAB V2 compatibility

## Authority order

1. `Rotor_Software_v2` — numerical and behavioural authority.
2. Manual V1 — intent, terminology and contracts.
3. 22 example scripts.
4. 83 DRM book-problem scripts.

The original V2 archive SHA256 is `bc42d18020013a537da6e7785a3d6b15533cd881939410c5e2a58c8563db5344`. Numerical authority sources are frozen under `reference/matlab_v2` and checked against canonical LF SHA256 values before formal qualification.

## Preserved conventions

The migration preserves V2 DOF ordering, signs/phases, SI solver units, constrained DOF behaviour, matrix/result ordering, FW/BW semantics used by the legacy routines, speed-dependent bearing behaviour and the split between stationary, coaxial and rotating-frame solvers.

## Known intentional compatibility choices

- `time_fdn.m` and `runup.m`: V2 uses modal truncation through `eig(K,M)`, although Manual V1 describes Guyan/static reduction. Stage 1 preserves V2.
- `shftasym.m`: the incorrect default-argument guard and undefined `Kre` axial-force branch are not silently repaired. The translated compatibility path rejects the non-executable axial branch explicitly.
- `bearasym.m` type 4: the legacy reverse rotational index behaviour is preserved where V2 behaviour is the target.
- `chr_asym.m`: output-count-dependent use of `K1b` is represented explicitly by the Python `want_vectors`/eigensystem path rather than normalized away.
- `freq_fdn.m` / `time_fdn.m`: the V2 `type > 2 OR type < 9` predicate is documented and preserved for compatibility.
- `runup.m`: mixed `jot` and MATLAB/Octave builtin `j` semantics are preserved by the qualified forcing definition.

Runtime probes live in `validation/legacy_cases`; static source evidence alone is not used as a substitute for a runtime observation.
