from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use('Agg',force=True)
import matplotlib.pyplot as plt

def plot_root_locus(speeds_rad_s,eigenvalues,NX=1.5,ax=None):
    sp=np.asarray(speeds_rad_s,dtype=float).ravel();ev=np.asarray(eigenvalues)
    if sp.size<2:raise ValueError('there must be more than one rotor spin speed')
    if ev.ndim==1:ev=ev[:,None]
    if ev.shape[1]!=sp.size:raise ValueError('eigenvalue speed dimension mismatch')
    ax=ax or plt.subplots()[1];max_axes=abs(NX)*float(np.max(sp))
    ax.plot(ev.real,ev.imag)
    ax.plot(ev[:,0].real,ev[:,0].imag,'x',label=f'{sp[0]*60/(2*np.pi):g} rev/min')
    ax.plot(ev[:,-1].real,ev[:,-1].imag,'d',label=f'{sp[-1]*60/(2*np.pi):g} rev/min')
    ax.set_xlim(-max_axes,max_axes);ax.set_ylim(-max_axes,max_axes);ax.set_aspect('equal',adjustable='box')
    ax.set_xlabel('Real (eigenvalues)');ax.set_ylabel('Imag (eigenvalues)');ax.set_title('Root Locus');ax.grid(True);ax.legend();return ax
