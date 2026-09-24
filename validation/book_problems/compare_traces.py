from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import numpy as np
from scipy.io import loadmat

from drm_core.domain.model import RotorModel
from drm_core.analysis.modal import run_modal
from drm_core.analysis.frequency_response import run_frequency_response
from drm_core.analysis.critical_speed import run_critical_speeds
from drm_core.analysis.asymmetric import run_asymmetric_modal
from drm_core.post.whirl import whirl
from validation.equivalence.comparators import eigenvalue_max_rel, complex_response_rel

POLICY = {
    'eigenvalues_rel': 1e-8,
    'critical_speeds_rel': 1e-6,
    'complex_response_rel': 1e-8,
    'whirl_abs': 1e-10,
}

def arr(x):
    if x is None: return np.empty((0,0))
    a=np.asarray(x)
    if a.size==0: return np.empty((0,0))
    if a.ndim==0: return a.reshape(1,1)
    if a.ndim==1: return a.reshape(1,-1)
    return a

def struct_field(s,name,default=None):
    if isinstance(s,dict): return s.get(name,default)
    return getattr(s,name,default)

def model_from_mat(s) -> RotorModel:
    node=arr(struct_field(s,'node',[]))
    shaft=arr(struct_field(s,'shaft',[]))
    disc=arr(struct_field(s,'disc',[]))
    bearing=arr(struct_field(s,'bearing',[]))
    force=arr(struct_field(s,'force',[]))
    bend=arr(struct_field(s,'bend',[]))
    rotors=arr(struct_field(s,'rotors',[]))
    def rows(a): return [] if a.size==0 else a.tolist()
    return RotorModel.from_legacy_arrays(rows(node),rows(shaft),rows(disc),rows(bearing),rows(force),rows(bend),rows(rotors))

def cell_outputs(m):
    tmp=m['tmp']
    if isinstance(tmp,list): return tmp
    if isinstance(tmp,np.ndarray) and tmp.dtype==object: return list(tmp.ravel())
    return [tmp]

def scalar(x,default=None):
    a=np.asarray(x)
    if a.size==0: return default
    return float(a.ravel()[0])

def rel_vec(a,b):
    a=np.asarray(a).ravel(); b=np.asarray(b).ravel()
    if a.size!=b.size: return float('inf')
    den=np.maximum(1.0,np.abs(a))
    return float(np.max(np.abs(a-b)/den)) if a.size else 0.0

def compare_trace(path:Path):
    kind=path.stem.split('__')[-1]
    m=loadmat(path,simplify_cells=True)
    outs=cell_outputs(m)
    if kind=='whirl':
        k,amp=whirl(np.asarray(m['u']),np.asarray(m['v']))
        e=float(np.max(np.abs(np.asarray(outs[0])-k)))
        if len(outs)>1: e=max(e,float(np.max(np.abs(np.asarray(outs[1])-amp))))
        return kind,e,POLICY['whirl_abs']
    model=model_from_mat(m['model'])
    if kind=='chr_root':
        sp=np.asarray(m['Rotor_Spd'],dtype=float).ravel()
        vals=[run_modal(model,float(w)).eigenvalues for w in sp]
        got=np.column_stack(vals); ref=np.asarray(outs[0])
        if ref.ndim==1: ref=ref[:,None]
        return kind,eigenvalue_max_rel(ref,got),POLICY['eigenvalues_rel']
    if kind=='chr_asym':
        sp=np.asarray(m['Rotor_Spd'],dtype=float).ravel()
        vals=[run_asymmetric_modal(model,float(w),with_eigenvectors=False).eigenvalues for w in sp]
        got=np.column_stack(vals); ref=np.asarray(outs[0])
        if ref.ndim==1: ref=ref[:,None]
        return kind,eigenvalue_max_rel(ref,got),POLICY['eigenvalues_rel']
    if kind=='freq_rsp':
        sp=np.asarray(m['Rotor_Spd'],dtype=float).ravel()
        got=run_frequency_response(model,sp).response
        return kind,complex_response_rel(got,np.asarray(outs[0])),POLICY['complex_response_rel']
    if kind=='crit_spd':
        narg=int(round(scalar(m.get('nargin_requested'),1)))
        kw={}
        if narg>=2: kw['NX']=scalar(m.get('NX'),1.0)
        if narg>=3: kw['damped']=scalar(m.get('damped_NF'),1.0)>=0.5
        if narg>=4: kw['ncrit']=int(round(scalar(m.get('number_criticals'),5)))
        if narg>=5: kw['max_iterations']=int(round(scalar(m.get('max_iterations'),20)))
        if narg>=6: kw['tol']=scalar(m.get('convergence_tol'),1e-6)
        if narg>=7:
            initial=np.asarray(m.get('initial_estimates'),dtype=float).ravel()
            kw['initial_estimates']=initial; kw['method']=3
        got=run_critical_speeds(model,**kw).critical_speeds_rad_s
        ref=np.asarray(outs[0],dtype=float).ravel()
        return kind,rel_vec(ref,got),POLICY['critical_speeds_rel']
    raise RuntimeError(kind)

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--trace-dir',required=True); ap.add_argument('--status-csv',required=True)
    ap.add_argument('--inventory',required=True); ap.add_argument('--output',required=True)
    args=ap.parse_args(); inv=json.loads(Path(args.inventory).read_text())
    status={}
    with open(args.status_csv,newline='') as f:
        for row in csv.DictReader(f): status[row['problem']]=row
    rows=[]; ok=True
    for p in inv['problems']:
        st=status.get(p['problem'],{'status':'MISSING','message':'not executed'})
        if st['status']!='PASS': ok=False
        traces=sorted(Path(args.trace_dir).glob(f"{p['problem']}__*.mat"))
        if p['class']=='A_SOLVER' and not traces: ok=False
        max_ratio=0.0; comparisons=[]
        for t in traces:
            kind,err,limit=compare_trace(t); passed=err<=limit; ok &= passed
            max_ratio=max(max_ratio,err/limit if limit else 0.0)
            comparisons.append({'trace':t.name,'kind':kind,'error':err,'limit':limit,'status':'PASS' if passed else 'FAIL'})
        rows.append({'problem':p['problem'],'class':p['class'],'octave_status':st['status'],'octave_message':st.get('message',''),'trace_count':len(traces),'max_gate_ratio':max_ratio,'comparisons':comparisons})
    result={'gate':'G14','overall':'PASS' if ok else 'FAIL','problem_count':len(rows),'A_solver':sum(r['class']=='A_SOLVER' for r in rows),'B_analytical':sum(r['class']=='B_ANALYTICAL' for r in rows),'octave_pass':sum(r['octave_status']=='PASS' for r in rows),'rows':rows,'policy':POLICY}
    Path(args.output).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
    return 0 if ok else 1

if __name__=='__main__': raise SystemExit(main())
