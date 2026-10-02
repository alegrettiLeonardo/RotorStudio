"""One-time B3 axial/torsional authority freeze after Linux/Windows candidate PASS."""
from __future__ import annotations
import argparse,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from validation.b3.authority_common import *
from validation.ross_parity.verify_axial_torsional_candidate import compare,self_check,load

def freeze(linux:Path,windows:Path,cross_report:Path)->dict:
    linux=linux.resolve();windows=windows.resolve();target=(REPO_ROOT/FROZEN_PATH).resolve()
    require(linux.is_dir() and windows.is_dir(),"missing B3 platform candidate")
    al,_=load(linux);aw,_=load(windows)
    current=head(REPO_ROOT)
    require(al["generator_head"]==current and aw["generator_head"]==current,"candidate HEAD differs from freeze HEAD")
    require(al["ross_sha"]==aw["ross_sha"]==ROSS_SHA,"wrong ROSS SHA")
    lcheck=self_check(linux);wcheck=self_check(windows)
    cross=compare(linux,windows,cross_report);require(cross["status"]=="PASS","B3 cross-platform comparison failed")
    if target.exists():
        frozen,_=load(target)
        left=compare(target,linux,None);right=compare(target,windows,None)
        sums=read_json(target/"SHA256SUMS.json")
        expected={p.relative_to(target).as_posix():file_hash(p) for p in sorted(target.rglob("*"))
                  if p.is_file() and p.name!="SHA256SUMS.json"}
        require(sums["files"]==expected,"B3 frozen SHA256SUMS mismatch")
        return {"status":"PASS","mode":"REPRODUCTION","frozen_head":frozen["generator_head"],
                "candidate_head":al["generator_head"],"linux_vs_frozen":left["status"],
                "windows_vs_frozen":right["status"],"linux":lcheck,"windows":wcheck}
    shutil.copytree(linux,target)
    (target/".gitattributes").write_text("*.npy -text\n*.json text eol=lf\n*.txt -text\n",encoding="utf-8")
    evidence=target/"initial_reproduction";evidence.mkdir()
    if cross_report.is_file():shutil.copy2(cross_report,evidence/"cross-platform.json")
    shutil.copytree(windows,evidence/"windows_candidate")
    record={"schema_version":1,"freeze_utc":datetime.now(timezone.utc).isoformat(),
            "freeze_parent_head":current,"ross_sha":ROSS_SHA,"canonical_platform":"ubuntu-24.04",
            "linux_data_bundle_sha256":al["data_bundle_sha256"],"windows_data_bundle_sha256":aw["data_bundle_sha256"],
            "linux_self_check":lcheck,"windows_self_check":wcheck,"cross_platform":"PASS",
            "policy_sha256":al["policy_sha256"],"input_sha256":al["input_sha256"],
            "rotor_spec_sha256":al["rotor_spec_sha256"],"production_solver":"NOT_STARTED"}
    write_json(target/"FREEZE_RECORD.json",record)
    files={p.relative_to(target).as_posix():file_hash(p) for p in sorted(target.rglob("*"))
           if p.is_file() and p.name!="SHA256SUMS.json"}
    write_json(target/"SHA256SUMS.json",{"schema_version":1,"files":files})
    compare(target,linux,None);compare(target,windows,None)
    return {"status":"PASS","mode":"FIRST_FREEZE","frozen_head":current,"ross_sha":ROSS_SHA,
            "file_count":len(files),"linux":lcheck,"windows":wcheck}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--linux",type=Path,required=True)
    p.add_argument("--windows",type=Path,required=True)
    p.add_argument("--cross-report",type=Path,required=True)
    a=p.parse_args();print("B3_AUTHORITY_FREEZE",freeze(a.linux,a.windows,a.cross_report))
