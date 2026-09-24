from __future__ import annotations
import argparse,csv,json,math,sys
from pathlib import Path
import numpy as np
from scipy.io import loadmat
sys.path.insert(0,str(Path(__file__).resolve().parent))
from inventory import build_inventory
from drm_core import RotorModel,run_modal,run_frequency_response,run_asymmetric_modal
CONFIG={
'05_01':('modal','example','Rotor_Spd','eigenvalues'),'05_02':('modal','example','Rotor_Spd','eigenvalues'),
'05_03':('modal','example','Rotor_Spd','eigenvalues'),'05_08':('modal','example','Rotor_Spd','eigenvalues'),
'05_09':('modal','example','Rotor_Spd','eigenvalues'),'05_11':('modal','model','Rotor_Spd','eigenvalues'),
'06_10':('response','example','speed_vector','response'),'06_11':('modal','example','Rotor_Spd','eigenvalues'),
'06_11e':('modal','example','Rotor_Spd','eigenvalues'),'06_12':('response','example','speed_vector','response'),
'07_10':('modal','example','Rotor_Spd','eigenvalues'),'07_11':('asym_modal','example','Rotor_Spd','eigenvalues'),
'08_11':('response','model','Rotor_Spd','response03'),'08_12':('response','example','Rotor_Spd','response03'),
'08_14':('response','model','Rotor_Spd','response03')}
def rows(a):
    x=np.asarray(a)
    if x.size==0:return []
    if x.ndim==0:return [[float(x)]]
    if x.ndim==1:return [x.tolist()]
    return x.tolist()
def get(s,n):return s[n] if n in s and s[n] is not None else []
def model_from_struct(s):
    node=np.asarray(get(s,'node'))
    if node.ndim==1:node=node.reshape(-1,1)
    if node.shape[1]==1:node=np.column_stack([np.arange(1,len(node)+1),node[:,0]])
    return RotorModel.from_legacy_arrays(rows(node),rows(get(s,'shaft')),rows(get(s,'disc')),rows(get(s,'bearing')),rows(get(s,'force')),rows(get(s,'bend')),rows(get(s,'rotors')))
def sample(n):
    if n<=7:return list(range(n))
    return sorted(set([0,n//8,n//4,n//2,3*n//4,7*n//8,n-1]))
def rel(a,b):
    a=np.asarray(a);b=np.asarray(b)
    if a.shape!=b.shape:return math.inf
    return float(np.max(np.abs(a-b))/max(float(np.max(np.abs(a))) if a.size else 0,1))
def matrix(x):
    a=np.asarray(x);return (a[:,None] if a.ndim==1 else a).astype(complex)
def compare(cid,mat,tol):
    ws=loadmat(mat,simplify_cells=True);kind,mname,sname,rname=CONFIG[cid];m=model_from_struct(ws[mname]);speeds=np.asarray(ws[sname],float).reshape(-1);ref=matrix(ws[rname]);idx=sample(len(speeds))
    if kind=='modal':got=np.column_stack([run_modal(m,float(speeds[j])).eigenvalues for j in idx]);exp=ref[:,idx] if ref.shape[1]>1 else ref
    elif kind=='asym_modal':got=np.column_stack([run_asymmetric_modal(m,float(speeds[j])).eigenvalues for j in idx]);exp=ref[:,idx] if ref.shape[1]>1 else ref
    else:got=run_frequency_response(m,speeds[idx]).response;exp=ref[:,idx]
    e=rel(exp,got)
    if not np.isfinite(e) or e>tol:raise AssertionError(f"{cid}: {kind} relative error {e:.3e} > {tol:.3e}; {exp.shape}/{got.shape}")
    return {"case_id":cid,"kind":kind,"sample_count":len(idx),"relative_error":e,"status":"PASS"}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--problem-dir',default='reference/drm_problem_scripts');ap.add_argument('--octave-report',default='validation/reports/book_problems/octave_runtime.csv');ap.add_argument('--workspace-dir',default='validation/reports/book_problems/workspaces');ap.add_argument('--output',default='validation/reports/G14_BOOK_PROBLEM_REGRESSION.json');ap.add_argument('--inventory-output',default='validation/reports/G14_INVENTORY.json');ap.add_argument('--tol',type=float,default=1e-7);a=ap.parse_args()
    inv=build_inventory(a.problem_dir);Path(a.inventory_output).parent.mkdir(parents=True,exist_ok=True);Path(a.inventory_output).write_text(json.dumps(inv,indent=2))
    with Path(a.octave_report).open(newline='') as f:runtime={r['problem']:r for r in csv.DictReader(f)}
    missing=[c['file'] for c in inv['cases'] if c['file'] not in runtime];failed=[n for n,r in runtime.items() if r['status']!='PASS']
    if missing or failed:raise SystemExit(f"G14 FAIL: missing={missing} octave_failed={failed}")
    details=[compare(c['case_id'],Path(a.workspace_dir)/f"Problem_{c['case_id']}.mat",a.tol) for c in inv['cases'] if c['class']=='A']
    out={"schema_version":1,"gate":"G14","status":"PASS","authority":"GNU Octave 7.1.0 + original DRM problem scripts","case_count":83,"class_counts":inv['class_counts'],"octave_runtime_pass":len(runtime),"class_a_numeric_pass":len(details),"tolerance":a.tol,"solver_duplication":False,"details":details}
    Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
