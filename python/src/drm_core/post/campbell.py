from __future__ import annotations
import matplotlib
matplotlib.use("Agg",force=True)
import matplotlib.pyplot as plt
import numpy as np

def whirl_direction(kappa_mode):
    k=np.asarray(kappa_mode,float).ravel();npos=np.count_nonzero(k>0);nneg=np.count_nonzero(k<0)
    if npos and not nneg:return 1
    if nneg and not npos:return -1
    return 0

def plot_campbell(speeds_rad_s,eigenvalues,NX=1.5,damped_NF=True,kappa=None,ax=None):
    sp=np.asarray(speeds_rad_s,float).ravel();ev=np.asarray(eigenvalues)
    if sp.size<2:raise ValueError('there must be more than one rotor spin speed')
    if ev.ndim==1:ev=ev[:,None]
    if ev.shape[1]!=sp.size:raise ValueError('eigenvalue speed dimension mismatch')
    ax=ax or plt.subplots()[1];rpm=sp*60/(2*np.pi);maxrpm=float(np.max(rpm));maxhz=abs(NX)*maxrpm/60
    nf=(np.abs(ev.imag) if damped_NF else np.abs(ev))/(2*np.pi)
    for row in nf:ax.plot(rpm,row)
    for n in range(1,int(abs(NX))+1):ax.plot(rpm,n*sp/(2*np.pi),'--')
    if NX<0:ax.plot(rpm,sp/(4*np.pi),'--')
    if kappa is not None:
        kp=np.asarray(kappa)
        if kp.ndim!=3 or kp.shape[1:]!=(ev.shape[0],sp.size):raise ValueError('kappa must have shape (ndof,nmode,nspeed)')
        for j in range(ev.shape[0]):
            for i in range(sp.size):
                if rpm[i]==0:continue
                d=whirl_direction(kp[0::2,j,i]);marker='>' if d>0 else ('<' if d<0 else 'o')
                ax.plot(rpm[i],nf[j,i],marker=marker,linestyle='None')
    ax.set_xlabel('Rotor spin speed (rev/min)');ax.set_ylabel('Damped natural frequencies (Hz)' if damped_NF else 'Undamped natural frequencies (Hz)')
    ax.set_xlim(0,maxrpm);ax.set_ylim(0,maxhz);ax.grid(True);return ax
