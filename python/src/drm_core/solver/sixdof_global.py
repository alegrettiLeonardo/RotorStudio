"""B2 thin Python adapter for the native global 6-DOF solver.

Production numerical work remains in Fortran:
- global M/K/C/G/Ksdt assembly
- state-space construction and dense eigensolution
- modal classification/whirl
- Campbell MAC tracking

Python performs declared-scope validation, domain mapping, qualified bearing
coefficient evaluation, Fortran-order buffer allocation, ABI calls and result
construction only.
"""
from __future__ import annotations

import ctypes as ct
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Iterable

import numpy as np

from drm_core.domain.model import (
    RotorModel, ShaftElement, TaperedShaftElement, AsymmetricShaftElement, Disk
)
from drm_core.domain.bearings import CoefficientBearing
from .bearings_backend import AdvancedBearingBackend
from .ffi import SolverLibraryError, load_library

NODE_DOF_ORDER=("x","y","z","alpha","beta","theta")
MODE_TYPE={1:"Lateral",2:"Axial",3:"Torsional"}
STATUS={
    0:"SUCCESS",20:"INVALID_INPUT",21:"INVALID_DIMENSION",22:"UNSUPPORTED",
    23:"SINGULAR_MASS",24:"LAPACK_FAILURE",25:"INSUFFICIENT_CAPACITY",
    26:"NONFINITE_RESULT",27:"B1_ELEMENT_FAILURE",
}


class SixDOFGlobalError(RuntimeError):
    def __init__(self,status:int,context:str):
        self.status=int(status)
        super().__init__(
            f"B2 {STATUS.get(self.status,'UNKNOWN_STATUS')} ({self.status}): "
            f"{context}. No Python numerical fallback was used."
        )


@dataclass(frozen=True)
class SixDOFGlobalMatrices:
    M: np.ndarray
    K: np.ndarray
    C: np.ndarray
    G: np.ndarray
    Ksdt: np.ndarray
    speed_rad_s: float
    frequency_rad_s: float
    node_dof_order: tuple[str,...]=NODE_DOF_ORDER


@dataclass(frozen=True)
class SixDOFModalResult:
    speed_rad_s: float
    eigenvalues_all: np.ndarray
    eigenvalues: np.ndarray
    eigenvectors_displacement: np.ndarray
    state_space: np.ndarray
    wn_rad_s: np.ndarray
    wd_rad_s: np.ndarray
    damping_ratio: np.ndarray
    log_dec: np.ndarray
    mode_type: tuple[str,...]
    whirl_value: np.ndarray
    residual: np.ndarray
    mass_rcond: float
    metadata: dict


@dataclass(frozen=True)
class SixDOFCampbellResult:
    speed_rad_s: np.ndarray
    wd_rad_s: np.ndarray
    wn_rad_s: np.ndarray
    damping_ratio: np.ndarray
    log_dec: np.ndarray
    whirl_value: np.ndarray
    mode_type: np.ndarray
    tracking_index: np.ndarray
    tracking_mac: np.ndarray
    mac_matrix: np.ndarray
    metadata: dict


def _ptr(a):
    if a.dtype==np.int32:
        return a.ctypes.data_as(ct.POINTER(ct.c_int))
    return a.ctypes.data_as(ct.POINTER(ct.c_double))


def _native(library_path=None):
    lib=load_library(library_path)
    I,D=ct.c_int,ct.c_double
    IP,P=ct.POINTER(I),ct.POINTER(D)
    try:
        reqg=lib.rd_6dof_global_required_v1
        glob=lib.rd_6dof_global_matrices_v1
        reqm=lib.rd_6dof_modal_required_v1
        modal=lib.rd_6dof_modal_v1
        reqc=lib.rd_6dof_campbell_required_v1
        camp=lib.rd_6dof_campbell_v1
        camp2=lib.rd_6dof_campbell_v2
    except AttributeError as exc:
        raise SolverLibraryError(
            "B2 requires rd_6dof_global/modal/campbell_*_v1 symbols. "
            "Rebuild the B2 native library; no fallback is available."
        ) from exc
    reqg.argtypes=[I,IP,IP];reqg.restype=I
    glob.argtypes=[I,I,IP,P,IP,I,IP,P,I,IP,P]+[P,I,I]*5;glob.restype=I
    reqm.argtypes=[I,I,IP,IP,IP,IP,IP,IP];reqm.restype=I
    modal.argtypes=[
        I,I,IP,P,IP,I,IP,P,I,IP,P,D,I,
        I,I,I,I,I,I,IP,IP,P,
        P,P,P,P,P,P,P,P,P,P,IP,P,P,P,
    ];modal.restype=I
    reqc.argtypes=[I,I,I,IP,IP,IP];reqc.restype=I
    camp.argtypes=[
        I,I,IP,P,IP,I,IP,P,I,IP,I,P,P,I,I,I,I,
        P,P,P,P,P,IP,IP,P,P
    ];camp.restype=I
    camp2.argtypes=[
        I,I,IP,P,IP,I,IP,P,I,IP,I,P,P,I,I,I,I,I,
        P,P,P,P,P,IP,IP,P,P
    ];camp2.restype=I
    return lib,reqg,glob,reqm,modal,reqc,camp,camp2


