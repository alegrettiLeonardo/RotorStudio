"""Thin I8 binding for global rotor-bearing-support matrix composition."""
from __future__ import annotations
import ctypes as ct
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from drm_core.domain.model import BearingSupport
from .ffi import SolverLibraryError,load_library

@dataclass(frozen=True)
class IrdinGlobalSupportMatrices:
    M:np.ndarray;C:np.ndarray;G:np.ndarray;K:np.ndarray

def _f(a,shape=None):
    x=np.asarray(a,dtype=np.float64)
    if shape is not None and x.shape!=shape:
        raise ValueError(f"shape={x.shape}; expected {shape}")
    if not np.isfinite(x).all():
        raise ValueError("matrix contains NaN/Inf")
    return np.asfortranarray(x)

def _tables(value,ns):
    a=np.asarray(value,dtype=np.float64)
    if a.shape!=(ns,2,2):
        raise ValueError(f"support tables shape={a.shape}; expected {(ns,2,2)}")
    if not np.isfinite(a).all():
        raise ValueError("support table contains NaN/Inf")
    return np.ascontiguousarray(np.stack([x.ravel(order="F") for x in a]).ravel())

def assemble_support_global_matrices(*,rotor_M,rotor_C,rotor_G,rotor_K,
                                     support_nodes,support_masses,bearing_K,bearing_C,
                                     support_K,support_C,library_path:str|Path|None=None):
    mr=_f(rotor_M)
    if mr.ndim!=2 or mr.shape[0]!=mr.shape[1] or mr.shape[0]%4:
        raise ValueError("rotor matrices require square 4N shape")
    nd=mr.shape[0]
    cr=_f(rotor_C,(nd,nd));gr=_f(rotor_G,(nd,nd));kr=_f(rotor_K,(nd,nd))
    nodes=np.ascontiguousarray(support_nodes,dtype=np.int32)
    masses=np.ascontiguousarray(support_masses,dtype=np.float64);ns=len(nodes)
    if ns<1 or len(masses)!=ns or not np.isfinite(masses).all() or np.any(masses<=0):
        raise ValueError("support nodes/masses must be finite, positive and equally sized")
    kb=_tables(bearing_K,ns);cb=_tables(bearing_C,ns);ks=_tables(support_K,ns);cs=_tables(support_C,ns)
    no=nd+2*ns;outs=[np.full((no,no),np.nan,dtype=np.float64,order="F") for _ in range(4)]
    lib=load_library(library_path)
    try: fn=lib.rd_irdin_support_global_matrices_v1
    except AttributeError as exc:
        raise SolverLibraryError("I8 requires rd_irdin_support_global_matrices_v1; rebuild native solver.") from exc
    I=ct.c_int;D=ct.c_double;P=ct.POINTER(D);IP=ct.POINTER(I)
    fn.argtypes=[I,I,IP,P,P,P,P,P,P,P,P,P,I,I,P,P,P,P,I,I];fn.restype=I
    ptr=lambda a:a.ctypes.data_as(P)
    status=int(fn(nd//4,ns,nodes.ctypes.data_as(IP),ptr(masses),ptr(kb),ptr(cb),ptr(ks),ptr(cs),
                  ptr(mr),ptr(cr),ptr(gr),ptr(kr),nd,nd*nd,
                  *(ptr(x) for x in outs),no,no*no))
    if status:
        raise ValueError(f"I8 native global support assembly status={status}")
    if not all(np.isfinite(x).all() for x in outs):
        raise RuntimeError("I8 returned nonfinite matrices")
    return IrdinGlobalSupportMatrices(*outs)

def support_arrays(supports:list[BearingSupport]):
    nodes=[];mass=[];ks=[];cs=[]
    for s in supports:
        nodes.append(int(s.node));mass.append(float(s.mass_kg))
        ks.append([[s.kxx_n_m,s.kxy_n_m],[s.kyx_n_m,s.kyy_n_m]])
        cs.append([[s.cxx_ns_m,s.cxy_ns_m],[s.cyx_ns_m,s.cyy_ns_m]])
    return nodes,mass,np.asarray(ks,float),np.asarray(cs,float)

__all__=["IrdinGlobalSupportMatrices","assemble_support_global_matrices","support_arrays"]
