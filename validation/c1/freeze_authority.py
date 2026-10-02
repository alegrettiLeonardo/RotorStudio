"""Freeze a reviewed C1 authority candidate before production implementation."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"

def sha256(path:Path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidate",required=True)
    ap.add_argument("--cross-platform",required=True)
    ap.add_argument("--out",default="validation/ross_parity/misalignment")
    args=ap.parse_args()
    src=Path(args.candidate);dst=ROOT/args.out
    if dst.exists():
        raise SystemExit(f"refusing to overwrite existing freeze: {dst}")
    cross=json.loads(Path(args.cross_platform).read_text())
    if cross.get("status")!="PASS":
        raise SystemExit("cross-platform authority is not PASS")
    production=[
        ROOT/"fortran/src/rd_fault_misalignment.f90",
        ROOT/"fortran/src/rd_fault_misalignment_c_api.f90",
        ROOT/"python/src/drm_core/solver/misalignment.py",
    ]
    if any(p.exists() for p in production):
        raise SystemExit("production C1 solver already exists; authority must freeze first")
    shutil.copytree(src,dst)
    parent=os.environ.get("GITHUB_SHA","UNKNOWN")
    record={
        "schema":1,
        "ross_sha":ROSS_SHA,
        "freeze_parent_head":parent,
        "production_solver":"NOT_STARTED",
        "cross_platform_status":"PASS",
        "array_count":sum(1 for _ in dst.rglob("*.npy")),
        "source_provenance":json.loads((dst/"source_provenance.json").read_text()),
    }
    (dst/"FREEZE_RECORD.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    hashes={}
    for p in sorted(dst.rglob("*")):
        if p.is_file() and p.name!="SHA256SUMS.json":
            hashes[str(p.relative_to(dst)).replace("\\","/")]=sha256(p)
    (dst/"SHA256SUMS.json").write_text(json.dumps(hashes,indent=2,sort_keys=True)+"\n")
    print("C1_AUTHORITY_FROZEN",json.dumps(record,sort_keys=True))

if __name__=="__main__":
    main()