def _status(code,context):
    if int(code):
        raise SixDOFGlobalError(int(code),context)


def _finite_real(name,value,*,nonnegative=False):
    if isinstance(value,(bool,np.bool_)):
        raise ValueError(f"{name}: expected finite real scalar")
    value=float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name}: expected finite real scalar")
    if nonnegative and value<0:
        raise ValueError(f"{name}: expected >= 0")
    return value


def _shaft_flags(stype:int):
    typ=stype if 1<=stype<=8 else stype-20 if 21<=stype<=28 else None
    if typ is None or not 1<=typ<=8:
        raise ValueError(f"unsupported B2 shaft_type={stype}")
    shear=typ not in (1,5,7,8)
    rotary=typ not in (1,4,6,8)
    gyro=typ not in (3,6,7,8)
    return int(shear),int(rotary),int(gyro),1  # Cowper; frozen legacy domain semantics.


def _disk_inertias(d:Disk):
    if d.disk_type==1:
        rho,w,od,idd=map(float,(d.p3,d.p4,d.p5,d.p6))
        if not (rho>0 and w>0 and od>idd>=0):
            raise ValueError(f"disk node={d.node}: invalid geometric disk")
        m=rho*np.pi*w*(od*od-idd*idd)/4.0
        Ip=m*(od*od+idd*idd)/8.0
        Id=0.5*Ip+m*w*w/12.0
        return m,Id,Ip
    if d.disk_type==2:
        m,Id,Ip=map(float,(d.p3,d.p4,d.p5))
        if not (m>0 and Id>0 and Ip>0):
            raise ValueError(f"disk node={d.node}: invalid inertial disk")
        return m,Id,Ip
    raise ValueError(
        f"disk_type={d.disk_type} at node={d.node} is outside initial B2 scope; "
        "flexible/anisotropic/generic disks are not silently reduced"
    )


def _validate_model(model:RotorModel):
    n=len(model.nodes)
    if not 2<=n<=100:
        raise ValueError(f"B2 nodes={n}; expected 2..100")
    numbers=[int(x.number) for x in model.nodes]
    if numbers!=list(range(1,n+1)):
        raise ValueError(f"B2 nodes must be consecutive one-based; received {numbers}")
    z=np.asarray([float(x.z_m) for x in model.nodes],float)
    if not np.isfinite(z).all() or not np.all(np.diff(z)>0):
        raise ValueError("B2 node axial coordinates must be finite and strictly increasing")
    if model.rotors:
        raise ValueError("B2 initial scope rejects coaxial/multirotor definitions")
    if len(model.shafts)!=n-1:
        raise ValueError("B2 requires exactly one shaft element between every consecutive node")
    for i,s in enumerate(model.shafts,1):
        if isinstance(s,AsymmetricShaftElement):
            raise ValueError("AsymmetricShaftElement is outside initial B2 scope")
        if not isinstance(s,(ShaftElement,TaperedShaftElement)):
            raise ValueError(f"unsupported B2 shaft class {type(s).__name__}")
        if (int(s.node1),int(s.node2))!=(i,i+1):
            raise ValueError(
                f"B2 shaft {i}: expected nodes {(i,i+1)}, received {(s.node1,s.node2)}"
            )
        if isinstance(s,ShaftElement) and float(s.damping_factor)!=0.0:
            raise ValueError("B2 shaft damping semantics are not qualified; expected damping_factor=0")
    for d in model.disks:
        if int(d.node) not in numbers:
            raise ValueError(f"disk node={d.node} outside model")
        _disk_inertias(d)
    for b in model.bearings:
        if int(b.node) not in numbers:
            raise ValueError(f"bearing node={b.node} outside model")
        if int(b.bearing_type) not in (3,5):
            raise ValueError(
                f"legacy bearing_type={b.bearing_type} outside B2 initial radial coefficient scope"
            )
    for b in model.advanced_bearings:
        if int(b.node) not in numbers:
            raise ValueError(f"advanced bearing node={b.node} outside model")
        if not isinstance(b,CoefficientBearing):
            raise ValueError(
                f"{type(b).__name__} is a direct physical provider; B2 modal/Campbell "
                "requires a pre-materialized qualified CoefficientBearing/MAP_BACKED table"
            )


