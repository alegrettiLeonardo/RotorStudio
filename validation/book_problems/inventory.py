from __future__ import annotations
from pathlib import Path
import argparse,hashlib,json,re
SOLVER_FUNCTIONS=("bearasym","bearmtx","chr_asym","chr_root","chr_root_coax","crit_spd","freq_asym","freq_aux","freq_fdn","freq_rsp","freq_rsp_coax","rotorasym","rotormtx","runup","shftasym","shftelem","taper","time_fdn")
POST_FUNCTIONS=("whirl","picrotor","plotcamp","ploteig","plotfrf","plotloci","plotmode","plotorbit","plotresp","fftscale")
def build_inventory(problem_dir):
    root=Path(problem_dir);cases=[]
    for p in sorted(root.glob("Problem_*.m")):
        raw=p.read_bytes();text=raw.decode(errors="replace")
        solver=[f for f in SOLVER_FUNCTIONS if re.search(r"(?<![A-Za-z0-9_])"+re.escape(f)+r"\s*\(",text)]
        post=[f for f in POST_FUNCTIONS if re.search(r"(?<![A-Za-z0-9_])"+re.escape(f)+r"\s*\(",text)]
        cases.append({"case_id":p.stem.replace("Problem_",""),"file":p.name,"class":"A" if solver else "B","sha256":hashlib.sha256(raw).hexdigest(),"solver_calls":solver,"post_calls":post,"bytes":len(raw)})
    if len(cases)!=83:raise RuntimeError(f"expected 83 Problem_*.m files, found {len(cases)}")
    counts={"A":sum(c["class"]=="A" for c in cases),"B":sum(c["class"]=="B" for c in cases)}
    if counts!={"A":15,"B":68}:raise RuntimeError(f"unexpected A/B classification: {counts}")
    return {"schema_version":1,"case_count":83,"class_counts":counts,"classification_rule":"A iff original problem invokes a Rotor_Software_v2 numerical solver/matrix routine; plot/post-only calls do not count.","solver_functions":SOLVER_FUNCTIONS,"post_functions":POST_FUNCTIONS,"cases":cases}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--problem-dir",default="reference/drm_problem_scripts");ap.add_argument("--output",default="validation/reports/G14_INVENTORY.json");a=ap.parse_args()
    inv=build_inventory(a.problem_dir);Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(inv,indent=2));print(json.dumps({"case_count":83,"class_counts":inv["class_counts"]}))
if __name__=="__main__":main()
