# Commands executed — M2

Key commands actually executed in the continuation workspace:

```bash
cmake -S fortran -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release -j2
ctest --test-dir build-release --output-on-failure

cmake -S fortran -B build-debug -DCMAKE_BUILD_TYPE=Debug
cmake --build build-debug -j2
ctest --test-dir build-debug --output-on-failure

export PYTHONPATH=$PWD/python/src
export DRMROTOR_LIB=$PWD/build-release/libdrmrotor.so
python -m pytest -q python/tests
python validation/scripts/run_m2_internal_qualification.py

python -m drm_core.cli.main validate examples/models/m2_smoke.json
python -m drm_core.cli.main frequency-response examples/models/m2_smoke.json --start-rpm 500 --stop-rpm 1500 --step-rpm 500
python -m drm_core.cli.main critical-speeds examples/models/m2_smoke.json --number 3 --method direct

python examples/chapter05/example_05_08_01.py --outdir validation/example_05_08_01_m2
python examples/chapter06/example_06_03_01.py --case 1 --outdir validation/example_06_03_01_m2
python examples/chapter06/example_06_08_01.py --lh-case 1 --rh-case 1 --outdir validation/example_06_08_01_m2
```

Clean-package validation additionally extracted the candidate archive into an empty directory, rebuilt both configurations, installed the Python package into a clean target with `pip --no-build-isolation --no-deps` because the execution sandbox has no network access, ran all tests/CLI/example smokes, and verified no dependency on the original working tree.
