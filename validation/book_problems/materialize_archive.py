from __future__ import annotations
from pathlib import Path
import argparse, base64, hashlib, io, json, zipfile

EXPECTED_SHA256 = "8b5db23fa57bc5e41f68ed9e25ab8f1f1a72e4a24b9e11af38dccdd4098501d1"
EXPECTED_PROBLEMS = 83

def archive_bytes(repo_root: Path) -> bytes:
    parts = sorted((repo_root / "reference" / "problems" / "archive_b64").glob("DRM_problem_scripts.zip.b64.part*"))
    if not parts:
        raise RuntimeError("DRM problem archive fragments are missing")
    raw = base64.b64decode("".join(p.read_text().strip() for p in parts), validate=True)
    got = hashlib.sha256(raw).hexdigest()
    if got != EXPECTED_SHA256:
        raise RuntimeError(f"DRM_problem_scripts.zip SHA256 mismatch: received {got}, expected {EXPECTED_SHA256}")
    return raw

def materialize(repo_root: Path, target: Path, write_zip: Path | None = None) -> dict:
    raw = archive_bytes(repo_root)
    if write_zip is not None:
        write_zip.parent.mkdir(parents=True, exist_ok=True)
        write_zip.write_bytes(raw)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        members = [n for n in zf.namelist() if n.startswith("rb_prob_solns/") and not n.endswith("/")]
        for name in members:
            base = Path(name).name
            if not base or base in {".", ".."}:
                continue
            (target / base).write_bytes(zf.read(name))
    cases = sorted(target.glob("Problem_*.m"))
    if len(cases) != EXPECTED_PROBLEMS:
        raise RuntimeError(f"expected {EXPECTED_PROBLEMS} Problem_*.m files, found {len(cases)}")
    bnpr = target / "bnpr.m"
    if not bnpr.is_file():
        raise RuntimeError("bnpr.m was not materialized")
    return {
        "archive_sha256": EXPECTED_SHA256,
        "fragment_count": len(sorted((repo_root / "reference" / "problems" / "archive_b64").glob("DRM_problem_scripts.zip.b64.part*"))),
        "problem_count": len(cases),
        "helper_count": 1,
        "target": str(target),
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--target", default="reference/drm_problem_scripts")
    ap.add_argument("--write-zip")
    ap.add_argument("--report", default="validation/reports/DRM_PROBLEM_ARCHIVE.json")
    a = ap.parse_args()
    root = Path(a.repo_root).resolve()
    target = (root / a.target).resolve()
    write_zip = (root / a.write_zip).resolve() if a.write_zip else None
    report = materialize(root, target, write_zip)
    rp = root / a.report
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
