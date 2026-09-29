"""Validation-only access to native pre-integration matrices."""
import ctypes as ct
import numpy as np
from drm_core.solver.general_frf_backend import prepare

def configure(lib):
    I=ct.c_int;D=ct.c_double;P=ct.POINTER(D);IP=ct.POINTER(I)
    for name,args in [('rd_transient_shaft_v1',[D]*4+[P]),('rd_transient_disk_v1',[D,P]),('rd_transient_stiffness_v1',[I,P,I,P,I,P]+[P]*3),('rd_speed_gradient_v1',[I]+[P]*3),('rd_time_matrices_v1',[I,P,I,P,I,P,I,IP,P,D,D]+[P]*8)]:
        f=getattr(lib,name);f.argtypes=args;f.restype=I

def matrices(backend,m,s):
    configure(backend.lib);t=np.asarray(s['time_s']);omega=np.broadcast_to(s['speed'],t.shape).copy()
    z,sh,di,nodes,coef,*_=prepare(backend,m,omega,vector_response=True)
    n=4*len(z);p=backend._ptr;alpha=np.zeros(len(t))
    if np.ndim(s['speed']): assert backend.lib.rd_speed_gradient_v1(len(t),p(t),p(omega),p(alpha))==0
    out={k:[] for k in ('M','C','G','K','Ksdt','Ceff','Keff','Fg')}
    for i in range(len(t)):
        arrays=[np.zeros((n,n),order='F') for _ in range(7)]+[np.zeros(n)]
        c=np.asfortranarray(coef[:,:,i])
        status=backend.lib.rd_time_matrices_v1(len(z),p(z),sh.shape[1],p(sh),di.shape[1],p(di),len(nodes),backend._iptr(nodes),p(c),omega[i],alpha[i],*[p(a) for a in arrays])
        assert status==0,status
        for k,a in zip(out,arrays):out[k].append(a)
    result={k:np.stack(v,axis=-1) for k,v in out.items()}
    ks=[np.zeros((n,n),order='F') for _ in range(3)]
    assert backend.lib.rd_transient_stiffness_v1(len(z),p(z),sh.shape[1],p(sh),di.shape[1],p(di),*[p(a) for a in ks])==0
    result.update(Kshaft=ks[0],Kdisk=ks[1],alpha=alpha)
    return result
