from __future__ import annotations
from pathlib import Path
import json
import numpy as np

def save_figure(fig,path,formats=("png","svg","pdf"),**kwargs):
    base=Path(path);base.parent.mkdir(parents=True,exist_ok=True);written=[]
    for fmt in formats:
        p=base.with_suffix('.'+fmt.lstrip('.'));fig.savefig(p,bbox_inches='tight',**kwargs);written.append(p)
    return written

def export_array_csv(path,array,header=None):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);a=np.asarray(array)
    if a.ndim==1:a=a[:,None]
    if np.iscomplexobj(a):
        cols=[];names=[]
        for j in range(a.shape[1]):
            cols.extend([a[:,j].real,a[:,j].imag]);names.extend([f"col{j}_real",f"col{j}_imag"])
        a=np.column_stack(cols);header=header or names
    np.savetxt(p,a,delimiter=',',header='' if header is None else ','.join(header),comments='');return p

def export_npz(path,**arrays):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);np.savez(p,**arrays);return p

def export_metadata_json(path,metadata):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(metadata,indent=2,sort_keys=True,default=lambda x:np.asarray(x).tolist())+'\n',encoding='utf-8');return p