def _descriptors(model:RotorModel,speed:float,frequency:float,library_path=None):
    _validate_model(model)
    nn=len(model.nodes);ns=len(model.shafts);nd=len(model.disks)
    sn=np.zeros((2,max(1,ns)),dtype=np.int32,order="F")
    sf=np.zeros((4,max(1,ns)),dtype=np.int32,order="F")
    sp=np.zeros((10,max(1,ns)),dtype=np.float64,order="F")
    z={int(x.number):float(x.z_m) for x in model.nodes}
    for j,s in enumerate(model.shafts):
        L=z[int(s.node2)]-z[int(s.node1)]
        if isinstance(s,ShaftElement):
            st=int(s.shaft_type);idl=float(s.inner_diameter_m);odl=float(s.outer_diameter_m)
            idr=idl;odr=odl;rho=float(s.rho_kg_m3);E=float(s.E_pa);Gs=float(s.G_pa)
            F=float(s.axial_force_n);T=float(s.torque_nm)
        else:
            st=int(s.shaft_type);idl=float(s.inner_diameter_1_m);odl=float(s.outer_diameter_1_m)
            idr=float(s.inner_diameter_2_m);odr=float(s.outer_diameter_2_m)
            rho=float(s.rho_kg_m3);E=float(s.E_pa);Gs=float(s.G_pa);F=float(s.axial_force_n);T=0.0
        if not (L>0 and rho>0 and E>0 and Gs>0 and 0<=idl<odl and 0<=idr<odr):
            raise ValueError(f"shaft {j+1}: invalid B2/B1 geometry or material")
        sn[:,j]=(int(s.node1),int(s.node2))
        sf[:,j]=_shaft_flags(st)
        sp[:,j]=(L,idl,odl,idr,odr,rho,E,Gs,F,T)
    dn=np.zeros(max(1,nd),dtype=np.int32)
    dp=np.zeros((3,max(1,nd)),dtype=np.float64,order="F")
    for j,d in enumerate(model.disks):
        dn[j]=int(d.node);dp[:,j]=_disk_inertias(d)

    rows=[]
    nodes=[]
    for b in model.bearings:
        p=tuple(float(x) for x in b.properties)
        if int(b.bearing_type)==3:
            if len(p)<4: raise ValueError("bearing type 3 requires Kxx,Kyy,Cxx,Cyy")
            K=np.array([[p[0],0.0],[0.0,p[1]]]);C=np.array([[p[2],0.0],[0.0,p[3]]]);M=np.zeros((2,2))
        else:
            if len(p)<8: raise ValueError("bearing type 5 requires full radial K/C coefficients")
            K=np.array([[p[0],p[1]],[p[2],p[3]]]);C=np.array([[p[4],p[5]],[p[6],p[7]]]);M=np.zeros((2,2))
        nodes.append(int(b.node));rows.append((K,C,M))
    if model.advanced_bearings:
        provider=AdvancedBearingBackend(rotor_library_path=library_path)
        for b in model.advanced_bearings:
            ev=provider.evaluate(b,float(speed),float(frequency))
            K=np.asarray(ev.K,float);C=np.asarray(ev.C,float);M=np.asarray(ev.M,float)
            if K.shape!=(2,2) or C.shape!=(2,2) or M.shape!=(2,2):
                raise ValueError(f"{type(b).__name__}: expected qualified radial 2x2 K/C/M")
            nodes.append(int(b.node));rows.append((K,C,M))
    nb=len(rows)
    bn=np.zeros(max(1,nb),dtype=np.int32)
    bp=np.zeros((12,max(1,nb)),dtype=np.float64,order="F")
    for j,(node,(K,C,M)) in enumerate(zip(nodes,rows,strict=True)):
        if not all(np.isfinite(x).all() for x in (K,C,M)):
            raise ValueError(f"bearing node={node}: nonfinite coefficient")
        bn[j]=node
        bp[:,j]=(K[0,0],K[0,1],K[1,0],K[1,1],
                 C[0,0],C[0,1],C[1,0],C[1,1],
                 M[0,0],M[0,1],M[1,0],M[1,1])
    return nn,ns,sn,sp,sf,nd,dn,dp,nb,bn,bp


