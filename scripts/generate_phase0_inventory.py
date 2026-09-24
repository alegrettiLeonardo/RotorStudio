from __future__ import annotations
from pathlib import Path
import hashlib,json,re

ATTACHMENTS={
"Rotor_Software_v2.zip":{"bytes":50461,"sha256":"bc42d18020013a537da6e7785a3d6b15533cd881939410c5e2a58c8563db5344"},
"Rotor_Examples_v1.zip":{"bytes":37269,"sha256":"8fe42cb5291b0fe54eac97cf67bad89f8a68d9252056383d567380c865c230fb"},
"DRM_problem_scripts.zip":{"bytes":73105,"sha256":"8b5db23fa57bc5e41f68ed9e25ab8f1f1a72e4a24b9e11af38dccdd4098501d1"},
"Rotor_Software_Manual_v1.pdf":{"bytes":167110,"sha256":"acaa80024bc493b10b81079ad667b7c7b181d13b56abbf3cb4ea6f24935aac49"},
"FRISWELL - Dynamics of Rotating Machines.pdf":{"bytes":50974531,"sha256":"d01c695b139f98feee8e190de34c16eb9e611a86889df59d8434c4e8d42845d9"},
"ChatGPT Image 23 de set. de 2026, 13_12_32 (2).png":{"bytes":1704753,"sha256":"7d9d57b5b9e03588a136b6d08b0ff751bcc1bc10d210313f19e2b34d6f5ec1c2"},
"ChatGPT Image 23 de set. de 2026, 13_12_33 (3).png":{"bytes":1628587,"sha256":"0dea484009ff912a40dd9c1e12bb2f2c1bc7fc390647d83c7c52efa861c80990"},
"ChatGPT Image 23 de set. de 2026, 13_12_31 (1).png":{"bytes":1356952,"sha256":"342eb4bee8564c344bb8ebd82b73f6ecd1f6049495e9a710ca4da8aa2fa269de"},
"Markdown(1).md colado":{"bytes":22829,"sha256":"bfbddc9ee6bd59c9a2b5b4f0789b41ae7fc56dd660ac9524ed0ac1e25c5a35c0"},
}
ORIGINAL_V2=["bearasym","bearmtx","chr_asym","chr_root","chr_root_coax","crit_spd","fftscale","freq_asym","freq_aux","freq_fdn","freq_rsp","freq_rsp_coax","picrotor","plotcamp","ploteig","plotfrf","plotloci","plotmode","plotorbit","plotresp","rotorasym","rotormtx","runup","shftasym","shftelem","taper","time_fdn","whirl"]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 root=Path(__file__).resolve().parents[1]
 matlab=sorted((root/"reference"/"matlab_v2").glob("*.m"))
 numeric_names={p.stem for p in matlab}
 graph={}
 for p in matlab:
  txt=p.read_text(errors="replace")
  graph[p.stem]=sorted(n for n in numeric_names if n!=p.stem and re.search(r"(?<![A-Za-z0-9_])"+re.escape(n)+r"\s*\(",txt))
 problems=sorted((root/"reference"/"drm_problem_scripts").glob("Problem_*.m"))
 examples=sorted((root/"examples").glob("chapter*/example_*.py"))
 fortran=sorted((root/"fortran"/"src").glob("*.f90"))
 py=sorted((root/"python"/"src"/"drm_core").rglob("*.py"))
 report={"schema_version":1,"attachments":ATTACHMENTS,
   "matlab":{"original_v2_function_count":28,"original_v2_functions":ORIGINAL_V2,
             "frozen_numeric_source_count":len(matlab),"frozen_sources":[{"file":p.name,"sha256":sha(p)} for p in matlab],"call_graph":graph},
   "problems":{"count":len(problems),"files":[{"file":p.name,"sha256":sha(p)} for p in problems]},
   "examples":{"translated_count":len(examples),"files":[str(p.relative_to(root)) for p in examples]},
   "fortran":{"source_count":len(fortran),"files":[str(p.relative_to(root)) for p in fortran]},
   "python":{"module_count":len(py),"files":[str(p.relative_to(root)) for p in py]}}
 out=root/"validation"/"reports"/"PHASE0_INVENTORY.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,sort_keys=True))
 print(json.dumps({"matlab_original":28,"matlab_frozen":len(matlab),"problems":len(problems),"examples":len(examples),"fortran_sources":len(fortran),"python_modules":len(py)},indent=2))
 if len(problems)!=83:raise SystemExit("Phase 0 inventory requires exactly 83 materialized book problems")
 if len(examples)!=22:raise SystemExit("Phase 0 inventory requires exactly 22 translated example files")
if __name__=="__main__":main()
