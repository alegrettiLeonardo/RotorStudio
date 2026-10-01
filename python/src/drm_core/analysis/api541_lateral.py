"""I11 API 541 lateral-dynamics assessment core for qualified iRdin models.

Native I9 solves remain authoritative for eigenvalues/eigenvectors and
synchronous response. This module performs deterministic modal tracking,
critical-speed intersection detection, separation checks, legacy-response
summaries and support-stiffness sensitivity.

The result is deliberately PARTIAL: the API 541 analytical unbalance case is
a separate qualification gate and is not fabricated from legacy [Desbal].
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
import math
from pathlib import Path
from typing import Iterable

import numpy as np

from drm_core.analysis.irdin_lateral import (
    run_irdin_modal,
    run_irdin_synchronous_sweep,
)

RPM_TO_RAD_S=2.0*math.pi/60.0
RAD_S_TO_RPM=60.0/(2.0*math.pi)


@dataclass(frozen=True)
class API541ModalTracking:
    speed_rad_s: np.ndarray
    frequency_rad_s: np.ndarray
    damping_ratio: np.ndarray
    mac_to_previous: np.ndarray


@dataclass(frozen=True)
class API541CriticalSpeed:
    branch: int
    excitation_order: float
    speed_rad_s: float
    speed_rpm: float
    modal_frequency_rad_s: float
    damping_ratio: float
    mac: float


@dataclass(frozen=True)
class API541SeparationCheck:
    branch: int
    excitation_order: float
    critical_speed_rpm: float
    reference: str
    reference_speed_rpm: tuple[float, float]
    separation_fraction: float
    required_fraction: float
    passed: bool


@dataclass(frozen=True)
class API541ProbePeak:
    probe_index: int
    speed_rad_s: float
    speed_rpm: float
    amplitude_m: float
    phase_rad: float


@dataclass(frozen=True)
class API541SupportSensitivity:
    stiffness_factor: float
    critical_speeds_rpm: tuple[float, ...]


@dataclass(frozen=True)
class API541LateralCoreResult:
    tracking: API541ModalTracking
    critical_speeds: tuple[API541CriticalSpeed, ...]
    separation_checks: tuple[API541SeparationCheck, ...]
    legacy_probe_peaks: tuple[API541ProbePeak, ...]
    support_sensitivity: tuple[API541SupportSensitivity, ...]
    metadata: dict


def _mac(a: np.ndarray,b: np.ndarray) -> float:
    aa=np.vdot(a,a).real
    bb=np.vdot(b,b).real
    if not np.isfinite([aa,bb]).all() or aa<=0.0 or bb<=0.0:
        return 0.0
    value=(abs(np.vdot(a,b))**2)/(aa*bb)
    return float(min(1.0,max(0.0,value)))


def _positive_modes(modal,mode_count:int|None=None):
    eig=np.asarray(modal.eigenvalues,dtype=np.complex128)
    vec=np.asarray(modal.eigenvectors,dtype=np.complex128)
    if vec.ndim!=2 or vec.shape[1]!=eig.size:
        raise ValueError("I11 modal eigenvector/eigenvalue dimensions disagree")
    scale=max(1.0,float(np.max(np.abs(eig))) if eig.size else 1.0)
    tol=128.0*np.finfo(float).eps*scale
    idx=np.flatnonzero(eig.imag>tol)
    if idx.size<1:
        raise ValueError("I11 found no positive-frequency damped modes")
    idx=idx[np.argsort(np.abs(eig[idx].imag),kind="stable")]
    if mode_count is not None:
        if mode_count<1:
            raise ValueError("mode_count must be >= 1")
        idx=idx[:min(int(mode_count),idx.size)]
    lam=eig[idx]
    freq=np.abs(lam.imag)
    mag=np.abs(lam)
    zeta=np.divide(-lam.real,mag,out=np.zeros_like(freq),where=mag>0)
    return idx,freq,zeta,vec[:,idx]


def track_modal_sweep(project,speeds_rad_s,*,mode_count:int=9,library_path:str|Path|None=None):
    speeds=np.asarray(speeds_rad_s,dtype=np.float64)
    if speeds.ndim!=1 or speeds.size<2 or not np.isfinite(speeds).all():
        raise ValueError("I11 modal tracking requires at least two finite speed points")
    if np.any(speeds<0.0) or np.any(np.diff(speeds)<=0.0):
        raise ValueError("I11 modal tracking speeds must be strictly increasing and nonnegative")

    points=[]
    for speed in speeds:
        modal=run_irdin_modal(project,float(speed),library_path=library_path)
        points.append(_positive_modes(modal,None))

    branches=min(int(mode_count),min(len(p[0]) for p in points))
    if branches<1:
        raise ValueError("I11 modal tracking has no common branches")

    freq=np.empty((branches,speeds.size),dtype=float)
    damp=np.empty_like(freq)
    mac=np.ones_like(freq)

    _idx,f0,z0,v0=points[0]
    freq[:,0]=f0[:branches];damp[:,0]=z0[:branches]
    prev=v0[:,:branches]

    for j in range(1,speeds.size):
        _idx,fc,zc,vc=points[j]
        available=set(range(fc.size))
        selected=[]
        selected_mac=[]
        for branch in range(branches):
            scores=[]
            for candidate in available:
                score=_mac(prev[:,branch],vc[:,candidate])
                distance=abs(fc[candidate]-freq[branch,j-1])
                scores.append((score,-distance,-candidate,candidate))
            if not scores:
                raise ValueError("I11 lost a modal branch during tracking")
            best=max(scores)[3]
            selected.append(best)
            selected_mac.append(_mac(prev[:,branch],vc[:,best]))
            available.remove(best)
        selected=np.asarray(selected,dtype=int)
        freq[:,j]=fc[selected];damp[:,j]=zc[selected];mac[:,j]=selected_mac
        prev=vc[:,selected]

    return API541ModalTracking(speeds.copy(),freq,damp,mac)


def critical_crossings(tracking:API541ModalTracking,*,excitation_orders:Iterable[float]=(1.0,)):
    speed=np.asarray(tracking.speed_rad_s,float)
    out=[]
    for order_raw in excitation_orders:
        order=float(order_raw)
        if not math.isfinite(order) or order<=0.0:
            raise ValueError("excitation orders must be finite and > 0")
        for b in range(tracking.frequency_rad_s.shape[0]):
            residual=tracking.frequency_rad_s[b]-order*speed
            candidates=[]
            for i in range(speed.size-1):
                r0=float(residual[i]);r1=float(residual[i+1])
                if r0==0.0 and speed[i]>0.0:
                    x=float(speed[i]);alpha=0.0
                elif r0*r1<0.0:
                    alpha=-r0/(r1-r0)
                    x=float(speed[i]+alpha*(speed[i+1]-speed[i]))
                else:
                    continue
                if x<=0.0:
                    continue
                z=float(tracking.damping_ratio[b,i]+alpha*(tracking.damping_ratio[b,i+1]-tracking.damping_ratio[b,i]))
                m=float(tracking.mac_to_previous[b,i]+alpha*(tracking.mac_to_previous[b,i+1]-tracking.mac_to_previous[b,i]))
                candidates.append(API541CriticalSpeed(
                    b+1,order,x,x*RAD_S_TO_RPM,order*x,z,m,
                ))
            for item in candidates:
                if not any(abs(item.speed_rad_s-prev.speed_rad_s)<=1e-9*max(1.0,item.speed_rad_s)
                           and item.branch==prev.branch and item.excitation_order==prev.excitation_order
                           for prev in out):
                    out.append(item)
    return tuple(sorted(out,key=lambda x:(x.speed_rad_s,x.excitation_order,x.branch)))


def separation_checks(criticals,*,required_fraction:float=0.15,
                      operating_speed_rad_s:float|None=None,
                      operating_range_rad_s:tuple[float,float]|None=None):
    req=float(required_fraction)
    if not math.isfinite(req) or req<0.0:
        raise ValueError("required separation fraction must be finite and >= 0")
    if (operating_speed_rad_s is None)==(operating_range_rad_s is None):
        raise ValueError("provide exactly one of operating_speed_rad_s or operating_range_rad_s")
    if operating_speed_rad_s is not None:
        lo=hi=float(operating_speed_rad_s)
        if not math.isfinite(lo) or lo<=0.0:
            raise ValueError("operating speed must be finite and > 0")
        reference="FIXED_SPEED"
    else:
        lo,hi=map(float,operating_range_rad_s)
        if not np.isfinite([lo,hi]).all() or lo<=0.0 or hi<lo:
            raise ValueError("operating range must satisfy 0 < min <= max")
        reference="SPEED_RANGE"
    out=[]
    for critical in criticals:
        c=float(critical.speed_rad_s)
        if lo<=c<=hi:
            margin=0.0
        elif c<lo:
            margin=(lo-c)/lo
        else:
            margin=(c-hi)/hi
        out.append(API541SeparationCheck(
            critical.branch,critical.excitation_order,critical.speed_rpm,
            reference,(lo*RAD_S_TO_RPM,hi*RAD_S_TO_RPM),
            float(margin),req,bool(margin+32*np.finfo(float).eps>=req),
        ))
    return tuple(out)


def _scaled_support_project(project,factor:float):
    f=float(factor)
    if not math.isfinite(f) or f<=0.0:
        raise ValueError("support stiffness factors must be finite and > 0")
    q=deepcopy(project)
    q.model.supports=[
        replace(
            s,
            kxx_n_m=s.kxx_n_m*f,
            kxy_n_m=s.kxy_n_m*f,
            kyx_n_m=s.kyx_n_m*f,
            kyy_n_m=s.kyy_n_m*f,
            provenance=dict(s.provenance)|{"api541_support_stiffness_factor":f},
        )
        for s in q.model.supports
    ]
    return q


def support_sensitivity(project,speeds_rad_s,*,mode_count:int,excitation_orders=(1.0,),
                        factors=(0.5,0.75,1.0,1.25,1.5),library_path:str|Path|None=None):
    result=[]
    for factor in factors:
        q=_scaled_support_project(project,float(factor))
        tracking=track_modal_sweep(q,speeds_rad_s,mode_count=mode_count,library_path=library_path)
        critical=critical_crossings(tracking,excitation_orders=excitation_orders)
        result.append(API541SupportSensitivity(
            float(factor),tuple(float(x.speed_rpm) for x in critical)
        ))
    return tuple(result)


def legacy_probe_peaks(project,speeds_rad_s,*,library_path:str|Path|None=None):
    sweep=run_irdin_synchronous_sweep(project,speeds_rad_s,library_path=library_path)
    peaks=[]
    for i,row in enumerate(np.asarray(sweep.probe_response),start=1):
        amp=np.abs(row)
        j=int(np.argmax(amp))
        peaks.append(API541ProbePeak(
            i,float(sweep.speed_rad_s[j]),float(sweep.speed_rad_s[j]*RAD_S_TO_RPM),
            float(amp[j]),float(np.angle(row[j])),
        ))
    return tuple(peaks)


def run_api541_lateral_core(project,*,campbell_speeds_rad_s,response_speeds_rad_s,
                            mode_count:int=9,excitation_orders=(1.0,),
                            required_separation_fraction:float=0.15,
                            operating_speed_rad_s:float|None=None,
                            operating_range_rad_s:tuple[float,float]|None=None,
                            support_stiffness_factors=(0.5,0.75,1.0,1.25,1.5),
                            library_path:str|Path|None=None):
    tracking=track_modal_sweep(project,campbell_speeds_rad_s,mode_count=mode_count,library_path=library_path)
    critical=critical_crossings(tracking,excitation_orders=excitation_orders)
    checks=separation_checks(
        critical,
        required_fraction=required_separation_fraction,
        operating_speed_rad_s=operating_speed_rad_s,
        operating_range_rad_s=operating_range_rad_s,
    )
    peaks=legacy_probe_peaks(project,response_speeds_rad_s,library_path=library_path)
    sensitivity=support_sensitivity(
        project,campbell_speeds_rad_s,mode_count=mode_count,
        excitation_orders=excitation_orders,factors=support_stiffness_factors,
        library_path=library_path,
    )
    return API541LateralCoreResult(
        tracking,critical,checks,peaks,sensitivity,
        {
            "status":"PASS_I11_API541_LATERAL_CORE",
            "scope":"API 541 lateral dynamics assessment core for declared imported iRdin scope",
            "required_separation_fraction":float(required_separation_fraction),
            "excitation_orders":[float(x) for x in excitation_orders],
            "legacy_unbalance_response_only":True,
            "api541_analytical_unbalance_qualified":False,
            "support_sensitivity_is_engineering_study":True,
            "full_api541_compliance_claim":False,
        },
    )


__all__=[
    "RPM_TO_RAD_S","RAD_S_TO_RPM","API541ModalTracking","API541CriticalSpeed",
    "API541SeparationCheck","API541ProbePeak","API541SupportSensitivity",
    "API541LateralCoreResult","track_modal_sweep","critical_crossings",
    "separation_checks","support_sensitivity","legacy_probe_peaks",
    "run_api541_lateral_core",
]
