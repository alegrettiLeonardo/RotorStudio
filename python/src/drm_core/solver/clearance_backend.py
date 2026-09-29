"""Thin A8 close-clearance binding.

The production unbalance force, synchronous forced-response sweep, probe
projection, API 617 scaling and orbit-major-axis clearance check are native
Fortran. Python performs declared-scope validation, speed-axis canonicalization,
qualified bearing coefficient materialization and ABI marshaling.
"""
from __future__ import annotations

import ctypes as ct
import numpy as np

from drm_core.domain.model import ShaftElement
from drm_core.domain.bearings import CoefficientBearing
from .general_frf_backend import prepare
from .ffi import configure_clearance,SolverLibraryError

ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"


def _validate_model(model):
    nn=len(model.nodes)
    if nn<2 or nn>128 or [n.number for n in model.nodes]!=list(range(1,nn+1)):
        raise ValueError("A8 requires 2..128 consecutive one-based shaft nodes")
    if model.rotors or model.bend:
        raise ValueError("A8 is a single straight shaft line; coaxial/pre-bend is out of scope")
    if len(model.shafts)!=nn-1:
        raise ValueError("A8 requires one shaft element between each consecutive node")
    for i,s in enumerate(model.shafts):
        if not isinstance(s,ShaftElement) or s.shaft_type!=2 or (s.node1,s.node2)!=(i+1,i+2):
            raise ValueError("A8 qualified shaft scope is the ordered circular type-2 4-DOF chain")
        if s.damping_factor!=0 or s.axial_force_n!=0 or s.torque_nm!=0:
            raise ValueError("A8 shaft damping/preload/torque are outside declared scope")
    if any(d.disk_type not in (1,2) for d in model.disks):
        raise ValueError("A8 supports disk types 1/2 only")
    for b in model.advanced_bearings:
        if not isinstance(b,CoefficientBearing):
            raise ValueError(
                f"{type(b).__name__}: A8 accepts qualified coefficient/map-backed "
                "bearings only; create a qualified coefficient map first"
            )
    return nn


