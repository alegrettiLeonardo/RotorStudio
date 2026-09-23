# RotorStudio — DRM Fortran 2018 + Python Core — Stage 1 M3

This repository is a continuation of the same Stage 1 migration baseline. It does **not** restart or reinterpret the MATLAB project. `Rotor_Software_v2` remains the numerical and behavioural authority; the manual and examples remain secondary references.

Stage 1 contains **no desktop application UI**. Python supplies typed model data, validation, units, orchestration, ctypes, post-processing, reports, CLI and examples. Fortran 2018 supplies the qualified numerical/physical kernel.

## Implemented through M3

Stationary-frame path:

- circular `shftelem` types 1..8;
- tapered `taper` types 21..28;
- disks types 1..4;
- `bearmtx` types 1..8, including the short-width fluid-film model and seal model;
- rigid constraints and restored zero DOFs;
- global M/C/G/K assembly;
- stationary modal eigensystem;
- synchronous `freq_rsp` including unbalance force, unbalance moment, bent shaft and type-8 rotating moment/PZT forcing;
- `crit_spd` direct method, iterative mode-number method, and initial-estimate method.

Coaxial path:

- `chr_root_coax` physics and assembly path;
- rotor speed factors, including negative/opposite rotation;
- type-20 inter-rotor coupling;
- `freq_rsp_coax` with V2 excitation-speed rules;
- V2 behaviour retained where speed-dependent bearing properties use the reference rotor speed.

Rotating-frame / asymmetric path:

- `shftasym` types 11..18 for the executable zero-axial-load V2 path;
- `rotorasym`, including conversion of circular shaft definitions to rotating-frame asymmetric elements;
- disk types 1..6 in the rotating frame;
- `bearasym` types 1..4;
- `chr_asym` including its V2 output-count-dependent `K1b` behaviour;
- `freq_asym` static rotating-frame unbalance response.

The V2 defects in `bearasym` and `chr_asym` are preserved deliberately in the compatibility path rather than silently corrected. The undefined `shftasym` nonzero axial-load branch is explicitly blocked.

## Qualification status

M3 executes:

- 4/4 CTest tests in Release;
- 4/4 CTest tests in Debug with runtime checks;
- 36/36 Python tests;
- source-derived formula/oracle tests for `bearmtx`, `freq_rsp`, all three `crit_spd` methods, coaxial and asymmetric paths;
- smoke translations of `Example_05_08_01`, `Example_06_06_01` and `Example_07_06_01`.

MATLAB/Octave is unavailable in the current qualification environment. Therefore MATLAB↔Fortran equivalence gates remain `BLOCKED`; source-derived tests are additional evidence and do not replace the authoritative MATLAB baseline.

## Build and test on Linux

```bash
cmake -S fortran -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release -j
ctest --test-dir build-release --output-on-failure

export PYTHONPATH="$PWD/python/src"
export DRMROTOR_LIB="$PWD/build-release/libdrmrotor.so"
python -m pytest python/tests -q
```

Relevant reports are in `docs/IMPLEMENTATION_M3.md`, `docs/SOURCE_DERIVED_QUALIFICATION_M3.md`, `validation/legacy_cases/README.md`, and `validation/reports/QUALIFICATION_STATUS_M3.md`.
