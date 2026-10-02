"""B3 thin Python adapter for dedicated axial/torsional 6-DOF workflows.

All numerical assembly, subspace extraction and eigensolution remain native
Fortran. Python validates inputs, maps the qualified B2 model descriptors,
allocates ABI buffers and constructs typed results.
"""
from __future__ import annotations
import ctypes as ct
from dataclasses import dataclass
from typing import Iterable
import numpy as np

from .ffi import SolverLibraryError,load_library
from .sixdof_global import _descriptors,_finite_real,_ptr

FAMILY_CODE={"Axial":1,"Torsional":2}
B3_STATUS={
    0:"SUCCESS",40:"INVALID_INPUT",41:"UNSUPPORTED_SUBSPACE",42:"LAPACK_FAILURE",
    43:"NONFINITE_RESULT",44:"MODE_COUNT_MISMATCH",
    20:"B2_INVALID_INPUT",21:"B2_INVALID_DIMENSION",22:"B2_UNSUPPORTED",
    23:"B2_SINGULAR_MASS",24:"B2_LAPACK_FAILURE",25:"B2_INSUFFICIENT_CAPACITY",
    26:"B2_NONFINITE_RESULT",27:"B2_ELEMENT_FAILURE",
}


class AxialTorsionalError(RuntimeError):
    def __init__(self,status:int,context:str):
        self.status=int(status)
        super().__init__(
            f"B3 {B3_STATUS.get(self.status,'UNKNOWN_STATUS')} ({self.status}): "
            f"{context}. No Python numerical fallback was used."
        )


@dataclass(frozen=True)
class AxialTorsionalModalResult:
    family:str
    speed_rad_s:float
    eigenvalues:np.ndarray
    wn_rad_s:np.ndarray
    wd_rad_s:np.ndarray
    damping_ratio:np.ndarray
    log_dec:np.ndarray
    eigenvectors:np.ndarray
    residual:np.ndarray
    M:np.ndarray
    K:np.ndarray
    C:np.ndarray
    G:np.ndarray
    Ksdt:np.ndarray
    max_decoupling_ratio:float
    metadata:dict


@dataclass(frozen=True)
class AxialTorsionalSweepResult:
    family:str
    speed_rad_s:np.ndarray
    wn_rad_s:np.ndarray
    wd_rad_s:np.ndarray
    damping_ratio:np.ndarray
    log_dec:np.ndarray
    eigenvectors:tuple[np.ndarray,...]
    residual:np.ndarray
    max_decoupling_ratio:np.ndarray
    metadata:dict


def _family(value:str)->tuple[str,int]:
    name=str(value).strip().capitalize()
    if name not in FAMILY_CODE:
        raise ValueError("family must be 'Axial' or 'Torsional'")
    return name,FAMILY_CODE[name]


def _native_b3(library_path=None):
    lib=load_library(library_path)
    I,D=ct.c_int,ct.c_double
    IP,P=ct.POINTER(I),ct.POINTER(D)
    try:
        req=lib.rd_axial_torsional_required_v1
        modal=lib.rd_axial_torsional_modal_v1
    except AttributeError as exc:
        raise SolverLibraryError(
            "B3 requires rd_axial_torsional_*_v1 symbols. Rebuild the B3 native library; "
            "no fallback is available."
        ) from exc
    req.argtypes=[I,IP,IP,IP];req.restype=I
    modal.argtypes=[
        I,I,IP,P,IP,I,IP,P,I,IP,P,I,D,
        I,I,I,I,I,IP,P,
        P,P,P,P,P,P,P,P,P,P,P
    ]
    modal.restype=I
    return req,modal


def _status(code:int,context:str)->None:
    if int(code):
        raise AxialTorsionalError(int(code),context)


