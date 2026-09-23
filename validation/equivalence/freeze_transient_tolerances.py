from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.io import loadmat

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--matlab-baseline',required=True);ap.add_argument('--source-reference-dir',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    out=Path(a.output)
    if out.exists():raise SystemExit(f'REFUSE_OVERWRITE: {out}; tolerances are immutable once frozen')
    m=loadmat(a.matlab_baseline,squeeze_me=True,struct_as_record=False);rd=Path(a.source_reference_dir)
    tref=np.load(rd/'time_fdn_source_reference.npz');rref=np.load(rd/'runup_source_reference.npz')
    tdofs=np.asarray(tref['response_dofs'],int);dt=float(np.max(np.abs(np.asarray(m['time_response'])[tdofs,:]-np.asarray(tref['response']))))
    rt=np.asarray(rref['time']);mt=np.asarray(m['runup_time']).ravel();mr=np.asarray(m['runup_response']);rdofs=np.asarray(rref['response_dofs'],int)
    interp=np.vstack([np.interp(rt,mt,row) for row in mr[rdofs,:]]);dr=float(np.max(np.abs(interp-np.asarray(rref['response']))))
    policy={'policy':'10x MATLAB-vs-independent-oracle discrepancy, frozen before Fortran comparison','matlab_baseline_sha256':sha(a.matlab_baseline),'time_source_reference_sha256':sha(rd/'time_fdn_source_reference.npz'),'runup_source_reference_sha256':sha(rd/'runup_source_reference.npz'),'time_fdn_matlab_vs_oracle_max_abs_m':dt,'runup_matlab_vs_oracle_max_abs_m':dr,'time_fdn_max_abs_m':max(1e-10,10*dt),'runup_max_abs_m':max(1e-10,10*dr),'time_fdn_force_max_abs':1e-12}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(policy,indent=2));print(json.dumps(policy,indent=2))
if __name__=='__main__':main()
