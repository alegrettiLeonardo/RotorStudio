from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use('Agg',force=True)
import matplotlib.pyplot as plt

def plot_eigenvalues(speeds_rad_s,eigenvalues,NX=1.5,axes=None):
    sp=np.asarray(speeds_rad_s,float).ravel();ev=np.asarray(eigenvalues)
    if sp.size<2:raise ValueError('there must be more than one rotor spin speed')
    if ev.ndim==1:ev=ev[:,None]
    if ev.shape[1]!=sp.size:raise ValueError('eigenvalue speed dimension mismatch')
    if axes is None:_,axes=plt.subplots(1,2)
    rpm=sp*60/(2*np.pi);maxrpm=float(np.max(rpm));maxhz=abs(NX)*maxrpm/60
    axes[0].plot(rpm,np.sort(ev.real,axis=0).T);axes[0].set_xlabel('Rotor spin speed (rev/min)');axes[0].set_ylabel('Real (eigenvalues)');axes[0].set_xlim(0,maxrpm);axes[0].grid(True)
    axes[1].plot(rpm,np.sort(np.abs(ev.imag),axis=0).T/(2*np.pi))
    for n in range(1,int(abs(NX))+1):axes[1].plot(rpm,n*sp/(2*np.pi),'--')
    axes[1].set_xlabel('Rotor spin speed (rev/min)');axes[1].set_ylabel('Imag (eigenvalues) (Hz)');axes[1].set_xlim(0,maxrpm);axes[1].set_ylim(-.05*maxhz,maxhz);axes[1].grid(True);return axes
