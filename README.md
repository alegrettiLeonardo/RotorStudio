# RotorStudio — Fortran 2018 + Python Core — Stage 1 M7

RotorStudio is the Stage 1 migration of the DRM rotor-dynamics toolbox to a Fortran 2018 numerical core with a Python pre/post-processing and orchestration layer. Stage 1 intentionally contains no desktop UI.

`Rotor_Software_v2` remains the numerical and behavioural authority.

## M7 qualification closure

The qualified implementation has completed the formal V2 equivalence gates G5–G12 with a frozen GNU Octave 7.1.0 authority run. The qualified head `224a279a5450f7d6054f639efe2f7ce306aa00e9` was merged into `main` by `97d482655f363fcc821b10879a3853066d6d6a0b`.

User-executed evidence on the qualified head:

- Fortran Release CTest: **5/5 PASS**
- Python qualification suite: **49/49 PASS**
- 22-example campaign: **33/33 PASS**, **22 unique examples**
- Formal equivalence G5–G12: **OVERALL PASS**
- No formal threshold was relaxed after observing Fortran results.

M7 adds repository-owned authority-source integrity checks and CI that continuously reproduces:

1. Linux Release build, CTest, Python tests and the example campaign.
2. Linux Debug build with runtime checks.
3. Formal G5–G12 equivalence using the pinned `gnuoctave/octave:7.1.0` authority runtime.

See:

- `validation/reports/QUALIFICATION_STATUS_M7.md`
- `validation/reports/FORMAL_EQUIVALENCE_M7.json`
- `validation/equivalence/authority_source_manifest.json`
- `.github/workflows/stage1-m7-qualification.yml`

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

First verify that the committed numerical V2 authority sources exactly match the frozen source manifest:

```bash
python validation/equivalence/verify_authority_sources.py
```

Then generate the independent transient references, create an authority baseline with GNU Octave 7.1.0, freeze transient tolerances before comparison, and run the formal comparator. The CI workflow performs these steps automatically and uploads the resulting evidence.

The next unclosed engineering gates are G14 (independent book-problem regression) and G17 (Windows execution qualification).
