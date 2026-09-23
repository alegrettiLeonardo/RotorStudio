# Commands executed — M4

```bash
cmake -S fortran -B build-release-m4 -DCMAKE_BUILD_TYPE=Release
cmake --build build-release-m4 -j2
ctest --test-dir build-release-m4 --output-on-failure

cmake -S fortran -B build-debug-m4 -DCMAKE_BUILD_TYPE=Debug
cmake --build build-debug-m4 -j2
ctest --test-dir build-debug-m4 --output-on-failure

export PYTHONPATH="$PWD/python/src:$PWD"
export DRMROTOR_LIB="$PWD/build-release-m4/libdrmrotor.so"
python3 -m pytest -q python/tests
python3 scripts/run_example_campaign.py --outdir validation/reports/example_campaign_M4
```

Campaign result: 32 runs over 22 unique examples; 30 PASS_IMPLEMENTED_SCOPE, 2 BLOCKED_PHASE8, 0 FAIL.

## Clean package / exact delivery archive

The execution environment is offline, so Python package installation used the already installed local build backend rather than network build isolation:

```bash
pip install --no-deps --no-build-isolation --target "$ROOT/_site" "$ROOT/python"
cmake -S "$ROOT/fortran" -B "$ROOT/build-release-clean" -DCMAKE_BUILD_TYPE=Release
cmake --build "$ROOT/build-release-clean" -j2
ctest --test-dir "$ROOT/build-release-clean" --output-on-failure
PYTHONPATH="$ROOT/_site:$ROOT/python/src" DRMROTOR_LIB="$ROOT/build-release-clean/libdrmrotor.so" python -m pytest -q "$ROOT/python/tests"
PYTHONPATH="$ROOT/_site:$ROOT/python/src" DRMROTOR_LIB="$ROOT/build-release-clean/libdrmrotor.so" python "$ROOT/scripts/run_example_campaign.py"
```

The final ZIP was extracted to an empty directory and the same install/build/CTest/pytest/campaign sequence was repeated successfully.
