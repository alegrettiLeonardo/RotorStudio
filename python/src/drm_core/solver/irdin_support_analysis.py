"""I9 native modal and synchronous solve for expanded iRdin support systems."""
from __future__ import annotations
import ctypes as ct
from dataclasses import dataclass
from pathlib import Path
import numpy as np

from drm_core.domain.model import Force
from .ffi import SolverLibraryError,load_library


@dataclass(frozen=True)
class IrdinExpandedModal:
    eigenvalues: np.ndarray
    eigenvectors: np.ndarray


@dataclass(frozen=True)
class IrdinExpandedResponse:
    response: np.ndarray
    residual: float


def _matrix(value,name):
    a=np.asarray(value,dtype=np.float64)
    if a.ndim!=2 or a.shape[0]!=a.shape[1]:
        raise ValueError(f"{name} must be square")
    if not np.isfinite(a).all():
        raise ValueError(f"{name} contains NaN/Inf")
    return np.asfortranarray(a)


def expanded_modal(M,C,K,*,library_path:str|Path|None=None):
    m=_matrix(M,"M");n=m.shape[0]
    c=_matrix(C,"C");k=_matrix(K,"K")
    if c.shape!=(n,n) or k.shape!=(n,n):
        raise ValueError("M/C/K shapes must agree")
    lib=load_library(library_path)
    try: fn=lib.rd_irdin_support_modal_v1
    except AttributeError as exc:
        raise SolverLibraryError("I9 requires rd_irdin_support_modal_v1; rebuild native solver.") from exc
    I=ct.c_int;D=ct.c_double;P=ct.POINTER(D)
    fn.argtypes=[I,P,P,P,I,I,I,P,P,P,P,I,I];fn.restype=I
    wr=np.empty(2*n,dtype=np.float64);wi=np.empty(2*n,dtype=np.float64)
    vr=np.empty((n,2*n),dtype=np.float64,order="F")
    vi=np.empty_like(vr,order="F")
    ptr=lambda a:a.ctypes.data_as(P)
    status=int(fn(n,ptr(m),ptr(c),ptr(k),n,n*n,2*n,ptr(wr),ptr(wi),ptr(vr),ptr(vi),n,n*(2*n)))
    if status:
        raise SolverLibraryError(f"I9 native expanded modal status={status}")
    eig=wr+1j*wi;vec=vr+1j*vi
    if not np.isfinite(eig).all() or not np.isfinite(vec).all():
        raise SolverLibraryError("I9 expanded modal returned NaN/Inf")
    return IrdinExpandedModal(eig,vec)


def expanded_synchronous(M,C,K,*,nnode:int,omega_rad_s:float,forces:list[Force],
                         library_path:str|Path|None=None):
    m=_matrix(M,"M");n=m.shape[0]
    c=_matrix(C,"C");k=_matrix(K,"K")
    if c.shape!=(n,n) or k.shape!=(n,n):
        raise ValueError("M/C/K shapes must agree")
    rows=[]
    for force in forces:
        if force.force_type!=1 or len(force.values)<3:
            raise ValueError("I9 iRdin response accepts only qualified Force type 1 unbalance rows")
        node=int(force.values[0]);mag=float(force.values[1]);phase=float(force.values[2])
        if not np.isfinite([mag,phase]).all():
            raise ValueError("I9 unbalance magnitude/phase must be finite")
        rows.append((node,mag,phase))
    if not rows:
        raise ValueError("I9 synchronous response requires at least one unbalance")
    nodes=np.ascontiguousarray([x[0] for x in rows],dtype=np.int32)
    mag=np.ascontiguousarray([x[1] for x in rows],dtype=np.float64)
    phase=np.ascontiguousarray([x[2] for x in rows],dtype=np.float64)
    lib=load_library(library_path)
    try: fn=lib.rd_irdin_support_synchronous_v1
    except AttributeError as exc:
        raise SolverLibraryError("I9 requires rd_irdin_support_synchronous_v1; rebuild native solver.") from exc
    I=ct.c_int;D=ct.c_double;P=ct.POINTER(D);IP=ct.POINTER(I)
    fn.argtypes=[I,I,P,P,P,I,I,D,I,IP,P,P,P,P,I,ct.POINTER(D)];fn.restype=I
    qr=np.empty(n,dtype=np.float64);qi=np.empty(n,dtype=np.float64);res=ct.c_double()
    ptr=lambda a:a.ctypes.data_as(P)
    status=int(fn(int(nnode),n,ptr(m),ptr(c),ptr(k),n,n*n,float(omega_rad_s),len(rows),
                  nodes.ctypes.data_as(IP),ptr(mag),ptr(phase),ptr(qr),ptr(qi),n,ct.byref(res)))
    if status:
        raise SolverLibraryError(f"I9 native expanded synchronous status={status}")
    q=qr+1j*qi
    if not np.isfinite(q).all() or not np.isfinite(res.value):
        raise SolverLibraryError("I9 expanded synchronous returned NaN/Inf")
    return IrdinExpandedResponse(q,float(res.value))


__all__=["IrdinExpandedModal","IrdinExpandedResponse","expanded_modal","expanded_synchronous"]
