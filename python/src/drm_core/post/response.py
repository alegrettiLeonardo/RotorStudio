from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use('Agg',force=True)
import matplotlib.pyplot as plt

def decode_outnodes(outnodes):
    dofs=[];labels=[];names={1:'x',2:'y',3:'theta',4:'psi'}
    for x in np.atleast_1d(outnodes):
        node=int(np.floor(float(x)+.05));direction=int(np.floor(10*(float(x)+.05-node)))
        if direction not in names or node<1:raise ValueError(f'invalid output specification {x}')
        dofs.append(4*node+direction-5);labels.append(f'Node {node}, {names[direction]}')
    return np.asarray(dofs,int),labels

def _plot_pair(x,response,outnodes,xlabel,axes=None):
    r=np.asarray(response);xx=np.asarray(x,float).ravel();dofs,labels=decode_outnodes(outnodes)
    if r.ndim!=2 or r.shape[1]!=xx.size or np.max(dofs)>=r.shape[0]:raise ValueError('response dimensions/output DOFs inconsistent')
    if axes is None:_,axes=plt.subplots(2,1)
    axes[0].semilogy(xx,np.abs(r[dofs,:]).T);axes[0].set_ylabel('Response magnitude (m)');axes[0].grid(True);axes[0].legend(labels)
    axes[1].plot(xx,-np.angle(r[dofs,:]).T*180/np.pi);axes[1].set_ylabel('Phase (degrees)');axes[1].set_xlabel(xlabel);axes[1].set_ylim(-200,200);axes[1].grid(True);axes[1].legend(labels)
    return axes

def plot_response(speeds_rad_s,response,outnodes,axes=None):
    return _plot_pair(np.asarray(speeds_rad_s,float)*60/(2*np.pi),response,outnodes,'Rotor spin speed (rev/min)',axes=axes)

def plot_frf(omega_rad_s,response,outnodes,axes=None):
    return _plot_pair(np.asarray(omega_rad_s,float)/(2*np.pi),response,outnodes,'Excitation frequency (Hz)',axes=axes)
