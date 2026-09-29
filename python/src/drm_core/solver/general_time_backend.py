"""Validate and marshal only: coefficients and all time physics run natively."""
import ctypes as ct
from dataclasses import replace
import numpy as np
from .general_frf_backend import prepare
from .ffi import SolverLibraryError

def configure_time(lib):
    try:fn=lib.rd_general_time_response_v1
    except AttributeError as exc:raise SolverLibraryError('General Time Response requires rd_general_time_response_v1; rebuild solver. No fallback.') from exc
    I=ct.c_int;D=ct.c_double;P=ct.POINTER(D);IP=ct.POINTER(I)
    fn.argtypes=[I,P,I,P,I,P,I,IP,I,P,P,I,P,I,I,P,I,D,D,D]+[P]*5+[IP]+[P]*3+[IP]
    fn.restype=I
    return fn

def prepare_time(backend,model,time_s,force_real,speed,weight,gamma,beta,tol):
    if any(np.iscomplexobj(x) for x in (time_s,force_real,speed)):raise ValueError('Time, speed and F(t) must be real SI values.')
    t=np.ascontiguousarray(time_s,dtype=float);n=4*len(model.nodes)
    if t.ndim!=1 or not 2<=len(t)<=10000 or not np.isfinite(t).all() or np.any(np.diff(t)<=0):raise ValueError('time_s requires 2..10000 finite strictly increasing seconds; correct the time grid.')
    if not 8<=n<=512 or 320*n*len(t)+240*n*n>512*1024**2:raise ValueError('General Time numerical buffers exceed 512 MiB or 2..128 nodes; reduce nodes/time samples.')
    sp=np.asarray(speed,dtype=float);variable=int(sp.ndim>0)
    if (variable and sp.shape!=t.shape) or not np.isfinite(sp).all():raise ValueError(f'Speed must be a finite scalar or history of shape {t.shape}, rad/s.')
    omega=np.full(len(t),float(sp)) if not variable else np.ascontiguousarray(sp)
    F=np.asarray(force_real,dtype=float)
    if F.shape!=(n,len(t)) or not np.isfinite(F).all():raise ValueError(f'F(t) received shape {F.shape}; expected finite real {(n,len(t))}, x/y in N and alpha/beta in N m.')
    if not all(np.isfinite(x) and x>0 for x in (gamma,beta,tol)):raise ValueError('gamma, beta and tol must be finite positive values; defaults .5, .25, 1e-6.')
    if not isinstance(weight,(bool,np.bool_)):raise ValueError('weight must be boolean; true adds native M*g with g=-9.8065 m/s².')
    bs=[]
    for b in model.advanced_bearings:
        if not all(hasattr(b,k) for k in ('mxx','myy','mxy','myx')):bs.append(b);continue
        values={}
        for k in ('mxx','myy','mxy','myx'):
            value=getattr(b,k)
            if value is None:continue
            mass=np.asarray(value,dtype=float)
            if not mass.size or not np.isfinite(mass).all() or np.any(mass!=mass.flat[0]):raise ValueError('A4 requires constant bearing mass: ROSS assembles M once at zero; varying Mb is outside scope.')
            values[k]=float(mass.flat[0])
        bs.append(replace(b,**values))
    prepared=prepare(backend,replace(model,advanced_bearings=bs),omega,vector_response=True,time_domain=True)
    return t,omega,np.asfortranarray(F),variable,prepared

def execute(backend,model,time_s,force_real,speed=0.,weight=False,gamma=.5,beta=.25,tol=1e-6):
    fn=configure_time(backend.lib)
    t,omega,F,var,prepared=prepare_time(backend,model,time_s,force_real,speed,weight,gamma,beta,tol)
    z,sh,di,nodes,coeff,*rest=prepared;meta=rest[-1];n,nt=F.shape
    out=[np.empty_like(F,order='F') for _ in range(3)];alpha=np.empty(nt);Fe=np.empty_like(F,order='F');it=np.zeros(nt,dtype=np.int32)
    res=np.zeros(nt);ar=np.zeros(nt);cond=np.zeros(nt);failed=ct.c_int();p=backend._ptr
    st=fn(len(z),p(z),sh.shape[1],p(sh),di.shape[1],p(di),len(nodes),backend._iptr(nodes),nt,p(t),p(omega),var,p(coeff),n,nt,p(F),int(weight),gamma,beta,tol,*[p(x) for x in out],p(alpha),p(Fe),backend._iptr(it),p(res),p(ar),p(cond),ct.byref(failed))
    if st:
        i=max(0,min(nt-1,failed.value-1))
        raise SolverLibraryError(f'General Time Response status={st}, step={failed.value} (one-based), iterations={it[i]}, residual={ar[i]:.9g}; invalid input (10), unsupported (20), singular/nonfinite (30), or 50-iteration nonconvergence (40). Check supports, input and time step; no fallback.')
    if not all(np.isfinite(x).all() for x in [*out,alpha,Fe,res,ar,cond]):raise SolverLibraryError('Nonfinite General Time result rejected.')
    return t,omega,alpha,F,Fe,*out,it,res,ar,cond,meta
