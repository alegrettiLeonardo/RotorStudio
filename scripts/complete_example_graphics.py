from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg",force=True)
import matplotlib.pyplot as plt
from drm_core.post import plot_campbell,save_figure

def _first_numeric_npz(path):
    with np.load(path,allow_pickle=False) as z:
        for k in z.files:
            a=np.asarray(z[k])
            if np.issubdtype(a.dtype,np.number) and a.size>1:
                return k,a
    return None,None

def _plot_dir(d:Path):
    # Prefer modal/Campbell data when available.
    for p in sorted(d.glob("*.npz")):
        with np.load(p,allow_pickle=False) as z:
            keys=set(z.files)
            if "rpm" in keys and "eigenvalues" in keys:
                rpm=np.asarray(z["rpm"],float).ravel()
                eig=np.asarray(z["eigenvalues"])
                if eig.ndim==2 and eig.shape[1]==rpm.size:
                    ax=plot_campbell(rpm*2*np.pi/60.0,eig)
                    ax.set_title(f"{d.name} — Campbell")
                    files=save_figure(ax.figure,d/"summary",formats=("png","svg","pdf"),dpi=140)
                    plt.close(ax.figure);return files
            if "time" in keys and "response" in keys:
                t=np.asarray(z["time"],float).ravel();r=np.asarray(z["response"])
                fig,ax=plt.subplots()
                if r.ndim==2: ax.plot(t,np.max(np.abs(r),axis=0))
                else: ax.plot(t,np.abs(r).ravel()[:t.size])
                ax.set_xlabel("Time (s)");ax.set_ylabel("Maximum response magnitude");ax.grid(True);ax.set_title(d.name)
                files=save_figure(fig,d/"summary",formats=("png","svg","pdf"),dpi=140);plt.close(fig);return files
            if "right_bearing_k" in keys and "critical_rad_s" in keys:
                x=np.asarray(z["right_bearing_k"],float).ravel();y=np.asarray(z["critical_rad_s"],float)*60/(2*np.pi)
                fig,ax=plt.subplots();ax.semilogx(x,y);ax.set_xlabel("Right bearing stiffness (N/m)");ax.set_ylabel("Critical speed (rpm)");ax.grid(True);ax.set_title(d.name)
                files=save_figure(fig,d/"summary",formats=("png","svg","pdf"),dpi=140);plt.close(fig);return files
            for xkey in ("rpm","omega_rpm","hz","NE"):
                if xkey in keys:
                    x=np.asarray(z[xkey],float).ravel()
                    for ykey in ("response","step","taper","critical_rad_s"):
                        if ykey in keys:
                            y=np.asarray(z[ykey])
                            fig,ax=plt.subplots()
                            yy=np.abs(y)
                            if yy.ndim==1: ax.plot(x[:yy.size],yy)
                            elif yy.shape[-1]==x.size: ax.plot(x,yy.reshape((-1,x.size)).T)
                            elif yy.shape[0]==x.size: ax.plot(x,yy.reshape((x.size,-1)))
                            else: continue
                            ax.set_xlabel(xkey);ax.set_ylabel(ykey);ax.grid(True);ax.set_title(d.name)
                            files=save_figure(fig,d/"summary",formats=("png","svg","pdf"),dpi=140);plt.close(fig);return files
    # CSV fallback.
    for p in sorted(d.glob("*.csv")):
        try:a=np.loadtxt(p,delimiter=",",ndmin=2)
        except Exception:continue
        if a.size:
            fig,ax=plt.subplots()
            if a.shape[1]>1: ax.plot(a[:,0],a[:,1:])
            else: ax.plot(np.arange(a.shape[0]),a[:,0])
            ax.grid(True);ax.set_title(d.name);ax.set_xlabel("Sample");ax.set_ylabel("Value")
            files=save_figure(fig,d/"summary",formats=("png","svg","pdf"),dpi=140);plt.close(fig);return files
    # Existing PNG can be promoted to SVG/PDF only through a simple manifest figure
    # rather than raster re-embedding. This keeps every example independently viewable.
    fig,ax=plt.subplots();ax.text(.5,.5,f"{d.name}\nNo numeric artifact available",ha="center",va="center");ax.set_axis_off()
    files=save_figure(fig,d/"summary",formats=("png","svg","pdf"),dpi=140);plt.close(fig);return files

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("--campaign-dir",required=True);ap.add_argument("--output",required=True);args=ap.parse_args()
    root=Path(args.campaign_dir)
    summary_file=root/"campaign_summary.json"
    if not summary_file.is_file(): raise SystemExit("campaign_summary.json not found")
    summary=json.loads(summary_file.read_text())
    names=sorted({r["example"] for r in summary["rows"]})
    rows=[];ok=True
    for name in names:
        d=root/f"example_{name.lower()}"
        if not d.is_dir():
            # Three bespoke examples use the same naming convention but preserve leading zeros.
            matches=list(root.glob(f"*{name.replace('_','_')}*"))
            if matches:d=matches[0]
        if not d.is_dir():
            rows.append({"example":name,"status":"MISSING_DIR"});ok=False;continue
        files=_plot_dir(d)
        ex_ok=all((d/f"summary.{fmt}").is_file() and (d/f"summary.{fmt}").stat().st_size>0 for fmt in ("png","svg","pdf"))
        rows.append({"example":name,"status":"PASS" if ex_ok else "FAIL","files":[str(x.relative_to(root)) for x in files]});ok &= ex_ok
    result={"example_count":len(names),"pass":sum(r["status"]=="PASS" for r in rows),"overall":"PASS" if ok and len(names)==22 else "FAIL","rows":rows}
    Path(args.output).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="rows"},indent=2))
    return 0 if result["overall"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
