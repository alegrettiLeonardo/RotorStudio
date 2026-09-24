# RotorStudio — Fortran 2018 + Python Core

RotorStudio is the qualified migration of the DRM rotor-dynamics software to a Fortran 2018 numerical core with a GUI-independent Python Core for domain modelling, validation, units, persistence, orchestration, post-processing, reports, CLI and examples.

`Rotor_Software_v2` remains the numerical and behavioural authority. The desktop application is Stage 2 and consumes the qualified Stage 1 Core; it does not replace or reimplement the solver.

## Stage 1 — FINAL

Stage 1 is functionally closed for its declared scope.

- **G1–G19: PASS**
- **Python qualification suite: 57/57 PASS**
- **G14 book-problem regression: 83/83 inventoried and semantically classified; 83/83 deterministic regressions; 20/20 A/hybrid product comparisons**
- **G17 Windows execution: PASS**
- **G18 clean-package qualification: PASS**
- **Phase 9 / Python Core: PASS**
- **22-example campaign and graphical coverage: PASS**

The final evidence matrix is recorded in:

- `validation/reports/QUALIFICATION_STATUS_STAGE1_FINAL.md`
- `docs/ARCHITECTURE.md`
- `docs/PYTHON_API.md`
- `docs/FORTRAN_API.md`
- `docs/UI_STAGE2_CONTRACT.md`

Historical M2–M7 reports are retained unchanged for traceability; they are not the current Stage 1 status.

## Stage 2 — Desktop UI

Stage 2 adds the PySide6 / Qt 6 desktop application over the existing qualified stack:

```text
PySide6 / Qt 6 desktop UI
        ↓
drm_core / AnalysisService
        ↓
SolverFacade / ctypes ABI
        ↓
Fortran 2018
        ↓
BLAS / LAPACK
```

The Stage 2 rule is strict: **the UI does not implement rotor-dynamics physics**. The Python API, CLI, Fortran tests and Stage 1 qualification remain headless and must continue to pass unchanged.

## Local Linux build and regression

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e './python[test]'

cmake -S fortran -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release -j
ctest --test-dir build-release --output-on-failure

export PYTHONPATH="$PWD/python/src:$PWD"
export DRMROTOR_LIB="$PWD/build-release/libdrmrotor.so"

python -m pytest python/tests -q
python scripts/run_example_campaign.py --outdir validation/reports/example_campaign_local
```

## Formal authority reproduction

Verify that the committed numerical V2 authority sources exactly match the frozen source manifest:

```bash
python validation/equivalence/verify_authority_sources.py
```

The qualification workflows reproduce the frozen Stage 1 authority and regression contracts, including Linux, Windows, G14 book problems and clean-package validation.
