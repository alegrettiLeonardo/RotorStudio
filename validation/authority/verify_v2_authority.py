from __future__ import annotations
import argparse, hashlib
from pathlib import Path

ARCHIVE_SHA256="bc42d18020013a537da6e7785a3d6b15533cd881939410c5e2a58c8563db5344"

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def parse_manifest(path: Path):
    rows=[]
    for raw in path.read_text().splitlines():
        line=raw.strip()
        if not line or line.startswith("#"):
            continue
        digest, rel=line.split(None,1)
        rows.append((digest,rel.strip()))
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=".")
    ap.add_argument("--manifest",default="validation/authority/V2_QUALIFICATION_SOURCE_SHA256.txt")
    a=ap.parse_args()
    root=Path(a.root).resolve()
    manifest=root/a.manifest
    rows=parse_manifest(manifest)
    failures=[]
    for expected,rel in rows:
        p=root/rel
        if not p.is_file():
            failures.append(f"MISSING {rel}")
            continue
        actual=sha256(p)
        if actual!=expected:
            failures.append(f"HASH_MISMATCH {rel} expected={expected} actual={actual}")
    if failures:
        print("\n".join(failures))
        raise SystemExit(1)
    print(f"V2_QUALIFICATION_SOURCE_INTEGRITY=PASS files={len(rows)}")
    print(f"ROTOR_SOFTWARE_V2_ARCHIVE_SHA256={ARCHIVE_SHA256}")

if __name__=="__main__":
    main()
