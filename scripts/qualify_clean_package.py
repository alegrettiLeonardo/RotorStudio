from __future__ import annotations
from pathlib import Path
import argparse,json,os,subprocess,sys,tempfile,zipfile,shutil

def run(cmd,cwd,env=None):
 p=subprocess.run(cmd,cwd=cwd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print("$"," ".join(map(str,cmd)));print(p.stdout)
 if p.returncode:raise RuntimeError(f"command failed ({p.returncode}): {' '.join(map(str,cmd))}")
 return {"cmd":[str(x) for x in cmd],"returncode":p.returncode,"tail":"\n".join(p.stdout.splitlines()[-30:])}

def main():
 ap=argparse.ArgumentParser();ap.add_argument("zip");ap.add_argument("--report",default="validation/reports/CLEAN_PACKAGE_QUALIFICATION.json");a=ap.parse_args()
 zp=Path(a.zip).resolve();report=Path(a.report).resolve();steps=[]
 with tempfile.TemporaryDirectory(prefix="stage1-clean-") as td:
  ext=Path(td)/"extract";ext.mkdir()
  with zipfile.ZipFile(zp) as z:z.extractall(ext)
  roots=[p for p in ext.iterdir() if p.is_dir()]
  if len(roots)!=1:raise RuntimeError(f"expected one package root, got {roots}")
  root=roots[0];build=Path(td)/"build-release"
  steps.append(run(["cmake","-S",str(root/"fortran"),"-B",str(build),"-DCMAKE_BUILD_TYPE=Release"],root))
  steps.append(run(["cmake","--build",str(build),"-j2"],root));steps.append(run(["ctest","--test-dir",str(build),"--output-on-failure"],root))
  venv=Path(td)/"venv";steps.append(run([sys.executable,"-m","venv",str(venv)],root))
  py=venv/("Scripts/python.exe" if os.name=="nt" else "bin/python")
  steps.append(run([str(py),"-m","pip","install","--upgrade","pip"],root));steps.append(run([str(py),"-m","pip","install","-e",str(root/"python")+"[test]"],root))
  env=os.environ.copy();env["PYTHONPATH"]=str(root/"python"/"src")+os.pathsep+str(root)
  libs=list(build.rglob("libdrmrotor.so"))+list(build.rglob("drmrotor.dll"))+list(build.rglob("libdrmrotor.dylib"))
  if not libs:raise RuntimeError("built drmrotor shared library not found")
  env["DRMROTOR_LIB"]=str(libs[0])
  steps.append(run([str(py),"-m","pytest",str(root/"python"/"tests"),"-q"],root,env))
  steps.append(run([str(py),str(root/"scripts"/"run_example_campaign.py"),"--outdir",str(Path(td)/"example_campaign")],root,env))
  steps.append(run([str(py),str(root/"validation"/"book_problems"/"inventory.py"),"--problem-dir",str(root/"reference"/"drm_problem_scripts"),"--output",str(Path(td)/"G14_INVENTORY.json")],root,env))
  if (root/".git").exists():raise RuntimeError("clean package contains .git")
  forbidden=[] 
  for p in root.rglob("*"):
   if p.name in {".venv","__pycache__",".pytest_cache"} or p.suffix.lower() in {".o",".mod",".so",".dll",".dylib"}:forbidden.append(str(p.relative_to(root)))
  if forbidden:raise RuntimeError(f"forbidden package artifacts: {forbidden[:20]}")
 payload={"gate":"G18","status":"PASS","zip":zp.name,"steps":steps,"isolated_root":str(root),"source_tree_dependency":False}
 report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(payload,indent=2));print(json.dumps({"gate":"G18","status":"PASS","steps":len(steps)},indent=2))
if __name__=="__main__":main()
