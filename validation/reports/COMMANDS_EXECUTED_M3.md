# Commands executed — M3

Representative commands actually executed in the qualification environment:

```bash
cmake -S fortran -B build-release-m3 -DCMAKE_BUILD_TYPE=Release
cmake --build build-release-m3 -j2
ctest --test-dir build-release-m3 --output-on-failure

cmake -S fortran -B build-debug-m3 -DCMAKE_BUILD_TYPE=Debug
cmake --build build-debug-m3 -j2
ctest --test-dir build-debug-m3 --output-on-failure

export PYTHONPATH="$PWD/python/src"
export DRMROTOR_LIB="$PWD/build-release-m3/libdrmrotor.so"
python3 -m pytest -q python/tests
python3 -m pytest --collect-only -q python/tests

python3 examples/chapter05/example_05_08_01.py
python3 examples/chapter06/example_06_06_01.py --case 1 --smoke
python3 examples/chapter07/example_07_06_01.py --case 1 --phase 0 --smoke
```

MATLAB/Octave availability was checked with `command -v`; neither executable was present.
