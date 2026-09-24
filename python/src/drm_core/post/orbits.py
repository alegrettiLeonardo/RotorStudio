from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use('Agg',force=True)
import matplotlib.pyplot as plt

def orbit_xy(mode,node,eigenvalue=None,npts=341,scale=1e6):
    v=np.asarray(mode,dtype=complex).reshape(-1);i=int(node)-1
    if i<0 or 4*i+1>=v.size:raise ValueError('output node outside mode vector')
    theta=np.linspace(0,np.deg2rad(340),npts);sign=-1.0 if eigenvalue is not None and np.imag(eigenvalue)<0 else 1.0;phase=np.exp(1j*sign*theta)
    return scale*np.real(v[4*i]*phase),scale*np.real(v[4*i+1]*phase)

def plot_orbits(mode,output_nodes,title=None,eigenvalue=None,ax=None):
    ax=ax or plt.subplots()[1]
    for node in np.atleast_1d(output_nodes):
        x,y=orbit_xy(mode,int(node),eigenvalue);ax.plot(x,y,label=f'Node {int(node)}');ax.plot(x[0],y[0],'x');ax.plot(x[-1],y[-1],'d')
    ax.set_aspect('equal',adjustable='box');ax.set_axis_off()
    if title:ax.set_title(title)
    if len(np.atleast_1d(output_nodes))>1:ax.legend()
    return ax
