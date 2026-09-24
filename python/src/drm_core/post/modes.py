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


def _interpolate_centerline(model, v, points_per_element=24):
    n=len(model.nodes)
    if v.size < 4*n:
        raise ValueError(f"mode: length={v.size}; expected at least {4*n}")
    z=np.asarray([node.z_m for node in model.nodes],float)
    if z.size<2 or np.ptp(z)<=0:
        raise ValueError("model.nodes: invalid axial coordinates for mode plot")

    zz=[];xx=[];yy=[]
    for i in range(n-1):
        le=z[i+1]-z[i]
        q=np.linspace(0.0,1.0,int(points_per_element),endpoint=(i==n-2))
        n1=1-3*q*q+2*q**3
        n2=q-2*q*q+q**3
        n3=3*q*q-2*q**3
        n4=-q*q+q**3
        xr=(n1*v[4*i] + le*n2*v[4*i+3] +
            n3*v[4*(i+1)] + le*n4*v[4*(i+1)+3])
        yr=(n1*v[4*i+1] - le*n2*v[4*i+2] +
            n3*v[4*(i+1)+1] - le*n4*v[4*(i+1)+2])
        zz.extend(z[i]+le*q);xx.extend(xr);yy.extend(yr)
    return z,np.asarray(zz),np.asarray(xx),np.asarray(yy)


def plot_mode_3d(
    model,
    mode,
    eigenvalue=None,
    ax=None,
    *,
    orbit_samples=72,
    orbit_stations=34,
    points_per_element=24,
    reference_line=True,
    show_node_markers=True,
    view_elev=22.0,
    view_azim=-58.0,
):
    """Plot a complex lateral mode as a 3-D shaft centerline plus whirl orbits.

    The axial machine coordinate is shown as Z.  X and Y are the two lateral
    displacement directions.  The red curve is the normalized real-phase
    deflected centerline; magenta loops are the complex whirl orbits at nodes;
    the black line is the undeformed shaft reference.  No modal quantities are
    recomputed here—the function is visualization-only and consumes the
    qualified eigenvector supplied by the solver.
    """
    v=_normalize_mode(mode)
    z,zz,xc,yc=_interpolate_centerline(model,v,points_per_element)
    span=float(np.ptp(z))
    z0=float(np.min(z))
    zn=(z-z0)/span
    zzn=(zz-z0)/span

    lateral=np.concatenate((np.abs(xc),np.abs(yc),np.abs(v[0::4]),np.abs(v[1::4])))
    scale=max(float(np.nanmax(lateral)),np.finfo(float).eps)

    ax=ax or plt.figure().add_subplot(111,projection="3d")
    # Map the machine axial coordinate to the matplotlib X axis so the
    # physical Z shaft line reads diagonally across the page like the supplied
    # DRM reference. Matplotlib axis labels retain the physical coordinate
    # names: axial=Z, lateral=X/Y.
    if reference_line:
        ax.plot(zn,np.zeros_like(zn),np.zeros_like(zn),color="black",linewidth=0.9,alpha=0.85)

    ax.plot(zzn,xc.real/scale,yc.real/scale,color="red",linewidth=2.0,zorder=6)

    theta=np.linspace(0.0,2.0*np.pi,int(orbit_samples),endpoint=True)
    jot=-1j if eigenvalue is not None and np.imag(eigenvalue)<0 else 1j
    exp_theta=np.exp(jot*theta)

    # Plot orbit ellipses at interpolated stations, not only FE nodes. This
    # reproduces the dense DRM mode-shape visualization while using exactly
    # the same complex eigenvector interpolation as the red centerline.
    nstations=max(2,min(int(orbit_stations),zzn.size))
    stations=np.unique(np.linspace(0,zzn.size-1,nstations).astype(int))
    for k in stations:
        ox=np.real(xc[k]*exp_theta)/scale
        oy=np.real(yc[k]*exp_theta)/scale
        oz=np.full(theta.size,zzn[k])
        ax.plot(oz,ox,oy,color="#ff35f2",linewidth=0.48,alpha=0.9,zorder=3)

    if show_node_markers:
        ax.plot(
            zn,
            np.real(v[0::4])/scale,
            np.real(v[1::4])/scale,
            linestyle="none",
            marker="o",
            markersize=3.2,
            markerfacecolor="red",
            markeredgecolor="red",
            zorder=7,
        )

    if eigenvalue is not None:
        ax.set_title(f"Mode shape 3D — {abs(eigenvalue)/(2*np.pi):.6g} Hz",pad=8)

    ax.set_xlabel("Z",labelpad=2)
    ax.set_ylabel("X",labelpad=2)
    ax.set_zlabel("Y",labelpad=2)
    ax.set_xlim(-0.02,1.02)
    ax.set_ylim(-1.15,1.15)
    ax.set_zlim(-1.15,1.15)
    ax.set_box_aspect((2.8,1.15,1.15))
    ax.view_init(elev=float(view_elev),azim=float(view_azim))
    ax.grid(False)

    # The reference image is intentionally sparse.  Retain axis labels while
    # suppressing pane fills/ticks so the mode/orbit geometry dominates.
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    for axis in (ax.xaxis,ax.yaxis,ax.zaxis):
        try:
            axis.pane.fill=False
            axis.pane.set_edgecolor((1,1,1,0))
        except Exception:
            pass
    return ax


def plot_mode(model, mode, eigenvalue=None, ax=None):
    """Legacy Stage 1 plot contract retained byte-for-behaviour compatibility."""
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
