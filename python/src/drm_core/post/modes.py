from __future__ import annotations

import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np


def _normalize_mode(mode):
    v=np.asarray(mode,complex).copy()
    if v.ndim!=1: raise ValueError("mode: expected a one-dimensional vector")
    x=v[0::4];y=v[1::4]
    if not x.size: raise ValueError("mode: no translational DOFs")
    ix=int(np.argmax(np.abs(x)));iy=int(np.argmax(np.abs(y)))
    ref=y[iy] if abs(y[iy])>0.4*abs(x[ix]) else x[ix]
    if abs(ref)==0: raise ValueError("mode: cannot normalize a zero translational mode")
    return v/ref


def plot_mode(model, mode, eigenvalue=None, ax=None):
    v=_normalize_mode(mode); n=len(model.nodes)
    if v.size < 4*n: raise ValueError(f"mode: length={v.size}; expected at least {4*n}")
    z=np.asarray([x.z_m for x in model.nodes],float)
    if z.size<2 or np.max(np.abs(z))==0: raise ValueError("model.nodes: invalid axial coordinates for mode plot")
    ax=ax or plt.figure().add_subplot(111,projection="3d")
    zz=[];xx=[];yy=[]
    for i in range(n-1):
        le=z[i+1]-z[i]; q=np.linspace(0,1,21)
        n1=1-3*q*q+2*q**3;n2=q-2*q*q+q**3;n3=3*q*q-2*q**3;n4=-q*q+q**3
        xr=n1*v[4*i].real + le*n2*v[4*i+3].real + n3*v[4*(i+1)].real + le*n4*v[4*(i+1)+3].real
        yr=n1*v[4*i+1].real - le*n2*v[4*i+2].real + n3*v[4*(i+1)+1].real - le*n4*v[4*(i+1)+2].real
        zz.extend(z[i]+le*q);xx.extend(xr);yy.extend(yr)
    scale=max(np.max(np.abs(xx)),np.max(np.abs(yy)),np.finfo(float).eps)
    ax.plot(np.asarray(zz)/np.max(np.abs(z)),np.asarray(xx)/scale,np.asarray(yy)/scale)
    th=np.linspace(0,2*np.pi,200)
    for i in range(n):
        ax.plot(np.full(th.size,z[i]/np.max(np.abs(z))),np.real(v[4*i]*np.exp(1j*th))/scale,np.real(v[4*i+1]*np.exp(1j*th))/scale,linewidth=.5)
    if eigenvalue is not None: ax.set_title(f"Nat Freq = {abs(eigenvalue)/(2*np.pi):.6g} Hz")
    ax.set_axis_off()
    return ax
