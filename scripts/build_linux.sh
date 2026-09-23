#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cmake -S "$ROOT/fortran" -B "$ROOT/build-release" -DCMAKE_BUILD_TYPE=Release
cmake --build "$ROOT/build-release" -j"${JOBS:-2}"
ctest --test-dir "$ROOT/build-release" --output-on-failure
export PYTHONPATH="$ROOT/python/src"
export DRMROTOR_LIB="$ROOT/build-release/libdrmrotor.so"
python3 -m pytest -q "$ROOT/python/tests"
