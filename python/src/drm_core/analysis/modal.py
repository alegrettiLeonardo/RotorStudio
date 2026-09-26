from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import numpy as np
from drm_core.solver.facade import SolverFacade
from drm_core.domain.bearings import CoefficientBearing
from drm_core.post.whirl import whirl

SYNCHRONOUS_COEFFICIENTS = "SYNCHRONOUS_COEFFICIENTS"
FIXED_WHIRL = "FIXED_WHIRL"
MATCHED_WHIRL = "MATCHED_WHIRL"
_COEFFICIENT_POLICIES = {SYNCHRONOUS_COEFFICIENTS, FIXED_WHIRL, MATCHED_WHIRL}


@dataclass(frozen=True)
class ModalResult:
    speed_rad_s: float
    eigenvalues: np.ndarray
    natural_frequency_hz: np.ndarray
    damping_ratio: np.ndarray
    eigenvectors: np.ndarray|None=None
    kappa: np.ndarray|None=None
    bearing_eccentricity: np.ndarray|None=None
    metadata: dict=field(default_factory=dict)


def modal_assurance_criterion(u, v) -> float:
    """Complex-vector MAC used by B17 inner and outer mode tracking."""
    a=np.asarray(u,dtype=np.complex128).reshape(-1)
    b=np.asarray(v,dtype=np.complex128).reshape(-1)
    den=float(np.vdot(a,a).real*np.vdot(b,b).real)
    if not np.isfinite(den) or den <= np.finfo(float).tiny:
        return 0.0
    value=float(abs(np.vdot(a,b))**2/den)
    return float(max(0.0,min(1.0,value)))


def _kappa(eig,vec):
    if vec is None:return None
    ndof,nmode=vec.shape;out=np.zeros((ndof,nmode),float)
    for j in range(nmode):
        kk,_=whirl(vec[0::2,j],vec[1::2,j])
        if eig[j].imag<0:kk=-kk
        out[0::2,j]=kk;out[1::2,j]=kk
    return out


def _axis_status(axis, value, atol=1e-12):
    axis=np.asarray(axis,dtype=float)
    if axis.size==0:return "CONSTANT"
    if value < axis[0]-atol or value > axis[-1]+atol:return "EXTRAPOLATED"
    if np.any(np.isclose(axis,value,rtol=0.0,atol=atol)):return "TABULATED"
    return "INTERPOLATED"


def _bearing_frequency_status(model, speed, frequency):
    statuses=[]
    for bearing in model.advanced_bearings:
        if isinstance(bearing,CoefficientBearing):
            ss=_axis_status(bearing.speed_rad_s,float(speed))
            fs=_axis_status(bearing.frequency_rad_s,float(frequency))
            source="MAP_BACKED" if dict(bearing.provenance).get("map_contract") else "COEFFICIENT_TABLE"
            statuses.append({"family":bearing.model_family,"source":source,"speed":ss,"frequency":fs})
        else:
            statuses.append({"family":getattr(bearing,"model_family",type(bearing).__name__),"source":"DIRECT_PHYSICAL","speed":"DIRECT","frequency":"DIRECT"})
    return statuses


def _base_metadata(model, policy, **extra):
    return {
        "solver_version":"0.5.0",
        "model_hash":model.model_hash(),
        "timestamp":datetime.now(timezone.utc).isoformat(),
        "backend":"Fortran2018/ctypes",
        "coefficient_policy":policy,
        **extra,
    }


def _result(model, speed, eig, vec, ecc, policy, with_kappa, metadata):
    eig=np.asarray(eig,dtype=np.complex128)
    wn=np.abs(eig)
    hz=wn/(2*np.pi)
    zeta=np.divide(-eig.real,wn,out=np.zeros_like(wn,dtype=float),where=wn!=0)
    kp=_kappa(eig,vec) if with_kappa else None
    return ModalResult(float(speed),eig,hz,zeta,vec,kp,ecc,_base_metadata(model,policy,**metadata))


