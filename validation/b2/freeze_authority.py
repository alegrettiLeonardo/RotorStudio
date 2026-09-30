"""One-time B2 authority freeze after same-head Linux/Windows candidate PASS."""
from __future__ import annotations
import argparse,json,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
from validation.b2.authority_common import *
from validation.ross_parity.verify_6dof_global_candidate import compare,self_check,load

def freeze(linux:Path,windows:Path,cross_report:Path)->dict:
    linux=linux.resolve();windows=windows.resolve();target=(REPO_ROOT/FROZEN_PATH).resolve()
    require(linux.is_dir() and windows.is_dir(),"missing platform candidate")
    al,_=load(linux);aw,_=load(windows)
    current=head(REPO_ROOT)
    require(al["generator_head"]==current and aw["generator_head"]==current,"candidate HEAD differs from freeze HEAD")
    require(al["ross_sha"]==aw["ross_sha"]==ROSS_SHA,"wrong ROSS SHA")
    lcheck=self_check(linux);wcheck=self_check(windows)
    cross=compare(linux,windows,cross_report)
    require(cross["status"]=="PASS","cross-platform comparison failed")
    if target.exists():
        frozen,_=load(target)
        require(frozen["generator_head"]==al["generator_head"],"frozen authority belongs to a different reviewed HEAD")
        verify_l=compare(target,linux,None);verify_w=compare(target,windows,None)
        sums=read_json(target/"SHA256SUMS.json")
        expected={p.relative_to(target).as_posix():file_hash(p) for p in sorted(target.rglob("*"))
                  if p.is_file() and p.name!="SHA256SUMS.json"}
        require(sums["files"]==expected,"frozen SHA256SUMS mismatch")
        return {"status":"PASS","mode":"REPRODUCTION","frozen_head":frozen["generator_head"],
                "ross_sha":ROSS_SHA,"linux":lcheck,"windows":wcheck,
                "linux_vs_frozen":verify_l["status"],"windows_vs_frozen":verify_w["status"]}
    # First freeze: Linux candidate is canonical after cross-platform numeric parity.
    shutil.copytree(linux,target)
    (target/".gitattributes").write_text("*.npy -text\n*.json text eol=lf\n*.txt -text\n",encoding="utf-8")
    evidence=target/"initial_reproduction";evidence.mkdir()
    if cross_report.is_file():shutil.copy2(cross_report,evidence/"cross-platform.json")
    for name in ("authority.json","source_provenance.json","source_ranges.json","requirements-freeze.txt","pip-check.txt"):
        src=windows/name
        if src.is_file():shutil.copy2(src,evidence/("windows-"+name))
    record={"schema_version":1,"freeze_utc":datetime.now(timezone.utc).isoformat(),
            "freeze_parent_head":current,"ross_sha":ROSS_SHA,
            "canonical_platform":"ubuntu-24.04",
            "linux_data_bundle_sha256":al["data_bundle_sha256"],
            "windows_data_bundle_sha256":aw["data_bundle_sha256"],
            "linux_self_check":lcheck,"windows_self_check":wcheck,
            "cross_platform":"PASS",
            "policy_sha256":al["policy_sha256"],"input_sha256":al["input_sha256"],
            "production_solver":"NOT_STARTED"}
    write_json(target/"FREEZE_RECORD.json",record)
    files={p.relative_to(target).as_posix():file_hash(p) for p in sorted(target.rglob("*"))
           if p.is_file() and p.name!="SHA256SUMS.json"}
    write_json(target/"SHA256SUMS.json",{"schema_version":1,"files":files})
    # Re-open and compare after materialization.
    compare(target,linux,None);compare(target,windows,None)
    return {"status":"PASS","mode":"FIRST_FREEZE","frozen_head":current,"ross_sha":ROSS_SHA,
            "file_count":len(files),"linux":lcheck,"windows":wcheck}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--linux",type=Path,required=True);p.add_argument("--windows",type=Path,required=True);p.add_argument("--cross-report",type=Path,required=True)
    a=p.parse_args();print("B2_AUTHORITY_FREEZE",json.dumps(freeze(a.linux,a.windows,a.cross_report),sort_keys=True))
