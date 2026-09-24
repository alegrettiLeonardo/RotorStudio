from __future__ import annotations
from pathlib import Path
import json
import numpy as np

def result_summary(result)->dict:
    d={'result_type':type(result).__name__,'metadata':getattr(result,'metadata',{})}
    for name in ('speed_rad_s','speeds_rad_s','critical_speeds_rad_s','natural_frequency_hz','damping_ratio','time_s'):
        if hasattr(result,name):
            v=getattr(result,name)
            if v is not None:
                a=np.asarray(v); d[name]={'shape':list(a.shape),'min_abs':float(np.min(np.abs(a))) if a.size else None,'max_abs':float(np.max(np.abs(a))) if a.size else None}
    return d

def write_json_report(result,path):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(result_summary(result),indent=2,sort_keys=True,default=str)+'\n');return p

def write_markdown_report(result,path):
    s=result_summary(result);p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    lines=[f"# {s['result_type']} report",'','## Metadata','','```json',json.dumps(s['metadata'],indent=2,sort_keys=True,default=str),'```','','## Arrays','']
    for k,v in s.items():
        if k not in ('result_type','metadata'): lines.append(f"- **{k}**: `{v}`")
    p.write_text('\n'.join(lines)+'\n',encoding='utf-8');return p
