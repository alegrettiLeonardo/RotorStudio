"""C1 thin native adapter for ROSS-derived 6-DOF misalignment dynamics.

All fault-force evaluation and Newmark integration remain in Fortran. Python
performs declared-scope validation, B2 descriptor mapping, ABI buffer
allocation and typed result construction only.
"""
from __future__ import annotations
import ctypes as ct
from dataclasses import dataclass
from typing import Iterable
import numpy as np

from .ffi import SolverLibraryError, load_library
from .sixdof_global import _descriptors, _finite_real, _ptr, NODE_DOF_ORDER

ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"
STATUS={
    0:"SUCCESS",50:"INVALID_INPUT",51:"UNSUPPORTED",52:"B2_ASSEMBLY_FAILURE",
    53:"NEWMARK_FAILURE",54:"NONFINITE_RESULT",
    20:"B2_INVALID_INPUT",21:"B2_INVALID_DIMENSION",22:"B2_UNSUPPORTED",
    23:"B2_SINGULAR_MASS",24:"B2_LAPACK_FAILURE",25:"B2_INSUFFICIENT_CAPACITY",
    26:"B2_NONFINITE_RESULT",27:"B2_ELEMENT_FAILURE",
}
COUPLING={"flex":1,"rigid":2}
MIS_TYPE={"parallel":1,"angular":2,"combined":3}


class MisalignmentError(RuntimeError):
    def __init__(self,status:int,context:str,failed_step:int=0):
        self.status=int(status);self.failed_step=int(failed_step)
        suffix=f" at one-based time step {failed_step}" if failed_step else ""
        super().__init__(
            f"C1 {STATUS.get(self.status,'UNKNOWN_STATUS')} ({self.status}){suffix}: "
            f"{context}. No Python numerical fallback was used."
        )


@dataclass(frozen=True)
class MisalignmentResult:
    time_s:np.ndarray
    speed_rad_s:float
    angle_rad:np.ndarray
    force_unbalance:np.ndarray
    force_misalignment:np.ndarray
    force_total:np.ndarray
    displacement:np.ndarray
    velocity:np.ndarray
    acceleration:np.ndarray
    iterations:np.ndarray
    residual:np.ndarray
    absolute_residual:np.ndarray
    condition_estimate:np.ndarray
    rigid_parameters:np.ndarray
    coupling:str
    mis_type:str|None
    shaft_index:int
    metadata:dict


def _native(library_path=None):
    lib=load_library(library_path)
    I,D=ct.c_int,ct.c_double
    IP,P=ct.POINTER(I),ct.POINTER(D)
    try:
        req=lib.rd_misalignment_required_v1
        fn=lib.rd_misalignment_response_v1
    except AttributeError as exc:
        raise SolverLibraryError(
            "C1 requires rd_misalignment_required_v1 and "
            "rd_misalignment_response_v1. Rebuild the C1 native library; "
            "no fallback is available."
        ) from exc
    req.argtypes=[I,I,IP,IP];req.restype=I
    fn.argtypes=[
        I,I,IP,P,IP,I,IP,P,I,IP,P,
        I,I,I,D,D,D,D,D,D,D,D,
        I,IP,P,P,I,P,D,D,D,D,I,I,
        P,P,P,P,P,P,P,IP,P,P,P,IP,P,
    ]
    fn.restype=I
    return req,fn


def _status(code:int,context:str,failed_step:int=0)->None:
    if int(code):
        raise MisalignmentError(int(code),context,failed_step)


def _float_array(name:str,value:Iterable[float],*,minimum_size:int=1)->np.ndarray:
    a=np.asarray(tuple(value),dtype=np.float64)
    if a.ndim!=1 or len(a)<minimum_size or not np.isfinite(a).all():
        raise ValueError(f"{name} must be a finite 1-D array with >= {minimum_size} entries")
    return np.ascontiguousarray(a)


def _int_array(name:str,value:Iterable[int])->np.ndarray:
    raw=tuple(value)
    if any(isinstance(x,bool) or int(x)!=x for x in raw):
        raise ValueError(f"{name} must contain integer node numbers")
    return np.ascontiguousarray(raw,dtype=np.int32)


