"""Thin A5 UCS binding.

Production map construction, modal sweeps, Rouch mass folding, intersections and
critical-point modal solves are native Fortran. Python only validates scope,
marshals arrays and uses the already-qualified native bearing interpolation
provider to evaluate the original bearing curve.
"""
from __future__ import annotations
from dataclasses import replace
import numpy as np
from drm_core.domain.model import ShaftElement
from drm_core.domain.bearings import CoefficientBearing
from .ffi import configure_ucs, SolverLibraryError


ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"


def _validate_model(backend,model,stiffness_range_exponents,num,num_modes,bearing_speed_range,synchronous):
    nn=len(model.nodes)
    if stiffness_range_exponents is None:
        raise ValueError(
            "UCS stiffness_range_exponents is required in A5: RotorStudio has no "
            "unambiguous rated_w/rated-speed domain property, so no rated-speed heuristic is used."
        )
    try:
        start,stop=map(float,stiffness_range_exponents)
    except Exception as exc:
        raise ValueError("UCS stiffness exponent range must contain exactly two numeric exponents.") from exc
    if not np.isfinite([start,stop]).all() or stop<=start:
        raise ValueError("UCS stiffness exponents must be finite and strictly increasing.")
    if not (2<=int(num)<=256):
        raise ValueError("UCS number of stiffness points must be 2..256.")
    num=int(num);num_modes=int(num_modes)
    if num_modes<4 or num_modes>8*nn or num_modes//4<1:
        raise ValueError("UCS num_modes must permit at least one branch and fit the full 4-DOF state system.")
    if synchronous not in (False,True,0,1):
        raise ValueError("UCS synchronous must be a boolean Rouch flag.")
    if nn<2 or nn>128 or [x.number for x in model.nodes]!=list(range(1,nn+1)):
        raise ValueError("UCS requires 2..128 consecutive one-based shaft nodes.")
    if model.rotors or model.bend:
        raise ValueError("UCS initial A5 scope is a single shaft line without coaxial links or pre-bend.")
    if len(model.shafts)!=nn-1:
        raise ValueError("UCS requires one shaft element between each consecutive node.")
    for i,s in enumerate(model.shafts):
        if not isinstance(s,ShaftElement) or s.shaft_type!=2 or (s.node1,s.node2)!=(i+1,i+2):
            raise ValueError("UCS A5 qualified shaft scope is the ordered circular Timoshenko type-2 4-DOF chain.")
        if s.axial_force_n!=0 or s.torque_nm!=0:
            raise ValueError("UCS A5 axial preload and shaft torque are outside the declared scope.")
    if any(d.disk_type not in (1,2) for d in model.disks):
        raise ValueError("UCS A5 supports gyroscopic disk types 1/2 only.")
    legacy=[x for x in model.bearings if x.bearing_type!=8]
    seals=[x for x in model.bearings if x.bearing_type==8]
    advanced=list(model.advanced_bearings)
    if legacy and advanced:
        raise ValueError(
            "UCS cannot infer the ROSS first-bearing ordering across separate legacy and advanced "
            "collections; use one support representation family for this A5 scope."
        )
    if legacy:
        for x in legacy:
            if x.bearing_type not in (3,5):
                raise ValueError("UCS legacy supports must be constant radial type 3 or 5; rigid/linked/physical paths fail closed.")
        supports=legacy
        family="legacy"
    elif advanced:
        if any(not isinstance(x,CoefficientBearing) for x in advanced):
            raise ValueError("UCS advanced supports must be qualified COEFFICIENT_TABLE / MAP_BACKED bearings.")
        supports=advanced
        family="coefficient"
    else:
        raise ValueError("UCS requires at least one non-seal radial support.")
    if any(x.node<1 or x.node>nn for x in supports):
        raise ValueError("UCS support node lies outside the shaft node range.")
    # Frozen ROSS Rotor.__init__ sorts by node before run_ucs selects bearing0.
    # Sort only this temporary list; stable ties and persisted order are preserved.
    supports=sorted(supports,key=lambda bearing:bearing.node)
    if bearing_speed_range is not None:
        try:a,b=map(float,bearing_speed_range)
        except Exception as exc:raise ValueError("UCS bearing_speed_range must contain two finite rad/s values.") from exc
        if not np.isfinite([a,b]).all() or b<=a:
            raise ValueError("UCS bearing_speed_range must be finite and strictly increasing.")
        bearing_speed_range=(a,b)
    return start,stop,num,num_modes,bool(synchronous),supports,family,bearing_speed_range,seals


def _native_model_arrays(backend,model):
    stripped=replace(model,bearings=[],advanced_bearings=[])
    _,z,sh,di,_=backend._arrays(stripped)
    if not all(np.isfinite(x).all() for x in (z,sh,di)):
        raise ValueError("UCS model contains NaN/Inf in native shaft/disk arrays.")
    return z,sh,di


