from __future__ import annotations

import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np
from .whirl import whirl


def _decode_outnode(spec):
    inode = int(np.floor(float(spec)+0.05))
    idir = int(np.floor(10*(float(spec)+0.05-inode)))
    if inode < 1 or idir not in (1,2,3,4):
        raise ValueError(f"outnode={spec}: expected node.dof with dof 1..4")
    return inode, idir, 4*inode+idir-5


def _axes(axes):
    if axes is not None:
        return axes
    _, ax = plt.subplots(2,1)
    return ax


def plot_response(speeds_rad_s, response, outnodes, axes=None):
    speeds=np.asarray(speeds_rad_s,float); rsp=np.asarray(response,complex)
    if speeds.ndim!=1 or speeds.size<2: raise ValueError("speeds_rad_s: expected more than one speed")
    if rsp.ndim!=2 or rsp.shape[1]!=speeds.size: raise ValueError("response: expected shape (ndof, nspeed)")
    dec=[_decode_outnode(v) for v in np.atleast_1d(outnodes)]
    dof=[d[2] for d in dec]
    if max(dof)>=rsp.shape[0]: raise ValueError("outnode: requested DOF outside response range")
    axes=_axes(axes); rpm=speeds*60/(2*np.pi)
    axes[0].semilogy(rpm,np.abs(rsp[dof,:]).T)
    axes[0].set_xlabel("Rotor spin speed (rev/min)");axes[0].set_ylabel("Response magnitude (m)");axes[0].grid(True)
    axes[1].plot(rpm,-180/np.pi*np.angle(rsp[dof,:]).T)
    axes[1].set_xlabel("Rotor spin speed (rev/min)");axes[1].set_ylabel("Phase (degrees)");axes[1].set_ylim(-200,200);axes[1].grid(True)
    if len(dec)==2 and dec[0][0]==dec[1][0] and {dec[0][1],dec[1][1]} in ({1,2},{3,4}):
        sd=sorted(dof)
        for i in range(speeds.size):
            if whirl(rsp[sd[0],i],rsp[sd[1],i])[0] < 0:
                left=rpm[i] if i==0 else .5*(rpm[i-1]+rpm[i])
                right=rpm[i] if i==rpm.size-1 else .5*(rpm[i]+rpm[i+1])
                axes[0].axvspan(left,right,alpha=.15)
    return axes


def plot_frf(omega_rad_s,response,outnodes,axes=None):
    omega=np.asarray(omega_rad_s,float);rsp=np.asarray(response,complex)
    if omega.ndim!=1 or omega.size<2: raise ValueError("omega_rad_s: expected more than one frequency")
    if rsp.ndim!=2 or rsp.shape[1]!=omega.size: raise ValueError("response: expected shape (ndof, nfreq)")
    dof=[_decode_outnode(v)[2] for v in np.atleast_1d(outnodes)]
    if max(dof)>=rsp.shape[0]: raise ValueError("outnode: requested DOF outside response range")
    axes=_axes(axes);hz=omega/(2*np.pi)
    axes[0].semilogy(hz,np.abs(rsp[dof,:]).T);axes[0].set_xlabel("Excitation frequency (Hz)");axes[0].set_ylabel("Response magnitude (m)");axes[0].grid(True)
    axes[1].plot(hz,-180/np.pi*np.angle(rsp[dof,:]).T);axes[1].set_xlabel("Excitation frequency (Hz)");axes[1].set_ylabel("Phase (degrees)");axes[1].set_ylim(-200,200);axes[1].grid(True)
    return axes
