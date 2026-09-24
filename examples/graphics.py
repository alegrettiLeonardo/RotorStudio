from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
from drm_core.post.phase9 import export_figure

_AXIS_KEYS=("rpm","omega_rpm","hz","time","time_s","NE","right_bearing_k","speed")
_SKIP_KEYS={"metadata"}

def _plot_array(ax,x,y,label):
    a=np.asarray(y)
    if a.ndim==0:return False
    if np.iscomplexobj(a):
        if "eigen" in label.lower(): a=np.abs(np.imag(a))/(2*np.pi)
        else:a=np.abs(a)
    if a.ndim==1:
        if len(a)==len(x): ax.plot(x,a,label=label);return True
        ax.plot(np.arange(len(a)),a,label=label);return True
    # Select orientation whose sample count matches x.
    if a.shape[-1]==len(x):
        rows=a.reshape((-1,a.shape[-1]))
    elif a.shape[0]==len(x):
        rows=np.moveaxis(a,0,-1).reshape((-1,len(x)))
    else:
        rows=a.reshape((a.shape[0],-1))
        x=np.arange(rows.shape[-1])
    for i,row in enumerate(rows[:8]): ax.plot(x,row,label=f"{label}[{i}]")
    return True

def _render_npz(path:Path,outbase:Path)->bool:
    with np.load(path,allow_pickle=True) as z:
        keys=[k for k in z.files if k not in _SKIP_KEYS]
        axis_key=next((k for k in _AXIS_KEYS if k in keys),None)
        x=np.asarray(z[axis_key]) if axis_key else None
        data=[k for k in keys if k!=axis_key and np.asarray(z[k]).dtype!=object]
        if not data:return False
        if x is None:
            a=np.asarray(z[data[0]]); n=a.shape[-1] if a.ndim else 1;x=np.arange(n);axis_key="sample"
        fig,ax=plt.subplots(figsize=(8,5))
        plotted=False
        for k in data[:4]: plotted|=_plot_array(ax,x,z[k],k)
        if not plotted:plt.close(fig);return False
        ax.set_xlabel(axis_key);ax.set_ylabel("response / frequency / value");ax.set_title(path.stem.replace("_"," "))
        ax.grid(True); 
        if len(ax.lines)<=12: ax.legend(fontsize="small")
        export_figure(fig,outbase);plt.close(fig);return True

def _render_csv(path:Path,outbase:Path)->bool:
    try:a=np.loadtxt(path,delimiter=",")
    except Exception:return False
    if a.size==0:return False
    if a.ndim==1:a=a[:,None]
    fig,ax=plt.subplots(figsize=(8,5))
    x=a[:,0] if a.shape[1]>1 else np.arange(a.shape[0])
    start=1 if a.shape[1]>1 else 0
    for j in range(start,min(a.shape[1],9)):ax.plot(x,a[:,j],label=f"col{j+1}")
    if a.shape[1]==1:ax.plot(x,a[:,0])
    ax.set_xlabel("first column / sample");ax.set_ylabel("value");ax.set_title(path.stem.replace("_"," "))
    ax.grid(True)
    if len(ax.lines)<=12:ax.legend(fontsize="small")
    export_figure(fig,outbase);plt.close(fig);return True

def render_example_directory(directory:Path)->dict:
    generated=[]
    numeric=sorted(directory.glob("*.npz"))+sorted(directory.glob("*.csv"))
    for source in numeric:
        if source.name in {"campaign_status.csv"}:continue
        base=directory/(source.stem+"_plot")
        try:
            ok=_render_npz(source,base) if source.suffix==".npz" else _render_csv(source,base)
        except Exception:
            ok=False
        if ok:
            generated.extend(str(base.with_suffix(ext).name) for ext in (".png",".svg",".pdf"))
    # Some legacy scripts already create PNGs. Add vector/PDF counterparts only
    # for our generated plots; an example is complete when at least one
    # headless scientific plot exists in each required format.
    formats={ext:sorted(p.name for p in directory.glob("*"+ext)) for ext in (".png",".svg",".pdf")}
    return {"directory":directory.name,"numeric_sources":[p.name for p in numeric],
            "generated":generated,"formats":formats,
            "complete":all(formats[e] for e in formats)}

def render_campaign_graphics(root)->dict:
    root=Path(root)
    dirs=sorted(p for p in root.glob("example_*") if p.is_dir())
    rows=[render_example_directory(p) for p in dirs]
    missing=[r["directory"] for r in rows if not r["complete"]]
    result={"unique_examples":len(rows),"complete_examples":len(rows)-len(missing),"missing":missing,"examples":rows}
    (root/"graphics_manifest.json").write_text(json.dumps(result,indent=2))
    return result