def _matched_whirl(model,speed,facade,*,whirl_rtol,whirl_max_iter,with_kappa):
    if whirl_rtol <= 0:
        raise ValueError("whirl_rtol must be > 0")
    if int(whirl_max_iter) < 1:
        raise ValueError("whirl_max_iter must be >= 1")
    sync_values,sync_vectors,_=facade.modal_eigensystem_at_frequency(model,speed,speed)
    sync_values=np.asarray(sync_values,dtype=np.complex128)
    sync_vectors=np.asarray(sync_vectors,dtype=np.complex128)
    forward=np.flatnonzero(sync_values.imag >= -1e-12)
    if not forward.size:
        forward=np.arange(sync_values.size)
    nphysical=max(1,sync_values.size//2)
    forward=forward[:nphysical]

    values=np.empty(len(forward),dtype=np.complex128)
    vectors=np.empty((sync_vectors.shape[0],len(forward)),dtype=np.complex128)
    diagnostics=[]
    final_ecc=None
    for out_index,initial_index in enumerate(forward):
        value=sync_values[initial_index]
        vector=sync_vectors[:,initial_index]
        current=max(abs(float(value.imag)),np.finfo(float).eps)
        last_mac=1.0
        converged=False
        iteration=0
        status=[]
        for iteration in range(1,int(whirl_max_iter)+1):
            candidate_values,candidate_vectors,ecc=facade.modal_eigensystem_at_frequency(model,float(speed),float(current))
            candidate_values=np.asarray(candidate_values,dtype=np.complex128)
            candidate_vectors=np.asarray(candidate_vectors,dtype=np.complex128)
            candidates=np.flatnonzero(candidate_values.imag >= -1e-12)
            if not candidates.size:
                candidates=np.arange(candidate_values.size)
            macs=np.asarray([modal_assurance_criterion(vector,candidate_vectors[:,j]) for j in candidates],dtype=float)
            match=int(candidates[int(np.argmax(macs))])
            last_mac=float(np.max(macs))
            value=candidate_values[match]
            vector=candidate_vectors[:,match]
            new_whirl=abs(float(value.imag))
            status=_bearing_frequency_status(model,speed,current)
            converged=abs(new_whirl-current) <= float(whirl_rtol)*max(current,new_whirl,1e-12)
            current=max(new_whirl,np.finfo(float).eps)
            final_ecc=ecc
            if converged:
                break
        values[out_index]=value
        vectors[:,out_index]=vector
        diagnostics.append({
            "mode":out_index+1,
            "iterations":iteration,
            "final_whirl_frequency_rad_s":float(current),
            "last_mac":float(last_mac),
            "converged":bool(converged),
            "coefficient_status":status,
        })
    return _result(
        model,speed,values,vectors,final_ecc,MATCHED_WHIRL,with_kappa,
        {
            "whirl_frequency_rad_s":[d["final_whirl_frequency_rad_s"] for d in diagnostics],
            "matched_whirl":diagnostics,
            "whirl_rtol":float(whirl_rtol),
            "whirl_max_iter":int(whirl_max_iter),
            "ross_authority_sha":"6320eab9f890f1b3cc1710d508b446fe063ca68d",
        },
    )


def run_modal(
    model,
    speed_rad_s:float,
    library_path=None,
    with_eigenvectors:bool=False,
    with_kappa:bool=False,
    coefficient_policy:str=SYNCHRONOUS_COEFFICIENTS,
    whirl_frequency_rad_s:float|None=None,
    whirl_rtol:float=1e-3,
    whirl_max_iter:int=15,
)->ModalResult:
    policy=str(coefficient_policy).upper()
    if policy not in _COEFFICIENT_POLICIES:
        raise ValueError(f"unsupported coefficient_policy={coefficient_policy!r}")
    facade=SolverFacade(library_path)
    speed=float(speed_rad_s)
    if policy==MATCHED_WHIRL:
        return _matched_whirl(model,speed,facade,whirl_rtol=whirl_rtol,whirl_max_iter=whirl_max_iter,with_kappa=with_kappa)
    frequency=speed
    if policy==FIXED_WHIRL:
        if whirl_frequency_rad_s is None or not np.isfinite(float(whirl_frequency_rad_s)):
            raise ValueError("FIXED_WHIRL requires finite whirl_frequency_rad_s")
        frequency=float(whirl_frequency_rad_s)
    if with_eigenvectors or with_kappa:
        eig,vec,ecc=facade.modal_eigensystem_at_frequency(model,speed,frequency)
    else:
        eig=facade.modal_at_frequency(model,speed,frequency);vec=None;ecc=None
    return _result(
        model,speed,eig,vec,ecc,policy,with_kappa,
        {
            "whirl_frequency_rad_s":float(frequency),
            "coefficient_status":_bearing_frequency_status(model,speed,frequency),
            "ross_authority_sha":"6320eab9f890f1b3cc1710d508b446fe063ca68d",
        },
    )


def track_modal_branches(previous:ModalResult, current:ModalResult)->ModalResult:
    """Reorder a Campbell point by global-greedy MAC, never by frequency."""
    if previous.eigenvectors is None or current.eigenvectors is None:
        return current
    a=np.asarray(previous.eigenvectors,dtype=np.complex128)
    b=np.asarray(current.eigenvectors,dtype=np.complex128)
    n=min(a.shape[1],b.shape[1])
    if n<1:return current
    matrix=np.empty((n,n),dtype=float)
    for i in range(n):
        for j in range(n):
            matrix[i,j]=modal_assurance_criterion(a[:,i],b[:,j])
    pairs=[(float(matrix[i,j]),i,j) for i in range(n) for j in range(n)]
    pairs.sort(key=lambda item:(-item[0],item[1],item[2]))
    assigned_prev=set();assigned_cur=set();mapping=[None]*n
    for score,i,j in pairs:
        if i in assigned_prev or j in assigned_cur:continue
        mapping[i]=j;assigned_prev.add(i);assigned_cur.add(j)
        if len(assigned_prev)==n:break
    assigned_order=[j for j in mapping if j is not None]
    used=set(assigned_order)
    order=np.asarray(assigned_order+[j for j in range(b.shape[1]) if j not in used],dtype=int)
    eig=np.asarray(current.eigenvalues)[order]
    vec=np.asarray(current.eigenvectors)[:,order]
    freq=np.asarray(current.natural_frequency_hz)[order]
    damp=np.asarray(current.damping_ratio)[order]
    kp=None if current.kappa is None else np.asarray(current.kappa)[:,order]
    scores=[float(matrix[i,mapping[i]]) for i in range(n) if mapping[i] is not None]
    metadata=dict(current.metadata)
    metadata["campbell_outer_tracking"]={
        "method":"MAC_GLOBAL_GREEDY",
        "minimum_mac":float(min(scores)) if scores else 0.0,
        "mean_mac":float(np.mean(scores)) if scores else 0.0,
        "assignment":[int(x) for x in order[:n]],
    }
    return ModalResult(current.speed_rad_s,eig,freq,damp,vec,kp,current.bearing_eccentricity,metadata)