def run_misalignment_6dof(
    model,
    *,
    coupling:str,
    shaft_index:int,
    time_s,
    speed_rad_s:float,
    unbalance_nodes=(),
    unbalance_magnitude_kg_m=(),
    unbalance_phase_rad=(),
    mis_type:str|None=None,
    mis_distance_x_m:float=0.0,
    mis_distance_y_m:float=0.0,
    mis_angle_rad:float=0.0,
    radial_stiffness_n_m:float=0.0,
    bending_stiffness_n:float=0.0,
    mis_distance_m:float=0.0,
    input_torque_nm:float=0.0,
    load_torque_nm:float=0.0,
    gamma:float=0.5,
    beta:float=0.25,
    tol:float=1e-9,
    library_path=None,
)->MisalignmentResult:
    coupling=str(coupling).strip().lower()
    if coupling not in COUPLING:
        raise ValueError("coupling must be 'flex' or 'rigid'")
    if isinstance(shaft_index,bool) or int(shaft_index)!=shaft_index:
        raise ValueError("shaft_index must be a zero-based integer")
    shaft_index=int(shaft_index)
    if not 0<=shaft_index<len(model.shafts):
        raise ValueError(f"shaft_index={shaft_index} outside 0..{len(model.shafts)-1}")

    speed=_finite_real("speed_rad_s",speed_rad_s)
    t=_float_array("time_s",time_s,minimum_size=2)
    if np.any(np.diff(t)<=0):
        raise ValueError("time_s must be strictly increasing")
    gamma=_finite_real("gamma",gamma);beta=_finite_real("beta",beta);tol=_finite_real("tol",tol)
    if gamma<=0 or beta<=0 or tol<=0:
        raise ValueError("gamma, beta and tol must be positive")

    nodes=_int_array("unbalance_nodes",unbalance_nodes)
    mag=_float_array("unbalance_magnitude_kg_m",unbalance_magnitude_kg_m,minimum_size=0)
    phase=_float_array("unbalance_phase_rad",unbalance_phase_rad,minimum_size=0)
    if not (len(nodes)==len(mag)==len(phase)):
        raise ValueError("unbalance_nodes, unbalance_magnitude_kg_m and unbalance_phase_rad must have equal length")
    valid_nodes={int(n.number) for n in model.nodes}
    if any(int(n) not in valid_nodes for n in nodes):
        raise ValueError("unbalance_nodes contains a node not present in the RotorStudio model")
    if np.any(mag<0):
        raise ValueError("unbalance magnitudes must be non-negative")

    values={
        "mis_distance_x_m":mis_distance_x_m,"mis_distance_y_m":mis_distance_y_m,
        "mis_angle_rad":mis_angle_rad,"radial_stiffness_n_m":radial_stiffness_n_m,
        "bending_stiffness_n":bending_stiffness_n,"mis_distance_m":mis_distance_m,
        "input_torque_nm":input_torque_nm,"load_torque_nm":load_torque_nm,
    }
    values={k:_finite_real(k,v) for k,v in values.items()}
    if values["radial_stiffness_n_m"]<0 or values["bending_stiffness_n"]<0 or values["mis_distance_m"]<0:
        raise ValueError("misalignment stiffnesses and rigid mis_distance_m must be non-negative")

    if coupling=="flex":
        mt=str(mis_type).strip().lower()
        if mt not in MIS_TYPE:
            raise ValueError("flex mis_type must be 'parallel', 'angular' or 'combined'")
        if mt in {"parallel","combined"} and values["mis_distance_y_m"]==0.0:
            raise ValueError("ROSS parallel formula requires nonzero mis_distance_y_m")
        mis_code=MIS_TYPE[mt]
    else:
        if mis_type not in (None,"",0):
            raise ValueError("rigid coupling does not accept a flex mis_type")
        mt=None;mis_code=0

    nn,ns,sn,sp,sf,nd,dn,dp,nb,bn,bp=_descriptors(model,speed,speed,library_path)
    req,fn=_native(library_path)
    ndof=ct.c_int();history=ct.c_int()
    _status(req(nn,len(t),ct.byref(ndof),ct.byref(history)),"misalignment size query")
    n=ndof.value;nt=len(t)
    if history.value!=n*nt:
        raise MisalignmentError(50,f"native size query returned history={history.value}, expected {n*nt}")

    def hist():
        return np.full((n,nt),np.nan,dtype=np.float64,order="F")
    q,v,a,funb,fmis,ftotal=(hist() for _ in range(6))
    theta=np.full(nt,np.nan,dtype=np.float64)
    iterations=np.full(nt,-1,dtype=np.int32)
    residual=np.full(nt,np.nan);absres=np.full(nt,np.nan);condition=np.full(nt,np.nan)
    rigid=np.full(4,np.nan)
    failed=ct.c_int()

    # Empty unbalance inputs still provide valid non-null one-element ABI buffers.
    ub_nodes=nodes if len(nodes) else np.zeros(1,dtype=np.int32)
    ub_mag=mag if len(mag) else np.zeros(1,dtype=np.float64)
    ub_phase=phase if len(phase) else np.zeros(1,dtype=np.float64)

    code=fn(
        nn,ns,_ptr(sn),_ptr(sp),_ptr(sf),nd,_ptr(dn),_ptr(dp),nb,_ptr(bn),_ptr(bp),
        COUPLING[coupling],mis_code,shaft_index+1,
        values["mis_distance_x_m"],values["mis_distance_y_m"],values["mis_angle_rad"],
        values["radial_stiffness_n_m"],values["bending_stiffness_n"],values["mis_distance_m"],
        values["input_torque_nm"],values["load_torque_nm"],
        len(nodes),_ptr(ub_nodes),_ptr(ub_mag),_ptr(ub_phase),
        nt,_ptr(t),speed,gamma,beta,tol,history.value,nt,
        _ptr(q),_ptr(v),_ptr(a),_ptr(theta),_ptr(funb),_ptr(fmis),_ptr(ftotal),
        _ptr(iterations),_ptr(residual),_ptr(absres),_ptr(condition),ct.byref(failed),_ptr(rigid),
    )
    _status(code,f"{coupling} misalignment transient",failed.value)
    arrays=(q,v,a,theta,funb,fmis,ftotal,residual,absres,condition)
    if not all(np.isfinite(x).all() for x in arrays):
        raise MisalignmentError(54,"native result contains non-finite values",failed.value)
    if coupling=="flex":
        rigid=np.full(4,np.nan)

    return MisalignmentResult(
        t.copy(),speed,theta.copy(),funb.copy(order="F"),fmis.copy(order="F"),ftotal.copy(order="F"),
        q.copy(order="F"),v.copy(order="F"),a.copy(order="F"),iterations.copy(),
        residual.copy(),absres.copy(),condition.copy(),rigid.copy(),
        coupling,mt,shaft_index,
        {
            "dof_model":6,
            "node_dof_order":NODE_DOF_ORDER,
            "node_numbers":tuple(int(n.number) for n in model.nodes),
            "native_abi":"rd_misalignment_response_v1",
            "backend":"Fortran2018/ctypes",
            "ross_authority_sha":ROSS_SHA,
            "ross_source":"ross/faults/misalignment.py",
            "workflow":"C1_MISALIGNMENT_FULL_ORDER_6DOF",
            "newmark_type":"simple",
            "gamma":gamma,"beta":beta,"tol":tol,
            "speed_policy":"CONSTANT",
            "model_reduction":False,
            "initial_state":"q0=v0=a0=0",
            "python_numerical_fallback":False,
        },
    )


