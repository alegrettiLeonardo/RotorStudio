#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$here/RotorStudio_Stage1_M2_source.tar.gz"
cat "$here"/RotorStudio_Stage1_M2_source.tar.gz.part* > "$out"
(
  cd "$here"
  sha256sum -c RotorStudio_Stage1_M2_source.tar.gz.sha256
)
echo "Reconstructed: $out"
