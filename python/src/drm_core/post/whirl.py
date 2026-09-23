import numpy as np
def whirl(u,v):
    u=np.asarray(u,dtype=complex);v=np.asarray(v,dtype=complex)
    if u.shape!=v.shape: raise ValueError("u and v must have equal shape")
    k=np.zeros(u.shape,float);amp=np.zeros(u.shape,float)
    for idx in np.ndindex(u.shape):
        ua,va=abs(u[idx]),abs(v[idx])
        if ua*va<1e-16: continue
        h12=ua*va*np.cos(np.angle(u[idx])-np.angle(v[idx])); vals=np.linalg.eigvalsh([[ua*ua,h12],[h12,va*va]])
        k[idx]=np.sqrt(max(0.0,vals[0]/vals[1])); d=(np.angle(v[idx])-np.angle(u[idx]))%(2*np.pi)
        if 0<d<np.pi:k[idx]=-k[idx]
        amp[idx]=np.sqrt(vals[1])
    return k,amp
