"""Thin I4 binding for the historical iRdin bearing-support coupling kernel."""
from __future__ import annotations
import ctypes as ct
from dataclasses import dataclass
import math
from pathlib import Path
import numpy as np
from drm_core.domain.model import BearingSupport
from .ffi import SolverLibraryError, load_library

STATUS_NAMES={0:"SUCCESS",10:"INVALID_INPUT",12:"INVALID_DIMENSION",13:"INSUFFICIENT_CAPACITY",14:"NONFINITE_RESULT"}

class IrdinSupportInputError(ValueError):
    def __init__(self,status:int,context:str):
        self.status=int(status);super().__init__(f"I4 {STATUS_NAMES.get(int(status),'UNKNOWN_STATUS')} ({int(status)}): {context}")

class IrdinSupportComputationError(RuntimeError):
    def __init__(self,status:int,context:str):
        self.status=int(status);super().__init__(f"I4 {STATUS_NAMES.get(int(status),'UNKNOWN_STATUS')} ({int(status)}): {context}")

@dataclass(frozen=True)
class IrdinSupportMatrices:
    M: np.ndarray
    C: np.ndarray
    K: np.ndarray

def _matrix(name,value):
    a=np.asarray(value,dtype=np.float64)
    if a.shape!=(2,2): raise IrdinSupportInputError(10,f"{name} shape={a.shape}; expected (2,2)")
    if not np.isfinite(a).all(): raise IrdinSupportInputError(10,f"{name} contains NaN/Inf")
    return np.ascontiguousarray(np.asfortranarray(a).ravel(order="F"))

def _support(support):
    if not isinstance(support,BearingSupport): raise IrdinSupportInputError(10,"support must be a BearingSupport")
    mass=float(support.mass_kg)
    if not math.isfinite(mass) or mass<=0: raise IrdinSupportInputError(10,"support mass must be finite and > 0")
    ks=[[support.kxx_n_m,support.kxy_n_m],[support.kyx_n_m,support.kyy_n_m]]
    cs=[[support.cxx_ns_m,support.cxy_ns_m],[support.cyx_ns_m,support.cyy_ns_m]]
    return mass,_matrix("support K",ks),_matrix("support C",cs)

def support_element_matrices(*,bearing_K,bearing_C,support:BearingSupport,library_path:str|Path|None=None):
    kb=_matrix("bearing K",bearing_K); cb=_matrix("bearing C",bearing_C)
    mass,ks,cs=_support(support)
    lib=load_library(library_path)
    try: fn=lib.rd_irdin_support_matrices_v1
    except AttributeError as exc:
        raise SolverLibraryError("I4 requires rd_irdin_support_matrices_v1; rebuild the native solver. No Python fallback is available.") from exc
    D,I,P=ct.c_double,ct.c_int,ct.POINTER(ct.c_double)
    fn.argtypes=[D,P,P,P,P,P,I,I,P,I,I,P,I,I];fn.restype=I
    out=[np.full((4,4),np.nan,dtype=np.float64,order="F") for _ in range(3)]
    ptr=lambda a:a.ctypes.data_as(P)
    status=int(fn(mass,ptr(kb),ptr(cb),ptr(ks),ptr(cs),ptr(out[0]),4,16,ptr(out[1]),4,16,ptr(out[2]),4,16))
    if status in (10,12,13): raise IrdinSupportInputError(status,"native support element rejected the request")
    if status: raise IrdinSupportComputationError(status,"native support element failed")
    if not all(np.isfinite(a).all() for a in out): raise IrdinSupportComputationError(14,"native support element returned nonfinite output")
    return IrdinSupportMatrices(*out)

__all__=["IrdinSupportInputError","IrdinSupportComputationError","IrdinSupportMatrices","support_element_matrices"]