def node_orbit(result:MisalignmentResult,node_number:int)->np.ndarray:
    nodes=tuple(result.metadata["node_numbers"])
    if int(node_number) not in nodes:
        raise ValueError("node_number not present in result model")
    i=nodes.index(int(node_number));j=6*i
    return np.vstack((result.displacement[j],result.displacement[j+1]))


def response_dfft(result:MisalignmentResult,node_number:int,direction:str="x")->tuple[np.ndarray,np.ndarray]:
    direction=str(direction).lower()
    offset={"x":0,"y":1,"z":2,"alpha":3,"beta":4,"theta":5}.get(direction)
    if offset is None:
        raise ValueError("direction must be x, y, z, alpha, beta or theta")
    nodes=tuple(result.metadata["node_numbers"])
    if int(node_number) not in nodes:
        raise ValueError("node_number not present in result model")
    t=np.asarray(result.time_s,float);dt=np.diff(t)
    if not np.allclose(dt,dt[0],rtol=1e-12,atol=0):
        raise ValueError("DFFT requires a uniform time grid; no implicit resampling is performed")
    i=nodes.index(int(node_number));x=np.asarray(result.displacement[6*i+offset],float)
    amp=np.abs(np.fft.rfft(x))/len(x)
    if len(amp)>1:
        amp[1:]*=2.0
        if len(x)%2==0:
            amp[-1]/=2.0
    return np.fft.rfftfreq(len(x),dt[0]),amp