def _raw_equal(bearing,family):
    if family=="legacy":
        p=bearing.properties
        if bearing.bearing_type==3:
            return np.array_equal(np.asarray(p[0]),np.asarray(p[1]))
        return np.array_equal(np.asarray(p[0]),np.asarray(p[3]))
    ky=bearing.kxx if bearing.kyy is None else bearing.kyy
    return np.array_equal(np.asarray(bearing.kxx),np.asarray(ky))


def _axis(bearing,family):
    if family=="legacy":return None
    if len(bearing.speed_rad_s):return np.asarray(bearing.speed_rad_s,dtype=float)
    if len(bearing.frequency_rad_s):return np.asarray(bearing.frequency_rad_s,dtype=float)
    return None


def _curve(backend,bearing,family,speeds):
    speeds=np.ascontiguousarray(speeds,dtype=np.float64)
    if family=="legacy":
        p=bearing.properties
        if bearing.bearing_type==3:kx,ky=float(p[0]),float(p[1])
        else:kx,ky=float(p[0]),float(p[3])
        return np.full(speeds.size,kx),np.full(speeds.size,ky),[{"status":"constant"} for _ in speeds]
    provider=backend._bearing_provider()
    kx=np.empty(speeds.size);ky=np.empty(speeds.size);meta=[]
    for i,w in enumerate(speeds):
        point=provider.evaluate(bearing,float(w),float(w))
        kx[i]=point.K[0,0];ky[i]=point.K[1,1]
        meta.append(dict(point.details))
    if not np.isfinite(kx).all() or not np.isfinite(ky).all():
        raise SolverLibraryError("UCS bearing interpolation produced NaN/Inf; result rejected.")
    return kx,ky,meta


def _map_call(backend,z,sh,di,nodes,start,stop,num,num_modes,synchronous):
    _,map_fn,_,_=configure_ucs(backend.lib);p=backend._ptr
    nodes=np.ascontiguousarray(nodes,dtype=np.int32)
    nbranch=num_modes//4
    grid=np.empty(num,dtype=np.float64)
    wn=np.empty((nbranch,num),dtype=np.float64,order="F")
    status=map_fn(len(z),p(z),sh.shape[1],p(sh),di.shape[1],p(di),len(nodes),backend._iptr(nodes),
                  float(start),float(stop),num,num_modes,int(synchronous),nbranch,p(grid),p(wn))
    if status:raise SolverLibraryError(f"UCS rd_ucs_map_v1 status={status}; invalid/singular temporary undamped rotor.")
    if not np.isfinite(grid).all() or not np.isfinite(wn).all():raise SolverLibraryError("UCS native map returned NaN/Inf.")
    return grid,wn


