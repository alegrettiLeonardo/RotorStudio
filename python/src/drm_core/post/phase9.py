from dataclasses import dataclass
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use("Agg",force=True)
import matplotlib.pyplot as plt
@dataclass(frozen=True)
class FFTResult:
    frequency_hz:np.ndarray
    spectrum:np.ndarray
def fft_scale(response,time_s):
    t=np.asarray(time_s,float).reshape(-1);r=np.asarray(response)
    if r.ndim==1:r=r[None,:]
    if r.shape[1]!=t.size:raise ValueError("response columns must equal len(time_s)")
    if t.size<2:raise ValueError("at least two samples required")
    dt=(t.max()-t.min())/(t.size-1);rec=t.min()+np.arange(t.size)*dt
    if np.max(np.abs(t-rec))>1e-10*max(abs(t.max()),1.0):raise ValueError("time_s must have equal increments")
    df=1/(t.max()-t.min())
    return FFTResult(df*np.arange(t.size),(2.0/t.size)*np.fft.fft(r,axis=1))
def _ev(e):
    a=np.asarray(e);return a[:,None] if a.ndim==1 else a
def plot_root_locus(speeds_rad_s,eigenvalues,nx=1.0,ax=None):
    e=_ev(eigenvalues);ax=ax or plt.subplots()[1]
    for i in range(e.shape[0]):ax.plot(e[i].real,e[i].imag,marker=".",markersize=2)
    lim=abs(float(nx))*max(float(np.max(np.abs(speeds_rad_s))) if np.size(speeds_rad_s) else 1,1)
    ax.set(xlim=(-lim,lim),ylim=(-lim,lim),xlabel="Real(lambda) [1/s]",ylabel="Imag(lambda) [rad/s]");ax.grid(True);return ax
def plot_eigenvalue_traces(speeds_rad_s,eigenvalues,nx=1.0):
    sp=np.asarray(speeds_rad_s)*60/(2*np.pi);e=_ev(eigenvalues);fig,(ar,ai)=plt.subplots(2,1,sharex=True)
    for i in range(e.shape[0]):ar.plot(sp,e[i].real);ai.plot(sp,e[i].imag/(2*np.pi))
    for n in range(1,max(1,int(abs(nx)))+1):ai.plot(sp,n*sp/60,linestyle="--",linewidth=.8)
    ar.set_ylabel("Real(lambda) [1/s]");ai.set_ylabel("Imag(lambda)/(2pi) [Hz]");ai.set_xlabel("Rotor speed [rev/min]");ar.grid(True);ai.grid(True);return fig
def plot_mode(model,mode,eigenvalue=None,phases=25):
    q=np.asarray(mode,complex).reshape(-1);n=len(model.nodes);z=np.array([a.z_m for a in model.nodes]);x=q[0:4*n:4];y=q[1:4*n:4]
    if q.size<4*n:raise ValueError("mode needs four DOFs per node")
    fig=plt.figure();ax=fig.add_subplot(111,projection="3d");scale=max(np.max(np.abs(x)),np.max(np.abs(y)),1e-30)
    for ph in np.linspace(0,2*np.pi,phases,endpoint=False):ax.plot(z,np.real(x*np.exp(1j*ph))/scale,np.real(y*np.exp(1j*ph))/scale,alpha=.25)
    ax.set_xlabel("z [m]");ax.set_ylabel("x/max");ax.set_zlabel("y/max")
    if eigenvalue is not None:ax.set_title(f"Mode - {abs(complex(eigenvalue).imag)/(2*np.pi):.4g} Hz")
    return fig
def plot_orbits(mode,nodes,title=None,eigenvalue=None):
    q=np.asarray(mode,complex).reshape(-1);nodes=[int(n) for n in nodes];fig,axs=plt.subplots(1,len(nodes),squeeze=False,figsize=(3.2*len(nodes),3.2));th=np.linspace(0,2*np.pi,181)
    for ax,node in zip(axs[0],nodes):
        i=4*node-4;ax.plot(np.real(q[i]*np.exp(1j*th)),np.real(q[i+1]*np.exp(1j*th)));ax.set_aspect("equal");ax.grid(True);ax.set_title(f"Node {node}")
    fig.suptitle(title or "Rotor orbits");fig.tight_layout();return fig
def _rsp(x,response,out_dofs,xlabel):
    r=np.asarray(response,complex);fig,(aa,ap)=plt.subplots(2,1,sharex=True)
    for i in out_dofs:aa.plot(x,np.abs(r[int(i)]));ap.plot(x,np.unwrap(np.angle(r[int(i)]))*180/np.pi,label=f"DOF {int(i)+1}")
    aa.set_ylabel("Amplitude");ap.set_ylabel("Phase [deg]");ap.set_xlabel(xlabel);aa.grid(True);ap.grid(True);ap.legend();fig.tight_layout();return fig
def plot_response(speeds_rad_s,response,out_dofs=(0,)):return _rsp(np.asarray(speeds_rad_s)*60/(2*np.pi),response,out_dofs,"Rotor speed [rev/min]")
def plot_frf(omega_rad_s,response,out_dofs=(0,)):return _rsp(np.asarray(omega_rad_s)/(2*np.pi),response,out_dofs,"Excitation frequency [Hz]")
def export_figure(fig,stem,formats=("png","svg","pdf"),dpi=160):
    stem=Path(stem);stem.parent.mkdir(parents=True,exist_ok=True);out=[]
    for ext in formats:
        p=stem.with_suffix("."+ext);fig.savefig(p,dpi=dpi,bbox_inches="tight");out.append(p)
    return out
def export_npz(path,**arrays):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(p,**arrays);return p
def export_csv(path,**arrays):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);cols={}
    for name,val in arrays.items():
        a=np.asarray(val)
        if a.ndim==0:a=a.reshape(1)
        if a.ndim!=1:continue
        if np.iscomplexobj(a):cols[name+"_real"]=a.real;cols[name+"_imag"]=a.imag
        else:cols[name]=a
    n=max((len(v) for v in cols.values()),default=0)
    with p.open("w",newline="") as f:
        w=csv.writer(f);keys=list(cols);w.writerow(keys)
        for i in range(n):w.writerow([cols[k][i] for k in keys])
    return p
def export_bundle(outdir,figures=None,arrays=None,metadata=None):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True);m={"figures":{},"data":{},"metadata":metadata or {}}
    for name,fig in (figures or {}).items():m["figures"][name]=[p.name for p in export_figure(fig,out/name)]
    if arrays:
        m["data"]["npz"]=export_npz(out/"data.npz",**arrays).name;m["data"]["csv"]=export_csv(out/"data.csv",**arrays).name
    (out/"manifest.json").write_text(json.dumps(m,indent=2,sort_keys=True));return m