def run_family_modal_6dof(model,speed_rad_s:float,family:str,library_path=None)->AxialTorsionalModalResult:
    family_name,family_code=_family(family)
    speed=_finite_real("speed_rad_s",speed_rad_s)
    nn,ns,sn,sp,sf,nd,dn,dp,nb,bn,bp=_descriptors(model,speed,speed,library_path)
    req,fn=_native_b3(library_path)
    maxm=ct.c_int();mvals=ct.c_int();qvals=ct.c_int()
    _status(req(nn,ct.byref(maxm),ct.byref(mvals),ct.byref(qvals)),"axial/torsional size query")
    mode_cap=maxm.value
    wn=np.full(mode_cap,np.nan);wd=np.full(mode_cap,np.nan)
    zeta=np.full(mode_cap,np.nan);logdec=np.full(mode_cap,np.nan);residual=np.full(mode_cap,np.nan)
    q=np.full((nn,mode_cap),np.nan,dtype=np.float64,order="F")
    matrices=[np.full((nn,nn),np.nan,dtype=np.float64,order="F") for _ in range(5)]
    nmode=ct.c_int();dec=ct.c_double()
    code=fn(
        nn,ns,_ptr(sn),_ptr(sp),_ptr(sf),nd,_ptr(dn),_ptr(dp),nb,_ptr(bn),_ptr(bp),
        family_code,speed,mode_cap,nn,q.size,nn,matrices[0].size,
        ct.byref(nmode),ct.byref(dec),
        _ptr(wn),_ptr(wd),_ptr(zeta),_ptr(logdec),_ptr(residual),_ptr(q),
        *[_ptr(a) for a in matrices],
    )
    _status(code,f"{family_name.lower()} dedicated modal analysis")
    count=int(nmode.value)
    if count<1 or count>mode_cap:
        raise AxialTorsionalError(44,f"{family_name} native mode count {count}/{mode_cap}")
    arrays=[wn[:count],wd[:count],zeta[:count],logdec[:count],residual[:count],q[:,:count],*matrices]
    if not all(np.isfinite(a).all() for a in arrays) or not np.isfinite(dec.value):
        raise AxialTorsionalError(43,f"{family_name} native result contains nonfinite values")
    eig=1j*wd[:count].astype(np.complex128)
    M,K,C,G,Ksdt=(a.copy(order="F") for a in matrices)
    return AxialTorsionalModalResult(
        family_name,speed,eig.copy(),wn[:count].copy(),wd[:count].copy(),
        zeta[:count].copy(),logdec[:count].copy(),q[:,:count].astype(np.complex128,copy=True),
        residual[:count].copy(),M,K,C,G,Ksdt,float(dec.value),
        {
            "dof_model":6,
            "family_dof":"z" if family_name=="Axial" else "theta",
            "family_dof_offset":2 if family_name=="Axial" else 5,
            "workflow":"B3_DEDICATED_INVARIANT_SUBSPACE",
            "coefficient_policy":"SYNCHRONOUS_COEFFICIENTS",
            "matched_whirl":False,
            "synchronous_rouch":False,
            "forced_response":False,
            "transient":False,
            "ross_authority_sha":"6320eab9f890f1b3cc1710d508b446fe063ca68d",
        },
    )


def run_family_sweep_6dof(model,speed_range_rad_s:Iterable[float],family:str,library_path=None)->AxialTorsionalSweepResult:
    family_name,_=_family(family)
    speeds=np.asarray(tuple(speed_range_rad_s),dtype=float)
    if speeds.ndim!=1 or len(speeds)<2 or not np.isfinite(speeds).all() or not np.all(np.diff(speeds)>0):
        raise ValueError("speed_range_rad_s must be a finite strictly increasing 1-D grid with >=2 stations")
    points=[run_family_modal_6dof(model,float(w),family_name,library_path) for w in speeds]
    count=len(points[0].wn_rad_s)
    if any(len(p.wn_rad_s)!=count for p in points):
        raise AxialTorsionalError(44,f"{family_name} mode count changed across sweep")
    return AxialTorsionalSweepResult(
        family_name,speeds.copy(),
        np.vstack([p.wn_rad_s for p in points]),
        np.vstack([p.wd_rad_s for p in points]),
        np.vstack([p.damping_ratio for p in points]),
        np.vstack([p.log_dec for p in points]),
        tuple(p.eigenvectors.copy() for p in points),
        np.vstack([p.residual for p in points]),
        np.asarray([p.max_decoupling_ratio for p in points],dtype=float),
        {
            "dof_model":6,
            "family_dof":"z" if family_name=="Axial" else "theta",
            "workflow":"B3_DEDICATED_INVARIANT_SUBSPACE_SWEEP",
            "speed_invariance_expected":True,
            "ross_authority_sha":"6320eab9f890f1b3cc1710d508b446fe063ca68d",
        },
    )


def run_axial_modal_6dof(model,speed_rad_s:float=0.0,library_path=None):
    return run_family_modal_6dof(model,speed_rad_s,"Axial",library_path)


def run_torsional_modal_6dof(model,speed_rad_s:float=0.0,library_path=None):
    return run_family_modal_6dof(model,speed_rad_s,"Torsional",library_path)


def run_axial_sweep_6dof(model,speed_range_rad_s,library_path=None):
    return run_family_sweep_6dof(model,speed_range_rad_s,"Axial",library_path)


def run_torsional_sweep_6dof(model,speed_range_rad_s,library_path=None):
    return run_family_sweep_6dof(model,speed_range_rad_s,"Torsional",library_path)
