from __future__ import annotations
from pathlib import Path
import argparse,hashlib,json,os,shutil,tempfile,zipfile,importlib.util

TOP=("fortran","python","examples","validation","reference","scripts","docs")
EXCLUDE_NAMES={".git",".venv","__pycache__",".pytest_cache","dist"}
EXCLUDE_SUFFIX={".o",".mod",".so",".dll",".dylib",".pyc"}

def excluded(p:Path)->bool:
 return any(x in EXCLUDE_NAMES for x in p.parts) or p.suffix.lower() in EXCLUDE_SUFFIX or any(x.startswith("build-") for x in p.parts)

def copy_tree(src:Path,dst:Path):
 for p in src.rglob("*"):
  rel=p.relative_to(src)
  if excluded(rel):continue
  q=dst/rel
  if p.is_dir():q.mkdir(parents=True,exist_ok=True)
  elif p.is_file():q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)

def file_sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def load_materializer(root):
 spec=importlib.util.spec_from_file_location("g14_materializer",root/"validation"/"book_problems"/"materialize_archive.py")
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def deterministic_zip(root:Path,out:Path):
 with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in sorted(root.rglob("*")):
   if not p.is_file():continue
   info=zipfile.ZipInfo(str(p.relative_to(root.parent)).replace(os.sep,"/"),date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
   z.writestr(info,p.read_bytes())

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--id");ap.add_argument("--output-dir",default="dist");a=ap.parse_args()
 repo=Path(__file__).resolve().parents[1];ident=a.id or os.environ.get("GITHUB_SHA","stage1")[:12]
 name=f"DRM_Fortran_Python_Stage1_{ident}";outdir=repo/a.output_dir;outdir.mkdir(parents=True,exist_ok=True);zip_path=outdir/(name+".zip")
 with tempfile.TemporaryDirectory(prefix="stage1-pack-") as td:
  stage=Path(td)/name;stage.mkdir()
  for top in TOP:
   src=repo/top
   if src.exists():copy_tree(src,stage/top)
  for f in ("README.md",".gitignore",".gitattributes"):
   if (repo/f).is_file():shutil.copy2(repo/f,stage/f)
  mat=load_materializer(repo)
  mat.materialize(repo,stage/"reference"/"drm_problem_scripts",stage/"reference"/"problems"/"DRM_problem_scripts.zip")
  frag=stage/"reference"/"problems"/"archive_b64"
  if frag.exists():shutil.rmtree(frag)
  entries=[]
  for p in sorted(stage.rglob("*")):
   if p.is_file():entries.append((file_sha(p),str(p.relative_to(stage)).replace(os.sep,"/")))
  (stage/"MANIFEST_SHA256.txt").write_text("".join(f"{h}  {n}\n" for h,n in entries))
  meta={"schema_version":1,"package":name,"source_commit":os.environ.get("GITHUB_SHA"),"file_count":len(entries)+2,"problem_archive_sha256":mat.EXPECTED_SHA256}
  (stage/"PACKAGE_METADATA.json").write_text(json.dumps(meta,indent=2,sort_keys=True))
  deterministic_zip(stage,zip_path)
 result={"zip":str(zip_path),"sha256":file_sha(zip_path),"bytes":zip_path.stat().st_size,"package":name}
 (outdir/(name+".sha256")).write_text(f"{result['sha256']}  {zip_path.name}\n")
 print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":main()
