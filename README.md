# RotorStudio — DRM Fortran 2018 + Python Core — Stage 1 M2

This repository continues the Stage 1 migration of the Friswell/Penny/Garvey/Lees MATLAB rotor software. MATLAB V2 remains the numerical and behavioural authority. The current increment does **not** claim full toolbox equivalence because MATLAB/Octave execution is unavailable in the qualification environment.

Implemented through M2:

- circular shaft `shftelem` types 1..8;
- tapered shaft `taper` types 21..28;
- asymmetric element `shftasym` zero-axial-load executable path, with known V2 defects explicitly preserved/documented;
- disks types 1..4;
- `bearmtx` types 1..8 (constant, short fluid-film and seal);
- stationary M/C/G/K assembly;
- modal eigensystem;
- synchronous `freq_rsp` path;
- direct and iterative-by-mode-number `crit_spd` paths;
- ISO_C_BINDING + ctypes ABI;
- GUI-independent Python domain/validation/analysis/post/CLI core;
- end-to-end `Example_05_08_01` execution without MATLAB.

No desktop UI is included in Stage 1.

## Build and test on Linux

```bash
cmake -S fortran -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release -j
ctest --test-dir build-release --output-on-failure

export PYTHONPATH="$PWD/python/src"
export DRMROTOR_LIB="$PWD/build-release/libdrmrotor.so"
python -m pytest python/tests -q
python examples/chapter05/example_05_08_01.py
```

See `docs/IMPLEMENTATION_M2.md` and `validation/reports/QUALIFICATION_STATUS_M2.md` for exact implemented scope and gate status.
