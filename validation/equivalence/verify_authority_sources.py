from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default="validation/equivalence/authority_source_manifest.json",
    )
    parser.add_argument(
        "--source-dir",
        default="reference/matlab_v2",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    source_dir = Path(args.source_dir)
    manifest = json.loads(manifest_path.read_text())

    expected = manifest["required_numeric_sources"]
    rows = []
    ok = True

    for name, wanted in sorted(expected.items()):
        path = source_dir / name
        if not path.is_file():
            rows.append(
                {
                    "file": name,
                    "status": "MISSING",
                    "expected_sha256_lf": wanted,
                }
            )
            ok = False
            continue

        got = hashlib.sha256(canonical_bytes(path)).hexdigest()
        passed = got == wanted
        rows.append(
            {
                "file": name,
                "status": "PASS" if passed else "FAIL",
                "expected_sha256_lf": wanted,
                "actual_sha256_lf": got,
            }
        )
        ok &= passed

    result = {
        "authority": manifest["authority"],
        "original_zip_sha256": manifest["original_zip_sha256"],
        "normalization": manifest["normalization"],
        "source_dir": str(source_dir),
        "required_source_count": len(expected),
        "overall": "PASS" if ok else "FAIL",
        "files": rows,
    }

    print(json.dumps(result, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
