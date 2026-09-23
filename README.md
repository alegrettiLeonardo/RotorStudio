# RotorStudio — DRM Fortran 2018 + Python Core — Stage 1 M5

This repository continues the same MATLAB-to-Fortran/Python Stage 1 migration baseline. `Rotor_Software_v2` remains the numerical and behavioural authority. Stage 1 still contains **no desktop UI**.

## M5 focus — Phase 8 transient

M5 starts Phase 8 without reopening or altering the M4 stationary/coaxial/asymmetric physics. The production additions are specifically:

- V2-style generalized modal truncation for `time_fdn` and `runup`;
- LAPACK `DGGEV` support for the `(K,M)` reduction problem;
- adaptive Dormand–Prince embedded 5(4) integration in Fortran 2018;
- `time_fdn` foundation-pulse response;
- `runup` response with V2 `phi(t)`, `Omega(t)` and acceleration forcing;
- ISO_C_BINDING/ctypes/Python result and CLI paths;
- frozen source-derived transient regression references in the delivery package.

The manual describes Guyan/static reduction, but MATLAB V2 actually uses `eig(K,M)` followed by the first `nr` eigenvectors. **M5 preserves the V2 modal truncation.**

## Qualification status

Executed in the M5 qualification environment:

- Fortran Release: **5/5 CTest PASS**
- Fortran Debug with runtime checks: **5/5 CTest PASS**
- Python delivery package: **47/47 pytest PASS**
- 22-example smoke campaign: **33/33 PASS**, **0 BLOCKED**, **0 FAIL**
- original full transient settings for `Example_06_05_01` case (b): **PASS_IMPLEMENTED_SCOPE**
- original full `Example_06_11_01` cases 1 and 2: **PASS_IMPLEMENTED_SCOPE**

Independent source-derived transient qualification against high-accuracy SciPy DOP853 gives:

```text
time_fdn max absolute response difference = 2.9704856645187266e-09 m
runup    max absolute response difference = 2.5818612682916922e-11 m
```

These values qualify the Fortran transient translation against an independent implementation of the V2 equations. They are **not MATLAB-equivalence results**.

MATLAB and Octave remain unavailable in this environment. Therefore the authoritative MATLAB/`ode45` numerical-equivalence gate remains **BLOCKED**; no transient tolerance was invented or relaxed.

## Build and test on Linux

```bash
cmake -S fortran -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release -j
ctest --test-dir build-release --output-on-failure

export PYTHONPATH="$PWD/python/src:$PWD"
export DRMROTOR_LIB="$PWD/build-release/libdrmrotor.so"
python -m pytest python/tests -q
python scripts/run_example_campaign.py --outdir validation/reports/example_campaign_M5
```

See:

- `docs/IMPLEMENTATION_M5_TRANSIENT.md`
- `docs/TRANSIENT_QUALIFICATION_M5.md`
- `validation/baseline/transient/README.md`
- `validation/reports/QUALIFICATION_STATUS_M5.md`
