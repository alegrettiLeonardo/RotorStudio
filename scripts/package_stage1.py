from __future__ import annotations
import argparse,hashlib,json,os,zipfile
from pathlib import Path

ROOTS=["README.md",".github","docs","fortran","python","examples","validation","scripts","reference"]
EXCLUDE_DIRS={".git",".venv","__pycache__",".pytest_cache","build","build-release","build-debug","build-stage1","build-g14","dist"}
EXCLUDE_SUFFIXES={".pyc",".pyo",".o",".obj",".mod",".so",".dll",".dylib"}
EXCLUDE_PREFIXES=("validation/reports/g14/","validation/reports/example_campaign_","validation/reports/legacy_probes/")

def included(path:Path,root:Path)->bool:
    rel=path.relative_to(root).as_posix()
    if any(part in EXCLUDE_DIRS for part in path.relative_to(root).parts): return False
    if path.suffix.lower() in EXCLUDE_SUFFIXES: return False
    if any(rel.startswith(p) for p in EXCLUDE_PREFIXES): return False
    if rel.endswith(".zip") and rel.startswith("validation/reports/"): return False
    return True

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=".");ap.add_argument("--output",required=True);ap.add_argument("--manifest",required=True);args=ap.parse_args()
    root=Path(args.root).resolve();out=Path(args.output).resolve();manifest_path=Path(args.manifest).resolve()
    files=[]
    for item in ROOTS:
        p=root/item
        if not p.exists(): continue
        if p.is_file(): files.append(p)
        else: files.extend(x for x in p.rglob("*") if x.is_file() and included(x,root))
    files=sorted(set(files),key=lambda x:x.relative_to(root).as_posix())
    out.parent.mkdir(parents=True,exist_ok=True)
    records=[]
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:
            rel=p.relative_to(root).as_posix();data=p.read_bytes()
            zi=zipfile.ZipInfo(rel,date_time=(2026,1,1,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;zi.external_attr=0o100644<<16
            z.writestr(zi,data)
            records.append({"path":rel,"sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)})
    zsha=hashlib.sha256(out.read_bytes()).hexdigest()
    manifest={"schema_version":1,"package":out.name,"sha256":zsha,"file_count":len(records),"files":records}
    manifest_path.parent.mkdir(parents=True,exist_ok=True);manifest_path.write_text(json.dumps(manifest,indent=2)+"\n")
    out.with_suffix(out.suffix+".sha256").write_text(f"{zsha}  {out.name}\n")
    print(json.dumps({"package":str(out),"sha256":zsha,"file_count":len(records)}))
    return 0
if __name__=="__main__": raise SystemExit(main())