def _matrix(n):
    return np.full((n,n),np.nan,dtype=np.float64,order="F")


def assemble_6dof(model:RotorModel,speed_rad_s:float=0.0,frequency_rad_s:float|None=None,library_path=None):
    speed=_finite_real("speed_rad_s",speed_rad_s)
    frequency=speed if frequency_rad_s is None else _finite_real("frequency_rad_s",frequency_rad_s)
    nn,ns,sn,sp,sf,nd,dn,dp,nb,bn,bp=_descriptors(model,speed,frequency,library_path)
    _,_,fn,_,_,_,_,_=_native(library_path);n=6*nn
    out=[_matrix(n) for _ in range(5)]
    args=[]
    for a in out:args.extend([_ptr(a),n,a.size])
    code=fn(nn,ns,_ptr(sn),_ptr(sp),_ptr(sf),nd,_ptr(dn),_ptr(dp),nb,_ptr(bn),_ptr(bp),*args)
    _status(code,"global M/K/C/G/Ksdt assembly")
    if not all(np.isfinite(x).all() for x in out):
        raise SixDOFGlobalError(26,"native global assembly returned nonfinite output")
    return SixDOFGlobalMatrices(*out,speed,frequency)


def run_modal_6dof(model:RotorModel,speed_rad_s:float,num_modes:int=12,library_path=None):
    speed=_finite_real("speed_rad_s",speed_rad_s)
    if isinstance(num_modes,bool) or int(num_modes)!=num_modes or int(num_modes)<2 or int(num_modes)%2:
        raise ValueError("num_modes must be an even integer >= 2")
    num_modes=int(num_modes)
    nn,ns,sn,sp,sf,nd,dn,dp,nb,bn,bp=_descriptors(model,speed,speed,library_path)
    _,_,_,req,fn,_,_,_=_native(library_path)
    ndof=ct.c_int();state=ct.c_int();maxret=ct.c_int();selected=ct.c_int();qvalues=ct.c_int();avalues=ct.c_int()
    _status(req(nn,num_modes,ct.byref(ndof),ct.byref(state),ct.byref(maxret),ct.byref(selected),ct.byref(qvalues),ct.byref(avalues)),"modal size query")
    allr=np.full(maxret.value,np.nan);alli=np.full(maxret.value,np.nan)
    nsel_cap=selected.value
    selected_arrays=[np.full(nsel_cap,np.nan) for _ in range(8)]
    er,ei,wn,wd,zeta,logdec,whirl,residual=selected_arrays
    mtype=np.full(nsel_cap,-1,dtype=np.int32)
    qr=np.full((ndof.value,nsel_cap),np.nan,order="F");qi=np.full_like(qr,np.nan,order="F")
    A=np.full((state.value,state.value),np.nan,order="F")
    nret=ct.c_int();nsel=ct.c_int();rcond=ct.c_double()
    code=fn(
        nn,ns,_ptr(sn),_ptr(sp),_ptr(sf),nd,_ptr(dn),_ptr(dp),nb,_ptr(bn),_ptr(bp),
        speed,num_modes,maxret.value,nsel_cap,ndof.value,qr.size,state.value,A.size,
        ct.byref(nret),ct.byref(nsel),ct.byref(rcond),
        _ptr(allr),_ptr(alli),_ptr(er),_ptr(ei),_ptr(wn),_ptr(wd),_ptr(zeta),_ptr(logdec),
        _ptr(whirl),_ptr(residual),_ptr(mtype),_ptr(qr),_ptr(qi),_ptr(A)
    )
    _status(code,"fixed-speed 6-DOF modal analysis")
    nr,nsout=nret.value,nsel.value
    result=SixDOFModalResult(
        speed,
        (allr[:nr]+1j*alli[:nr]).copy(),
        (er[:nsout]+1j*ei[:nsout]).copy(),
        (qr[:,:nsout]+1j*qi[:,:nsout]).copy(order="F"),
        A.copy(order="F"),
        wn[:nsout].copy(),wd[:nsout].copy(),zeta[:nsout].copy(),logdec[:nsout].copy(),
        tuple(MODE_TYPE.get(int(v),f"Unknown({int(v)})") for v in mtype[:nsout]),
        whirl[:nsout].copy(),residual[:nsout].copy(),float(rcond.value),
        {"dof_model":6,"coefficient_policy":"SYNCHRONOUS_COEFFICIENTS",
         "bearing_speed_rad_s":speed,"bearing_frequency_rad_s":speed,
         "matched_whirl":False,"synchronous_rouch":False,"torsional_analysis":False}
    )
    if not np.isfinite(result.residual).all() or result.mass_rcond<1e-14:
        raise SixDOFGlobalError(26,"modal diagnostics failed")
    return result


