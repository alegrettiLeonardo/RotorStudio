from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use('Agg',force=True)
import matplotlib.pyplot as plt

def mode_geometry(model,mode,points_per_element=21):
    v=np.asarray(mode,dtype=complex).reshape(-1);n=len(model.nodes);ndof=4*n
    if v.size!=ndof:raise ValueError(f'mode has {v.size} entries; expected {ndof}')
    modex=v[0::4];modey=v[1::4];xmax=float(np.max(np.abs(modex)));ymax=float(np.max(np.abs(modey)))
    den=modey[int(np.argmax(np.abs(modey)))] if ymax>.4*xmax else modex[int(np.argmax(np.abs(modex)))]
    if abs(den)>0:v=v/den
    z=np.array([x.z_m for x in model.nodes],float);xi=np.linspace(0,1,points_per_element)
    N1=1-3*xi**2+2*xi**3;N2=xi-2*xi**2+xi**3;N3=3*xi**2-2*xi**3;N4=-xi**2+xi**3
    xx=[];yy=[];zz=[]
    for i in range(n-1):
        L=z[i+1]-z[i];dofx=[4*i,4*i+3,4*i+4,4*i+7];dofy=[4*i+1,4*i+2,4*i+5,4*i+6]
        N=np.column_stack([N1,L*N2,N3,L*N4]);xx.append(N@v[dofx].real);yy.append(np.column_stack([N1,-L*N2,N3,-L*N4])@v[dofy].real);zz.append(z[i]+L*xi)
    return np.concatenate(zz),np.concatenate(xx),np.concatenate(yy)

def plot_mode(model,mode,eigenvalue=None,ax=None):
    z,x,y=mode_geometry(model,mode);ax=ax or plt.figure().add_subplot(111,projection='3d')
    scale=max(float(np.max(np.abs(x))),float(np.max(np.abs(y))),np.finfo(float).tiny);span=max(float(np.ptp(z)),np.finfo(float).tiny)
    ax.plot(z/span,x/scale,y/scale);ax.set_axis_off()
    if eigenvalue is not None:ax.set_title(f'Nat Freq = {abs(eigenvalue)/(2*np.pi):.6g} Hz')
    return ax
