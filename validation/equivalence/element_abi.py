from __future__ import annotations
import ctypes as ct
import numpy as np
from drm_core.solver.ffi import load_library
D=ct.c_double;I=ct.c_int;DP=ct.POINTER(D)
def _mats():return [np.empty((8,8),dtype=np.float64,order='F') for _ in range(4)]
def _p(a):return a.ctypes.data_as(DP)
def circular(stype,L,do,di,E,G,rho,axial,torque,library_path=None):
    lib=load_library(library_path);f=lib.rd_element_circular_legacy;f.argtypes=[I,D,D,D,D,D,D,D,D,DP,DP,DP,DP];f.restype=I;out=_mats();st=f(int(stype),L,do,di,E,G,rho,axial,torque,*[_p(x) for x in out])
    if st:raise RuntimeError(f'rd_element_circular_legacy status={st}')
    return tuple(out)
def tapered(stype,L,do1,do2,di1,di2,E,G,rho,axial,library_path=None):
    lib=load_library(library_path);f=lib.rd_element_tapered_legacy;f.argtypes=[I,D,D,D,D,D,D,D,D,D,DP,DP,DP,DP];f.restype=I;out=_mats();st=f(int(stype),L,do1,do2,di1,di2,E,G,rho,axial,*[_p(x) for x in out])
    if st:raise RuntimeError(f'rd_element_tapered_legacy status={st}')
    return tuple(out)
def asymmetric(stype,L,EIx,EIy,Phix,Phiy,rhoA,rhoI,axial,library_path=None):
    lib=load_library(library_path);f=lib.rd_element_asymmetric_legacy;f.argtypes=[I,D,D,D,D,D,D,D,D,DP,DP,DP,DP];f.restype=I;out=_mats();st=f(int(stype),L,EIx,EIy,Phix,Phiy,rhoA,rhoI,axial,*[_p(x) for x in out])
    if st:raise RuntimeError(f'rd_element_asymmetric_legacy status={st}')
    return tuple(out)