def run_campbell_6dof(model:RotorModel,speed_range_rad_s:Iterable[float],frequencies:int=6,library_path=None,frequency_type:str="wd"):
    speeds=np.asarray(tuple(speed_range_rad_s),dtype=np.float64)
    if speeds.ndim!=1 or len(speeds)<2 or not np.isfinite(speeds).all() or not np.all(np.diff(speeds)>0):
        raise ValueError("speed_range_rad_s must be a finite strictly increasing 1-D grid with >=2 stations")
    if isinstance(frequencies,bool) or int(frequencies)!=frequencies or int(frequencies)<1:
        raise ValueError("frequencies must be integer >=1")
    frequencies=int(frequencies)
    frequency_type=str(frequency_type).lower()
    if frequency_type not in {"wd","wn"}:
        raise ValueError("frequency_type must be 'wd' or 'wn'")
    frequency_type_code=0 if frequency_type=="wd" else 1
    # Descriptor topology is fixed; bearing coefficients are evaluated on the
    # synchronous diagonal (speed=frequency) at every station.
    first=_descriptors(model,float(speeds[0]),float(speeds[0]),library_path)
    nn,ns,sn,sp,sf,nd,dn,dp,nb,bn,_=first
    maps=np.zeros((12,max(1,nb),len(speeds)),dtype=np.float64,order="F")
    for k,w in enumerate(speeds):
        desc=_descriptors(model,float(w),float(w),library_path)
        if desc[:2]!=(nn,ns) or desc[5]!=nd or desc[8]!=nb:
            raise RuntimeError("B2 model topology changed while evaluating Campbell coefficient map")
        if not np.array_equal(desc[2],sn) or not np.array_equal(desc[6],dn) or not np.array_equal(desc[9],bn):
            raise RuntimeError("B2 topology changed while evaluating Campbell")
        maps[:,:,k]=desc[10]
    _,_,_,_,_,req,_,fn=_native(library_path)
    branches=ct.c_int();tracks=ct.c_int();macs_n=ct.c_int()
    _status(req(nn,len(speeds),frequencies,ct.byref(branches),ct.byref(tracks),ct.byref(macs_n)),"Campbell size query")
    shape=(frequencies,len(speeds))
    wd=np.full(shape,np.nan,order="F");wn=np.full(shape,np.nan,order="F")
    zeta=np.full(shape,np.nan,order="F");logdec=np.full(shape,np.nan,order="F");whirl=np.full(shape,np.nan,order="F")
    nt=frequencies+2
    mtype=np.full(shape,-1,dtype=np.int32,order="F")
    tidx=np.full((nt,len(speeds)),-1,dtype=np.int32,order="F")
    tmac=np.full((nt,len(speeds)),np.nan,order="F")
    mm=np.full((nt,nt,len(speeds)),np.nan,order="F")
    code=fn(
        nn,ns,_ptr(sn),_ptr(sp),_ptr(sf),nd,_ptr(dn),_ptr(dp),nb,_ptr(bn),
        len(speeds),_ptr(np.ascontiguousarray(speeds)),_ptr(maps),frequencies,frequency_type_code,
        branches.value,tracks.value,macs_n.value,
        _ptr(wd),_ptr(wn),_ptr(zeta),_ptr(logdec),_ptr(whirl),_ptr(mtype),_ptr(tidx),_ptr(tmac),_ptr(mm)
    )
    _status(code,"standard 6-DOF Campbell analysis")
    types=np.empty(shape,dtype=object)
    for j in range(shape[1]):
        for i in range(shape[0]):types[i,j]=MODE_TYPE.get(int(mtype[i,j]),f"Unknown({int(mtype[i,j])})")
    return SixDOFCampbellResult(
        speeds.copy(),wd.copy(order="F"),wn.copy(order="F"),zeta.copy(order="F"),logdec.copy(order="F"),
        whirl.copy(order="F"),types,tidx.copy(order="F"),tmac.copy(order="F"),mm.copy(order="F"),
        {"dof_model":6,"frequency_type":frequency_type,"matched_whirl":False,"synchronous_rouch":False,
         "torsional_analysis":False,"tracking":"ROSS_MAC_GT_0.9","bearing_policy":"speed=frequency=rotor_speed"}
    )
