# RotorStudio — DRM Fortran 2018 + Python Core — Stage 1 M2

This is a continuation of the executed M1 baseline, not a restart and not a claim that the complete MATLAB toolbox is qualified.

Implemented in this increment:

- circular shaft element `shftelem.m` types 1–8;
- tapered shaft element `taper.m` types 21–28;
- asymmetric shaft element `shftasym.m` types 11–18 at the element level, with the V2 axial-force broken branch explicitly gated rather than silently repaired;
- stationary `rotormtx.m` assembly for circular/tapered shafts and disk types 1–4;
- `bearmtx.m` types 1–8 plus legacy type-20 no-op behavior in single-rotor assembly;
- full stationary modal result through `ctypes -> ISO_C_BINDING -> Fortran -> LAPACK`;
- `freq_rsp.m` synchronous frequency response;
- `crit_spd.m` direct, iterative-by-index and iterative-nearest methods;
- Python typed domain, validation, result objects, `AnalysisService`, CLI and headless post-processing;
- end-to-end `Example_05_08_01` retained and re-executed.

MATLAB/Octave is not installed in the execution environment, so every MATLAB↔Fortran numerical equivalence declaration remains **BLOCKED**. Internal source-contract tests and invariants are reported separately and never promoted to MATLAB-equivalence PASS.

## Linux build

```bash
./scripts/build_linux.sh
export PYTHONPATH="$PWD/python/src"
export DRMROTOR_LIB="$PWD/build-release/libdrmrotor.so"
python -m pytest -q python/tests
python examples/chapter05/example_05_08_01.py --outdir example_05_08_01_out
```

## CLI

```bash
drm-cli validate examples/models/m2_smoke.json
drm-cli modal examples/models/m2_smoke.json --speed-rpm 1000
drm-cli frequency-response examples/models/m2_smoke.json --start-rpm 500 --stop-rpm 1500 --step-rpm 500
drm-cli critical-speeds examples/models/m2_smoke.json --number 3 --method direct
```

There is **no desktop UI** in Stage 1.

See `validation/reports/QUALIFICATION_STATUS.md`, `validation/reports/M2_QUALIFICATION.md` and `docs/MATLAB_TO_NEW_CODE.md`.
