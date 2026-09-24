from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import numpy as np
from scipy.io import loadmat

from drm_core.domain.model import RotorModel
from drm_core.solver.facade import SolverFacade
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

def modal_grid(facade:SolverFacade,model:RotorModel,speeds)->np.ndarray:
    sp=np.asarray(speeds,dtype=float).ravel()
    return np.column_stack([facade.modal(model,float(w)) for w in sp])

def asym_modal_grid(facade:SolverFacade,model:RotorModel,speeds,want_vectors:bool)->np.ndarray:
    sp=np.asarray(speeds,dtype=float).ravel()
    vals=[]
    for w in sp:
        eig,_=facade.asymmetric_modal(model,float(w),want_vectors)
        vals.append(eig)
    return np.column_stack(vals)

def max_eig_grid_rel(got,ref):
    got=np.asarray(got);ref=np.asarray(ref)
    if got.ndim==1: got=got[:,None]
    if ref.ndim==1: ref=ref[:,None]
    if got.shape!=ref.shape: return float('inf')
    return max((eigenvalue_max_rel(got[:,i],ref[:,i]) for i in range(ref.shape[1])),default=0.0)

def compare_trace(path:Path,facade:SolverFacade):
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
        got=modal_grid(facade,model,m['Rotor_Spd'])
        return kind,max_eig_grid_rel(got,outs[0]),POLICY['eigenvalues_rel']

    if kind=='chr_asym':
        # V2 deliberately changes the K1b contribution depending on nargout.
        nout=int(round(scalar(m.get('nargout_requested'),1)))
        got=asym_modal_grid(facade,model,m['Rotor_Spd'],want_vectors=(nout>=2))
        return kind,max_eig_grid_rel(got,outs[0]),POLICY['eigenvalues_rel']

    if kind=='freq_rsp':
        sp=np.asarray(m['Rotor_Spd'],dtype=float).ravel()
        got=facade.frequency_response(model,sp)
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
            kw['initial_estimates']=initial
            kw['method']=3
        got=facade.critical_speeds(model,**kw)
        if isinstance(got,tuple): got=got[0]
        ref=np.asarray(outs[0],dtype=float).ravel()
        return kind,rel_vec(ref,got),POLICY['critical_speeds_rel']

    raise RuntimeError(kind)

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--trace-dir',required=True)
    ap.add_argument('--status-csv',required=True)
    ap.add_argument('--inventory',required=True)
    ap.add_argument('--output',required=True)
    ap.add_argument('--library-path')
    args=ap.parse_args()

    inv=json.loads(Path(args.inventory).read_text())
    status={}
    with open(args.status_csv,newline='') as f:
        for row in csv.DictReader(f): status[row['problem']]=row

    # Load the qualified shared library once. This avoids thousands of repeated
    # ctypes DLL loads while retaining one-for-one numerical comparison of every
    # traced authority evaluation.
    facade=SolverFacade(args.library_path)

    rows=[];ok=True
    trace_root=Path(args.trace_dir)
    for idx,p in enumerate(inv['problems'],1):
        st=status.get(p['problem'],{'status':'MISSING','message':'not executed'})
        if st['status']!='PASS': ok=False
        traces=sorted(trace_root.glob(f"{p['problem']}__*.mat"))
        if p['class']=='A_SOLVER' and not traces: ok=False

        print(f"G14_PROGRESS {idx:02d}/{len(inv['problems'])} {p['problem']} class={p['class']} octave={st['status']} traces={len(traces)}",flush=True)

        max_ratio=0.0
        comparisons=[]
        for t in traces:
            kind,err,limit=compare_trace(t,facade)
            passed=bool(err<=limit)
            ok &= passed
            max_ratio=max(max_ratio,err/limit if limit else 0.0)
            comparisons.append({
                'trace':t.name,
                'kind':kind,
                'error':err,
                'limit':limit,
                'status':'PASS' if passed else 'FAIL',
            })
            print(f"  {t.name}: {kind} error={err:.6e} limit={limit:.6e} status={'PASS' if passed else 'FAIL'}",flush=True)

        rows.append({
            'problem':p['problem'],
            'class':p['class'],
            'octave_status':st['status'],
            'octave_message':st.get('message',''),
            'trace_count':len(traces),
            'max_gate_ratio':max_ratio,
            'comparisons':comparisons,
        })

    result={
        'gate':'G14',
        'overall':'PASS' if ok else 'FAIL',
        'problem_count':len(rows),
        'A_solver':sum(r['class']=='A_SOLVER' for r in rows),
        'B_analytical':sum(r['class']=='B_ANALYTICAL' for r in rows),
        'octave_pass':sum(r['octave_status']=='PASS' for r in rows),
        'trace_count':sum(r['trace_count'] for r in rows),
        'rows':rows,
        'policy':POLICY,
    }
    Path(args.output).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
    return 0 if ok else 1

if __name__=='__main__':
    raise SystemExit(main())