def execute(
    backend,
    model,
    speed_range_rad_s,
    minimum_allowable_speed_rad_s,
    maximum_continuous_speed_rad_s,
    probe_nodes,
    probe_angles_rad,
    clearance_nodes,
    radial_clearance_m,
    probe_tags=None,
    clearance_tags=None,
    mode=0,
    unbalance_nodes=None,
    unbalance_magnitude_kg_m=None,
    unbalance_phase_rad=None,
    scale_factor_cap=None,
    num_modes=12,
):
    nn=_validate_model(model)
    raw=np.asarray(speed_range_rad_s,dtype=float)
    if raw.ndim!=1 or raw.size<1 or raw.size>10000 or not np.isfinite(raw).all() or np.any(raw<0):
        raise ValueError("speed_range_rad_s must be 1..10000 finite nonnegative values")
    nma=float(minimum_allowable_speed_rad_s);nmc=float(maximum_continuous_speed_rad_s)
    if not np.isfinite([nma,nmc]).all() or not 0<=nma<=nmc or nmc<=0:
        raise ValueError("expected 0 <= minimum_allowable_speed_rad_s <= maximum_continuous_speed_rad_s and Nmc > 0")
    speed=np.ascontiguousarray(np.union1d(raw,[nma,nmc]),dtype=np.float64)

    pnodes=np.asarray(probe_nodes,dtype=np.int32)
    pang=np.asarray(probe_angles_rad,dtype=np.float64)
    cnodes=np.asarray(clearance_nodes,dtype=np.int32)
    radial=np.asarray(radial_clearance_m,dtype=np.float64)
    if pnodes.ndim!=1 or len(pnodes)<1 or len(pnodes)!=len(pang):
        raise ValueError("A8 requires equal non-empty probe_nodes/probe_angles_rad arrays")
    if cnodes.ndim!=1 or len(cnodes)<1 or len(cnodes)!=len(radial):
        raise ValueError("A8 requires equal non-empty clearance_nodes/radial_clearance_m arrays")
    if np.any(pnodes<1) or np.any(pnodes>nn) or np.any(cnodes<1) or np.any(cnodes>nn):
        raise ValueError(f"A8 probe/clearance nodes must be one-based values in 1..{nn}")
    if not np.isfinite(pang).all():
        raise ValueError("A8 probe angles must be finite radians")
    if not np.isfinite(radial).all() or np.any(radial<=0):
        raise ValueError("A8 running radial clearances must be finite and > 0 m")

    ptags=tuple(str(x) for x in (probe_tags or [f"Probe {i+1}" for i in range(len(pnodes))]))
    ctags=tuple(str(x) for x in (clearance_tags or [f"Node {n}" for n in cnodes]))
    if len(ptags)!=len(pnodes) or len(ctags)!=len(cnodes):
        raise ValueError("A8 probe/clearance tag counts must match their node arrays")

    mode=int(mode);num_modes=int(num_modes)
    if mode<0 or num_modes<4 or num_modes%2 or num_modes>64:
        raise ValueError("A8 mode must be >=0 and num_modes must be even in 4..64")

    explicit=unbalance_nodes is not None
    if explicit:
        if unbalance_magnitude_kg_m is None or unbalance_phase_rad is None:
            raise ValueError("unbalance_magnitude_kg_m and unbalance_phase_rad are required with unbalance_nodes")
        un=np.asarray(unbalance_nodes,dtype=np.int32)
        um=np.asarray(unbalance_magnitude_kg_m,dtype=np.float64)
        up=np.asarray(unbalance_phase_rad,dtype=np.float64)
        if un.ndim!=1 or len(un)<1 or len(un)!=len(um) or len(un)!=len(up):
            raise ValueError("explicit unbalance node/magnitude/phase arrays must be equal and non-empty")
        if np.any(un<1) or np.any(un>nn) or not np.isfinite(um).all() or np.any(um<0) or not np.isfinite(up).all():
            raise ValueError("invalid explicit unbalance node/magnitude/phase")
    else:
        un=np.empty(0,dtype=np.int32);um=np.empty(0);up=np.empty(0)

    cap_enabled=scale_factor_cap is not None
    cap=0.0 if scale_factor_cap is None else float(scale_factor_cap)
    if cap_enabled and (not np.isfinite(cap) or cap<=0):
        raise ValueError("scale_factor_cap must be finite and > 0 when supplied")

    # A3 synchronous response authority: Omega == excitation frequency at every
    # point, including native interpolation of coefficient/map-backed supports.
    z,sh,di,bnodes,coeff,_,_,policy,_,bearing_metadata=prepare(
        backend,model,speed,speed=None,vector_response=True
    )
    if policy!="synchronous":
        raise SolverLibraryError("A8 bearing preparation violated synchronous response policy")
    n2,z2,sh2,di2,be_nmc=backend._arrays(
        model,speed_rad_s=nmc,frequency_rad_s=nmc
    )
    if n2!=nn or sh2.shape!=sh.shape or di2.shape!=di.shape or be_nmc.shape[1]!=len(bnodes):
        raise SolverLibraryError("A8 Nmc support materialization is inconsistent with response support count")

    required,full=configure_clearance(backend.lib)
    maxout=ct.c_int()
    status=required(nn,len(speed),len(pnodes),len(cnodes),ct.byref(maxout))
    if status:
        raise ValueError(f"A8 size query rejected input with status={status}")
    maxout=int(maxout.value)
    ub_nodes_in=np.zeros(maxout,dtype=np.int32)
    ub_mag_in=np.zeros(maxout,dtype=np.float64)
    ub_phase_in=np.zeros(maxout,dtype=np.float64)
    if explicit:
        if len(un)>maxout:raise ValueError("too many explicit unbalance locations for A8")
        ub_nodes_in[:len(un)]=un;ub_mag_in[:len(un)]=um;ub_phase_in[:len(un)]=up

    nout=ct.c_int();mode_index=ct.c_int();mode_frequency=ct.c_double()
    ub_nodes=np.zeros(maxout,dtype=np.int32);ub_mag=np.zeros(maxout);ub_phase=np.zeros(maxout)
    probe_response=np.empty((len(pnodes),len(speed)),dtype=np.float64,order="F")
    vibration_limit=ct.c_double();max_probe=ct.c_double();scale=ct.c_double()
    diameter=np.empty(len(cnodes));clear_resp=np.empty((len(cnodes),len(speed)),dtype=np.float64,order="F")
    max_clear=np.empty(len(cnodes));speed_at=np.empty(len(cnodes));passed=np.empty(len(cnodes),dtype=np.int32)
    p=backend._ptr
    status=full(
        nn,p(z),sh.shape[1],p(sh),di.shape[1],p(di),
        len(bnodes),backend._iptr(bnodes),p(coeff),p(be_nmc),
        len(speed),p(speed),nma,nmc,
        len(pnodes),backend._iptr(pnodes),p(pang),
        len(cnodes),backend._iptr(cnodes),p(radial),
        int(explicit),len(un),backend._iptr(ub_nodes_in),p(ub_mag_in),p(ub_phase_in),
        mode,num_modes,int(cap_enabled),cap,maxout,
        ct.byref(nout),backend._iptr(ub_nodes),p(ub_mag),p(ub_phase),
        ct.byref(mode_index),ct.byref(mode_frequency),
        p(probe_response),ct.byref(vibration_limit),ct.byref(max_probe),ct.byref(scale),
        p(diameter),p(clear_resp),p(max_clear),p(speed_at),backend._iptr(passed),
    )
    if status:
        reason={
            10:"invalid A8 dimensions/input",
            20:"invalid probe response or unavailable API 617 mode/topology",
            30:"native forced-response/modal/static solve failure",
        }.get(status,"native failure")
        raise SolverLibraryError(f"A8 rd_clearance_v1 returned status={status}: {reason}")
    nout=int(nout.value)
    if nout<1 or nout>maxout:
        raise SolverLibraryError("A8 native unbalance count violated ABI sizing")
    arrays=[probe_response,diameter,clear_resp,max_clear,speed_at,ub_mag[:nout],ub_phase[:nout]]
    if not all(np.isfinite(a).all() for a in arrays):
        raise SolverLibraryError("A8 native result contains NaN/Inf")

    return dict(
        speed_range_rad_s=speed,
        minimum_allowable_speed_rad_s=nma,
        maximum_continuous_speed_rad_s=nmc,
        unbalance_nodes=np.asarray(ub_nodes[:nout],dtype=int),
        unbalance_magnitude_kg_m=np.asarray(ub_mag[:nout],dtype=float),
        unbalance_phase_rad=np.asarray(ub_phase[:nout],dtype=float),
        probe_tags=ptags,
        probe_nodes=np.asarray(pnodes,dtype=int),
        probe_angles_rad=np.asarray(pang,dtype=float),
        probe_response_m_pp=probe_response,
        vibration_limit_m_pp=float(vibration_limit.value),
        max_probe_amplitude_m_pp=float(max_probe.value),
        scale_factor=float(scale.value),
        clearance_tags=ctags,
        clearance_nodes=np.asarray(cnodes,dtype=int),
        clearance_positions_m=np.asarray([model.nodes[n-1].z_m for n in cnodes],dtype=float),
        diametral_clearance_m=np.asarray(diameter,dtype=float),
        clearance_response_m_pp=clear_resp,
        max_clearance_response_m_pp=np.asarray(max_clear,dtype=float),
        speed_at_max_response_rad_s=np.asarray(speed_at,dtype=float),
        passed=np.asarray(passed,dtype=bool),
        scale_factor_cap=None if not cap_enabled else cap,
        mode=None if explicit else mode,
        mode_index=None if explicit else int(mode_index.value),
        mode_frequency_rad_s=None if explicit else float(mode_frequency.value),
        bearing_evaluation=bearing_metadata,
    )