def execute(backend,model,stiffness_range_exponents,num=20,num_modes=16,bearing_speed_range=None,synchronous=False):
    start,stop,num,num_modes,synchronous,supports,family,bearing_speed_range,_ = _validate_model(
        backend,model,stiffness_range_exponents,num,num_modes,bearing_speed_range,synchronous
    )
    z,sh,di=_native_model_arrays(backend,model)
    nodes=np.ascontiguousarray([x.node for x in supports],dtype=np.int32)
    bearing0=supports[0]
    grid0,wn0=_map_call(backend,z,sh,di,nodes,start,stop,num,num_modes,synchronous)

    if bearing_speed_range is not None:
        bs=np.linspace(bearing_speed_range[0],bearing_speed_range[1],30,dtype=float)
        speed_policy="explicit_30_point_linspace"
    else:
        axis=_axis(bearing0,family)
        if axis is not None:
            bs=np.asarray(axis,dtype=float)
            speed_policy="bearing_speed_axis" if family=="coefficient" and len(bearing0.speed_rad_s) else "bearing_frequency_axis"
        else:
            margin=float(wn0.min())*.1
            bs=np.linspace(float(wn0.min()-margin),float(wn0.max()+margin),10,dtype=float)
            speed_policy="constant_10_point_rotor_wn_margin"
    if bs.ndim!=1 or bs.size<2 or bs.size>4096 or not np.isfinite(bs).all() or np.any(np.diff(bs)<0):
        raise ValueError("UCS bearing speed axis must be 2..4096 finite, nondecreasing rad/s values.")

    kxx,kyy,bearing_meta=_curve(backend,bearing0,family,bs)
    ncoeff=1 if _raw_equal(bearing0,family) else 2
    required,_,_,full_fn=configure_ucs(backend.lib)
    nb=np.array(0,dtype=np.int32);mi=np.array(0,dtype=np.int32);ncm=np.array(0,dtype=np.int32)
    import ctypes as ct
    nb_c=ct.c_int();mi_c=ct.c_int();ncm_c=ct.c_int()
    status=required(num,num_modes,ncoeff,bs.size,ct.byref(nb_c),ct.byref(mi_c),ct.byref(ncm_c))
    if status:raise ValueError(f"UCS size query rejected inputs with status={status}.")
    nbranch,maxint,ncritmode=nb_c.value,mi_c.value,ncm_c.value
    if nbranch!=num_modes//4 or ncritmode!=6 or maxint<0 or maxint>2_000_000:
        raise ValueError("UCS requested result buffers exceed validated A5 bounds.")

    p=backend._ptr
    grid=np.empty(num,dtype=np.float64)
    wn=np.empty((nbranch,num),dtype=np.float64,order="F")
    ik=np.empty(maxint,dtype=np.float64);sp=np.empty(maxint,dtype=np.float64)
    imode=np.empty(maxint,dtype=np.int32);isource=np.empty(maxint,dtype=np.int32)
    nint_c=ct.c_int()
    critical=[np.empty((6,maxint),dtype=np.float64,order="F") for _ in range(6)]
    status=full_fn(
        len(z),p(z),sh.shape[1],p(sh),di.shape[1],p(di),len(nodes),backend._iptr(nodes),
        start,stop,num,num_modes,int(synchronous),bs.size,p(np.ascontiguousarray(bs,dtype=np.float64)),
        p(np.ascontiguousarray(kxx,dtype=np.float64)),p(np.ascontiguousarray(kyy,dtype=np.float64)),
        ncoeff,nbranch,maxint,p(grid),p(wn),ct.byref(nint_c),p(ik),p(sp),
        backend._iptr(imode),backend._iptr(isource),*[p(x) for x in critical]
    )
    if status:raise SolverLibraryError(f"UCS rd_ucs_v1 status={status}; native sweep/intersection/critical solve failed closed.")
    nint=nint_c.value
    if nint<0 or nint>maxint:raise SolverLibraryError("UCS native intersection count violated the ABI buffer contract.")
    arrays=[grid,wn,ik[:nint],sp[:nint],*[x[:,:nint] for x in critical]]
    if not all(np.isfinite(x).all() for x in arrays):raise SolverLibraryError("UCS native result contains NaN/Inf.")
    if not np.array_equal(grid,grid0):
        raise SolverLibraryError("UCS full/native map stiffness grid mismatch.")
    if not np.allclose(wn,wn0,rtol=0,atol=0):
        raise SolverLibraryError("UCS full/native map branch mismatch.")
    return dict(
        stiffness_range_exponents=np.asarray([start,stop],float),
        stiffness_log_n_m=grid,
        natural_frequency_rad_s=wn,
        bearing_speed_rad_s=np.asarray(bs,float),
        bearing_kxx_n_m=np.asarray(kxx,float),
        bearing_kyy_n_m=np.asarray(kyy,float),
        intersection_stiffness_n_m=np.asarray(ik[:nint],float),
        intersection_speed_rad_s=np.asarray(sp[:nint],float),
        intersection_mode_index=np.asarray(imode[:nint],int)-1,
        intersection_coefficient=np.asarray(["kxx" if x==1 else "kyy" for x in isource[:nint]]),
        critical_eigenvalue_real=critical[0][:,:nint],
        critical_eigenvalue_imag=critical[1][:,:nint],
        critical_wn_rad_s=critical[2][:,:nint],
        critical_wd_rad_s=critical[3][:,:nint],
        critical_damping_ratio=critical[4][:,:nint],
        critical_log_dec=critical[5][:,:nint],
        synchronous=synchronous,
        bearing_evaluation=bearing_meta,
        bearing_speed_policy=speed_policy,
        coefficient_families=("kxx",) if ncoeff==1 else ("kxx","kyy"),
    )


def matrices(backend,model,stiffness_n_m,synchronous=False):
    start,stop,num,num_modes,synchronous,supports,family,_,_=_validate_model(
        backend,model,(6.0,7.0),2,4,None,synchronous
    )
    k=float(stiffness_n_m)
    if not np.isfinite(k) or k<=0:raise ValueError("UCS sentinel stiffness must be positive finite N/m.")
    z,sh,di=_native_model_arrays(backend,model)
    nodes=np.ascontiguousarray([x.node for x in supports],dtype=np.int32)
    _,_,matrix_fn,_=configure_ucs(backend.lib);n=4*len(z);p=backend._ptr
    out=[np.empty((n,n),dtype=np.float64,order="F") for _ in range(4)]
    status=matrix_fn(len(z),p(z),sh.shape[1],p(sh),di.shape[1],p(di),len(nodes),backend._iptr(nodes),k,int(synchronous),*[p(x) for x in out])
    if status:raise SolverLibraryError(f"UCS rd_ucs_matrix_v1 status={status}.")
    if not all(np.isfinite(x).all() for x in out):raise SolverLibraryError("UCS matrix sentinel contains NaN/Inf.")
    return dict(zip(("M","C","G","K"),out))
