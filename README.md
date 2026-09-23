# RotorStudio — DRM Fortran 2018 + Python Core — Stage 1 M4

This repository continues the same Stage 1 MATLAB-to-Fortran/Python migration baseline. `Rotor_Software_v2` remains the numerical and behavioural authority. Stage 1 contains **no desktop UI**.

## Implemented through M4

The Fortran 2018 kernel now covers the implemented stationary, coaxial and rotating/asymmetric paths: circular and tapered shafts, executable asymmetric shaft paths, disks, legacy bearings/seals, M/C/G/K assembly, modal analysis, synchronous response, auxiliary excitation, foundation frequency response, critical speeds, coaxial modal/response, and rotating-frame asymmetric modal/response.

Python provides the typed domain model, validation, SI/unit conversion, ctypes bridge, result objects, post-processing, CLI, persistence/report scaffolding, tests and deterministic book examples.

M4 adds:

- stationary eigenvectors, bearing eccentricity and Python whirl/kappa post-processing;
- `freq_aux` and `freq_fdn`, because the example campaign exposed these still-missing Phase-6 paths;
- Python entry points for all 22 supplied book examples;
- a deterministic 32-run example campaign spanning default and representative menu variants.

## M4 qualification

Executed locally from the M4 sources:

- Fortran Release: **4/4 CTest PASS**
- Fortran Debug with runtime checks: **4/4 CTest PASS**
- Python: **40/40 pytest PASS**
- Example campaign: **32 runs / 30 PASS_IMPLEMENTED_SCOPE / 2 BLOCKED_PHASE8 / 0 FAIL / 22 unique examples**
- Exact delivery ZIP: clean extract, offline Python package install, Fortran rebuild, CTest, pytest and example campaign all completed successfully.

At unique-example level, **20/22 examples are complete for the declared pre-Phase8 scope**. Two are deliberately partial:

- `Example_06_05_01`: the frequency-domain `freq_fdn` branch passes; its `time_fdn` branch remains `BLOCKED_PHASE8_TRANSIENT`.
- `Example_06_11_01`: the modal/Campbell precheck passes; `runup` remains `BLOCKED_PHASE8_RUNUP`.

No `time_fdn`, `runup`, ODE integrator or Dormand–Prince implementation was added in M4. The M4 `freq_fdn` ABI is qualified for the supplied two-bearing example topology; generalized variable-width foundation forcing is not yet claimed.

MATLAB/Octave is not available in the qualification environment, so MATLAB↔Fortran numerical-equivalence gates remain **BLOCKED**. Source-derived/oracle tests and translated examples are additional evidence; they do not replace the authoritative MATLAB baseline.

## Build and test on Linux

```bash
cmake -S fortran -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release -j
ctest --test-dir build-release --output-on-failure

export PYTHONPATH="$PWD/python/src:$PWD"
export DRMROTOR_LIB="$PWD/build-release/libdrmrotor.so"
python -m pytest python/tests -q
python scripts/run_example_campaign.py --outdir validation/reports/example_campaign_M4
```

See `docs/IMPLEMENTATION_M4.md`, `docs/EXAMPLE_CAMPAIGN_M4.md`, `docs/SOURCE_DERIVED_QUALIFICATION_M3.md`, `validation/legacy_cases/README.md`, and `validation/reports/QUALIFICATION_STATUS_M4.md`.
