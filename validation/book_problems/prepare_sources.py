from __future__ import annotations
import argparse,hashlib,json,re,shutil,zipfile
from pathlib import Path
EXPECTED_ZIP='8b5db23fa57bc5e41f68ed9e25ab8f1f1a72e4a24b9e11af38dccdd4098501d1'
SOLVER_CALLS=['shftelem','taper','shftasym','rotormtx','rotorasym','bearmtx','bearasym','chr_root','chr_asym','chr_root_coax','crit_spd','freq_rsp','freq_aux','freq_fdn','freq_rsp_coax','freq_asym','time_fdn','runup','whirl']

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--zip',required=True);ap.add_argument('--outdir',required=True);ap.add_argument('--inventory',required=True);a=ap.parse_args()
 zp=Path(a.zip); raw=zp.read_bytes(); got=hashlib.sha256(raw).hexdigest()
 if got!=EXPECTED_ZIP: raise SystemExit(f'problem archive SHA256 mismatch: {got}')
 out=Path(a.outdir);shutil.rmtree(out,ignore_errors=True);out.mkdir(parents=True)
 with zipfile.ZipFile(zp) as z:
  for n in z.namelist():
   if n.endswith('/') or '/._' in n or '__MACOSX' in n: continue
   if not n.startswith('rb_prob_solns/'): continue
   (out/Path(n).name).write_bytes(z.read(n))
 probs=[]
 for p in sorted(out.glob('Problem_*.m')):
  txt=p.read_text(errors='replace');calls=[k for k in SOLVER_CALLS if re.search(r'\b'+re.escape(k)+r'\s*\(',txt,re.I)]
  probs.append({'problem':p.stem,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'class':'A_SOLVER' if calls else 'B_ANALYTICAL','solver_calls':calls})
 inv={'schema_version':1,'authority':'DRM_problem_scripts.zip','archive_sha256':got,'problem_count':len(probs),'classification':{'A_SOLVER':sum(x['class']=='A_SOLVER' for x in probs),'B_ANALYTICAL':sum(x['class']=='B_ANALYTICAL' for x in probs)},'helper_files':{'bnpr.m':hashlib.sha256((out/'bnpr.m').read_bytes()).hexdigest()},'problems':probs}
 Path(a.inventory).parent.mkdir(parents=True,exist_ok=True);Path(a.inventory).write_text(json.dumps(inv,indent=2)+'\n')
 if len(probs)!=83 or inv['classification']!={'A_SOLVER':19,'B_ANALYTICAL':64}: raise SystemExit(f'unexpected problem inventory {inv["classification"]} count={len(probs)}')
 print(json.dumps({'archive_sha256':got,'problem_count':len(probs),**inv['classification']}))
if __name__=='__main__':main()
