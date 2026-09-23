#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-$ROOT/validation/baseline/matlab_authority}"
mkdir -p "$OUT"
if command -v matlab >/dev/null 2>&1; then
  matlab -batch "addpath('$ROOT/validation/equivalence/matlab'); generate_authority_baseline('$ROOT','$OUT')"
elif command -v octave >/dev/null 2>&1; then
  octave --quiet --eval "addpath('$ROOT/validation/equivalence/matlab'); generate_authority_baseline('$ROOT','$OUT')"
else
  echo "BLOCKED: neither matlab nor octave is installed" >&2
  exit 2
fi
