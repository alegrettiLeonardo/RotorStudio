import matplotlib
matplotlib.use("Agg",force=True)
import matplotlib.pyplot as plt
import numpy as np
def plot_campbell(speeds_rad_s,eigenvalues,ax=None):
    ax=ax or plt.subplots()[1]; sp=np.asarray(speeds_rad_s)*60/(2*np.pi); ev=np.asarray(eigenvalues)
    if ev.ndim==1: ev=ev[:,None]
    for i in range(0,min(ev.shape[0],16),2): ax.plot(sp,np.abs(ev[i,:])/(2*np.pi))
    ax.set_xlabel("Rotor speed (rev/min)");ax.set_ylabel("Natural frequency (Hz)");ax.grid(True);return ax
