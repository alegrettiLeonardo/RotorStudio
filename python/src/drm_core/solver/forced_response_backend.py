"""Thin split-complex ABI binding; no production H matrix or Python solve."""
import ctypes as ct
import numpy as np
from .general_frf_backend import prepare,POLICIES
from .ffi import SolverLibraryError

def configure_forced_response(lib):
    try: fn=lib.rd_forced_response_v1
    except AttributeError as exc: raise SolverLibraryError('Forced Response requires rd_forced_response_v1; rebuild the native solver. No fallback.') from exc
    I=ct.c_int;D=ct.c_double;P=ct.POINTER(D);IP=ct.POINTER(I)
    fn.argtypes=[I,P,I,P,I,P,I,IP,I,P,I,D,P,I,I]+[P]*10
    fn.restype=I
    return fn

def execute(backend,model,frequency_rad_s,force_real,force_imag,speed=None):
    fn=configure_forced_response(backend.lib)
    f=np.asarray(frequency_rad_s,dtype=float)
    shape=(4*len(model.nodes),f.size)
    if force_real is None or force_imag is None:
        raise ValueError('Forced Response requires force_real and force_imag arrays [4*nodes, frequencies], in N or N m; supply both components.')
    if np.iscomplexobj(force_real) or np.iscomplexobj(force_imag):
        raise ValueError("Split force buffers must be real-valued; provide quadrature in force_imag.")
    fr=np.asarray(force_real,dtype=float);fi=np.asarray(force_imag,dtype=float)
    if fr.shape!=shape or fi.shape!=shape or not np.isfinite(fr).all() or not np.isfinite(fi).all():
        raise ValueError(f'Invalid force: received shapes {fr.shape}/{fi.shape}; expected finite real/imag arrays {shape}. Use N for x/y and N m for alpha/beta.')
    z,sh,di,nodes,coeff,f,speeds,policy,fixed,metadata=prepare(backend,model,f,speed,vector_response=True)
    fr=np.asfortranarray(fr);fi=np.asfortranarray(fi)
    out=[np.empty(shape,dtype=float,order='F') for _ in range(6)]
    residual=np.empty(len(f));condition=np.empty(len(f));p=backend._ptr
    status=fn(len(z),p(z),sh.shape[1],p(sh),di.shape[1],p(di),len(nodes),backend._iptr(nodes),len(f),p(f),POLICIES[policy],fixed,p(coeff),*shape,p(fr),p(fi),*[p(a) for a in out],p(residual),p(condition))
    if status: raise SolverLibraryError(f'Forced Response rd_forced_response_v1 status={status}; invalid/singular/nonfinite system. Check force, supports and excitation; no fallback.')
    if not all(np.isfinite(a).all() for a in [*out,residual,condition]): raise SolverLibraryError('Nonfinite Forced Response rejected.')
    return f,speeds,fr+1j*fi,out[0]+1j*out[1],out[2]+1j*out[3],out[4]+1j*out[5],residual,condition,policy,metadata
