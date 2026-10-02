"""I12 API 541 analytical unbalance for the qualified iRdin lateral path.

The dynamic solve remains in the native I9 expanded rotor-bearing-support
solver. This module only derives the API 541 input-unbalance arrangement,
applies it to a temporary project, and scales it by linear response.

Declared source contract (API 541, Third Edition, 1995, lateral dynamic
analysis):
- SI baseline input unbalance: U = 6350 W / N [g.mm];
- analytical response input is no less than two times that value;
- W is journal static weight load [kg], or applicable overhung load;
- N is the operating speed nearest the critical of concern [rpm];
- the unbalance location(s) shall excite the particular mode most adversely;
- the input shall be sufficient to raise predicted probe motion to the
  vibration limit Lv = 25.4*sqrt(12000/N) micrometres peak-to-peak.

Initial I12 scope is exactly-two-support imported rotors. Journal static loads
are obtained from mass and first-moment equilibrium of the qualified shaft and
I7 disk mass distribution. No generic multi-support load allocation is
silently inferred.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
import math
from pathlib import Path
from typing import Mapping

import numpy as np

from drm_core.domain.model import (
    Disk,
    Force,
    RotorModel,
    ShaftElement,
    TaperedShaftElement,
)
from drm_core.analysis.irdin_lateral import run_irdin_modal,run_irdin_synchronous,probe_value
from drm_core.analysis.api541_lateral import API541CriticalSpeed,RAD_S_TO_RPM


@dataclass(frozen=True)
class API541JournalLoad:
    support_index:int
    node:int
    z_m:float
    static_load_kg:float


@dataclass(frozen=True)
class API541AnalyticalPlane:
    node:int
    z_m:float
    journal_load_kg:float
    minimum_unbalance_g_mm:float
    applied_unbalance_g_mm:float
    phase_rad:float


@dataclass(frozen=True)
class API541AnalyticalUnbalanceResult:
    critical:API541CriticalSpeed
    mode_kind:str
    reference_speed_rpm:float
    vibration_limit_pp_m:float
    journal_loads:tuple[API541JournalLoad,...]
    planes:tuple[API541AnalyticalPlane,...]
    scale_factor:float
    probe_response:np.ndarray
    max_probe_pp_m:float
    metadata:dict


def _shaft_mass_centroid(model:RotorModel):
    z={int(n.number):float(n.z_m) for n in model.nodes}
    out=[]
    for s in model.shafts:
        z0=z[int(s.node1)];z1=z[int(s.node2)]
        if z1<=z0:
            raise ValueError("I12 requires monotonically increasing shaft stations")
        L=z1-z0
        if isinstance(s,ShaftElement):
            area=math.pi/4.0*(s.outer_diameter_m**2-s.inner_diameter_m**2)
            mass=float(s.rho_kg_m3*area*L)
            out.append((mass,0.5*(z0+z1)))
            continue
        if isinstance(s,TaperedShaftElement):
            do0=float(s.outer_diameter_1_m);do1=float(s.outer_diameter_2_m)
            di0=float(s.inner_diameter_1_m);di1=float(s.inner_diameter_2_m)
            ao=(do1-do0)/L;ai=(di1-di0)/L
            c0=do0*do0-di0*di0
            c1=2.0*(do0*ao-di0*ai)
            c2=ao*ao-ai*ai
            integ=c0*L+c1*L*L/2.0+c2*L**3/3.0
            first=c0*L*L/2.0+c1*L**3/3.0+c2*L**4/4.0
            if integ<=0.0:
                raise ValueError("I12 found nonpositive tapered-shaft area integral")
            mass=float(s.rho_kg_m3*math.pi/4.0*integ)
            out.append((mass,z0+first/integ))
            continue
        raise ValueError(f"I12 imported scope does not qualify shaft type {type(s).__name__}")
    return out


def _disk_mass_centroid(model:RotorModel):
    z={int(n.number):float(n.z_m) for n in model.nodes}
    out=[]
    for d in model.disks:
        if int(d.node) not in z:
            raise ValueError("I12 disk references a missing node")
        if int(d.disk_type)==2:
            mass=float(d.p3)
        elif int(d.disk_type)==1:
            rho=float(d.p3);L=float(d.p4);do=float(d.p5);di=float(d.p6)
            mass=rho*math.pi/4.0*(do*do-di*di)*L
        else:
            raise ValueError(
                f"I12 initial static-load audit qualifies disk types 1/2; received {d.disk_type}"
            )
        if not math.isfinite(mass) or mass<0.0:
            raise ValueError("I12 disk mass must be finite and nonnegative")
        out.append((mass,z[int(d.node)]))
    return out


def journal_static_loads_kg(project)->tuple[API541JournalLoad,...]:
    supports=list(project.model.supports)
    if len(supports)!=2:
        raise ValueError("I12 initial API 541 journal-load rule requires exactly two supports")
    z={int(n.number):float(n.z_m) for n in project.model.nodes}
    ordered=sorted(enumerate(supports,1),key=lambda item:z[int(item[1].node)])
    (i1,s1),(i2,s2)=ordered
    z1=z[int(s1.node)];z2=z[int(s2.node)]
    if not z2>z1:
        raise ValueError("I12 support stations must be distinct")

    masses=_shaft_mass_centroid(project.model)+_disk_mass_centroid(project.model)
    total=sum(m for m,_ in masses)
    moment=sum(m*(zz-z1) for m,zz in masses)
    if not math.isfinite(total) or total<=0.0:
        raise ValueError("I12 modeled rotor mass must be finite and positive")
    right=moment/(z2-z1)
    left=total-right
    if not np.isfinite([left,right]).all() or left<=0.0 or right<=0.0:
        raise ValueError(
            "I12 two-support equilibrium produced nonpositive journal load; "
            "explicit qualified loads are required for this geometry"
        )
    return (
        API541JournalLoad(i1,int(s1.node),z1,float(left)),
        API541JournalLoad(i2,int(s2.node),z2,float(right)),
    )


def reference_operating_speed_rpm(critical_speed_rpm:float,*,
                                  operating_speed_rpm:float|None=None,
                                  operating_range_rpm:tuple[float,float]|None=None)->float:
    if (operating_speed_rpm is None)==(operating_range_rpm is None):
        raise ValueError("provide exactly one operating speed reference")
    c=float(critical_speed_rpm)
    if not math.isfinite(c) or c<=0.0:
        raise ValueError("critical speed must be finite and > 0")
    if operating_speed_rpm is not None:
        n=float(operating_speed_rpm)
        if not math.isfinite(n) or n<=0.0: raise ValueError("operating speed must be > 0")
        return n
    lo,hi=map(float,operating_range_rpm)
    if not np.isfinite([lo,hi]).all() or lo<=0.0 or hi<lo:
        raise ValueError("operating range must satisfy 0 < min <= max")
    return float(min(max(c,lo),hi))


def api541_vibration_limit_pp_m(reference_speed_rpm:float)->float:
    n=float(reference_speed_rpm)
    if not math.isfinite(n) or n<=0.0:
        raise ValueError("reference speed must be finite and > 0")
    return float(25.4*math.sqrt(12000.0/n)*1.0e-6)


def api541_minimum_analytical_unbalance_g_mm(static_load_kg:float,reference_speed_rpm:float)->float:
    w=float(static_load_kg);n=float(reference_speed_rpm)
    if not math.isfinite(w) or w<=0.0 or not math.isfinite(n) or n<=0.0:
        raise ValueError("journal load and reference speed must be finite and > 0")
    return float(2.0*6350.0*w/n)


def _positive_mode_at(project,critical:API541CriticalSpeed,*,library_path=None):
    modal=run_irdin_modal(project,float(critical.speed_rad_s),library_path=library_path)
    eig=np.asarray(modal.eigenvalues,dtype=np.complex128)
    vec=np.asarray(modal.eigenvectors,dtype=np.complex128)
    idx=np.flatnonzero(eig.imag>128*np.finfo(float).eps*max(1.0,float(np.max(np.abs(eig)))))
    if idx.size<1: raise ValueError("I12 found no positive-frequency modes")
    freq=np.abs(eig[idx].imag)
    pick=int(idx[np.argmin(np.abs(freq-float(critical.modal_frequency_rad_s)))])
    return vec[:,pick]


def classify_mode(project,vector,*,override:str|None=None)->str:
    if override is not None:
        value=str(override).strip().upper()
        if value not in {"TRANSLATORY","CONICAL"}:
            raise ValueError("I12 mode override must be TRANSLATORY or CONICAL")
        return value
    loads=journal_static_loads_kg(project)
    v=np.asarray(vector,dtype=np.complex128)
    a=[];b=[]
    for dof in (0,1):
        a.append(v[4*loads[0].node-4+dof])
        b.append(v[4*loads[1].node-4+dof])
    score=[min(abs(a[i]),abs(b[i])) for i in range(2)]
    axis=int(np.argmax(score))
    if score[axis]<=128*np.finfo(float).eps*max(1.0,float(np.max(np.abs(v)))):
        raise ValueError("I12 cannot classify mode from negligible journal displacement")
    phase=float(np.angle(b[axis]/a[axis]))
    cosine=math.cos(phase)
    if abs(cosine)<0.25:
        raise ValueError("I12 automatic translatory/conical classification is ambiguous; provide override")
    return "TRANSLATORY" if cosine>0.0 else "CONICAL"


def _radial_amplitude(vector,nnode:int):
    v=np.asarray(vector,dtype=np.complex128)
    return np.asarray([
        math.hypot(abs(v[4*i]),abs(v[4*i+1])) for i in range(nnode)
    ],dtype=float)


def _planes(project,critical,vector,mode_kind,reference_rpm):
    loads=journal_static_loads_kg(project)
    z=np.asarray([float(n.z_m) for n in project.model.nodes])
    amp=_radial_amplitude(vector,len(project.model.nodes))
    if mode_kind=="TRANSLATORY":
        node=int(np.argmax(amp))+1
        w=sum(x.static_load_kg for x in loads)
        u=api541_minimum_analytical_unbalance_g_mm(w,reference_rpm)
        return [API541AnalyticalPlane(node,float(z[node-1]),float(w),u,u,0.0)]
    midpoint=0.5*(loads[0].z_m+loads[1].z_m)
    left=np.flatnonzero(z<=midpoint);right=np.flatnonzero(z>=midpoint)
    if left.size<1 or right.size<1: raise ValueError("I12 cannot form conical placement regions")
    n1=int(left[np.argmax(amp[left])])+1
    n2=int(right[np.argmax(amp[right])])+1
    if n1==n2: raise ValueError("I12 conical planes collapsed to one node")
    u1=api541_minimum_analytical_unbalance_g_mm(loads[0].static_load_kg,reference_rpm)
    u2=api541_minimum_analytical_unbalance_g_mm(loads[1].static_load_kg,reference_rpm)
    return [
        API541AnalyticalPlane(n1,float(z[n1-1]),loads[0].static_load_kg,u1,u1,0.0),
        API541AnalyticalPlane(n2,float(z[n2-1]),loads[1].static_load_kg,u2,u2,math.pi),
    ]


def _solve_with_planes(project,critical,planes,*,library_path=None):
    q=deepcopy(project)
    q.model.forces=[
        Force(1,(float(p.node),float(p.applied_unbalance_g_mm)*1.0e-6,float(p.phase_rad)))
        for p in planes
    ]
    solved=run_irdin_synchronous(q,float(critical.speed_rad_s),library_path=library_path)
    probes=np.asarray([probe_value(solved.response,p) for p in q.model.probes],dtype=np.complex128)
    if probes.size<1 or not np.isfinite(probes.real).all() or not np.isfinite(probes.imag).all():
        raise ValueError("I12 requires finite response at at least one qualified probe")
    return probes


def analytical_unbalance_case(project,critical:API541CriticalSpeed,*,
                              operating_speed_rpm:float|None=None,
                              operating_range_rpm:tuple[float,float]|None=None,
                              mode_override:str|None=None,
                              library_path:str|Path|None=None)->API541AnalyticalUnbalanceResult:
    reference=reference_operating_speed_rpm(
        critical.speed_rpm,
        operating_speed_rpm=operating_speed_rpm,
        operating_range_rpm=operating_range_rpm,
    )
    loads=journal_static_loads_kg(project)
    vector=_positive_mode_at(project,critical,library_path=library_path)
    kind=classify_mode(project,vector,override=mode_override)
    minimum=_planes(project,critical,vector,kind,reference)
    probe0=_solve_with_planes(project,critical,minimum,library_path=library_path)
    pp0=2.0*np.abs(probe0)
    current=float(np.max(pp0))
    target=api541_vibration_limit_pp_m(reference)
    if not math.isfinite(current) or current<=0.0:
        raise ValueError("I12 analytical minimum unbalance produced zero/nonfinite probe response")
    scale=max(1.0,target/current)
    applied=[replace(p,applied_unbalance_g_mm=p.minimum_unbalance_g_mm*scale) for p in minimum]
    probe=_solve_with_planes(project,critical,applied,library_path=library_path)
    max_pp=float(np.max(2.0*np.abs(probe)))
    if max_pp+256*np.finfo(float).eps*max(1.0,target)<target:
        raise RuntimeError("I12 scaled analytical unbalance did not reach the API 541 vibration limit")
    return API541AnalyticalUnbalanceResult(
        critical,kind,reference,target,loads,tuple(applied),float(scale),probe,max_pp,
        {
            "status":"PASS_I12_API541_ANALYTICAL_UNBALANCE",
            "source_edition":"API 541 Third Edition 1995",
            "minimum_rule":"2 * (6350 W / N) g.mm",
            "vibration_limit_rule":"25.4 * sqrt(12000 / N) micrometres peak-to-peak",
            "journal_load_source":"TWO_SUPPORT_STATIC_MASS_AND_FIRST_MOMENT_EQUILIBRIUM",
            "dynamic_solver":"I9_NATIVE_EXPANDED_SYNCHRONOUS_RESPONSE",
            "persisted_project_mutated":False,
            "full_api541_compliance_claim":False,
        },
    )


def run_api541_analytical_unbalance(project,criticals,*,
                                    operating_speed_rpm:float|None=None,
                                    operating_range_rpm:tuple[float,float]|None=None,
                                    mode_overrides:Mapping[int,str]|None=None,
                                    library_path:str|Path|None=None):
    overrides=dict(mode_overrides or {})
    return tuple(
        analytical_unbalance_case(
            project,c,
            operating_speed_rpm=operating_speed_rpm,
            operating_range_rpm=operating_range_rpm,
            mode_override=overrides.get(int(c.branch)),
            library_path=library_path,
        )
        for c in criticals
    )


__all__=[
    "API541JournalLoad","API541AnalyticalPlane","API541AnalyticalUnbalanceResult",
    "journal_static_loads_kg","reference_operating_speed_rpm",
    "api541_vibration_limit_pp_m","api541_minimum_analytical_unbalance_g_mm",
    "classify_mode","analytical_unbalance_case","run_api541_analytical_unbalance",
]
