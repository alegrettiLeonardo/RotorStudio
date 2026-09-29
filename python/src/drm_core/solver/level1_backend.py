"""Thin A6 Level 1 binding.

Production Q sweep, matrix modification, eigensolutions, whirl classification and
first-non-backward mode selection are native Fortran. Python validates the
qualified scope, evaluates already-qualified bearing coefficients at the fixed
synchronous operating point and marshals arrays.
"""
from __future__ import annotations
import ctypes as ct
import numpy as np

from drm_core.domain.model import ShaftElement
from drm_core.domain.bearings import CoefficientBearing
from .ffi import configure_level1, SolverLibraryError


ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"


def _validate(model,rotor_speed_rad_s,cross_coupling_node,stiffness_range_n_m,num):
    speed=float(rotor_speed_rad_s)
    if not np.isfinite(speed) or speed<0:
        raise ValueError(f"rotor_speed_rad_s={rotor_speed_rad_s!r}; expected finite >= 0")
    nn=len(model.nodes)
    if nn<2 or nn>128 or [n.number for n in model.nodes]!=list(range(1,nn+1)):
        raise ValueError("Level 1 requires 2..128 consecutive one-based shaft nodes")
    node=int(cross_coupling_node)
    if node<1 or node>nn:
        raise ValueError(f"cross_coupling_node={node}; expected 1..{nn}")
    if stiffness_range_n_m is None:
        raise ValueError(
            "stiffness_range_n_m is required in A6. Frozen ROSS has an ambiguous "
            "default-range behavior; RotorStudio does not infer it."
        )
    try:q0,q1=map(float,stiffness_range_n_m)
    except Exception as exc:
        raise ValueError("stiffness_range_n_m must contain exactly two numeric N/m values") from exc
    if not np.isfinite([q0,q1]).all() or q0<0 or q1<=q0:
        raise ValueError(
            f"stiffness_range_n_m=({q0:g},{q1:g}); expected finite 0 <= start < stop"
        )
    num=int(num)
    if num<2 or num>4096:
        raise ValueError("Level 1 num must be 2..4096")
    if model.rotors or model.bend:
        raise ValueError("A6 Level 1 is a single straight shaft line; coaxial/pre-bend is out of scope")
    if len(model.shafts)!=nn-1:
        raise ValueError("A6 Level 1 requires one shaft element between each consecutive node")
    for i,shaft in enumerate(model.shafts):
        if not isinstance(shaft,ShaftElement) or shaft.shaft_type!=2 or (shaft.node1,shaft.node2)!=(i+1,i+2):
            raise ValueError("A6 Level 1 qualified shaft scope is the ordered circular type-2 4-DOF chain")
        if shaft.axial_force_n!=0 or shaft.torque_nm!=0:
            raise ValueError("A6 Level 1 axial preload and shaft torque are outside declared scope")
    if any(d.disk_type not in (1,2) for d in model.disks):
        raise ValueError("A6 Level 1 supports gyroscopic disk types 1/2 only")
    if not model.bearings and not model.advanced_bearings:
        raise ValueError("A6 Level 1 requires at least one existing radial support")
    for b in model.bearings:
        if b.bearing_type not in (3,5):
            raise ValueError(
                f"bearing type {b.bearing_type} at node {b.node}; A6 supports legacy radial type 3/5 only"
            )
    for b in model.advanced_bearings:
        if not isinstance(b,CoefficientBearing):
            raise ValueError(
                f"{type(b).__name__}: A6 initial scope accepts qualified coefficient/map-backed bearings only"
            )
    return speed,node,q0,q1,num


def execute(backend,model,rotor_speed_rad_s,cross_coupling_node,stiffness_range_n_m,num=5):
    speed,node,q0,q1,num=_validate(
        model,rotor_speed_rad_s,cross_coupling_node,stiffness_range_n_m,num
    )
    # Frozen run_level1 uses the rated rotor speed for the modal solve and
    # synchronous bearing lookup. Materialize those already-qualified
    # coefficients once; Q changes only the additive cross-coupling matrix.
    n,z,sh,di,be=backend._arrays(
        model,speed_rad_s=speed,frequency_rad_s=speed
    )
    if be.shape[1]<1:
        raise ValueError("Level 1 requires at least one materialized support")
    if not all(np.isfinite(a).all() for a in (z,sh,di,be)):
        raise ValueError("Level 1 input contains NaN/Inf")

    required,matrix_fn,full_fn=configure_level1(backend.lib)
    nm=ct.c_int();ns=ct.c_int()
    status=required(n,num,ct.byref(nm),ct.byref(ns))
    if status:
        raise ValueError(f"Level 1 size query rejected input with status={status}")
    nmode=int(nm.value)
    if nmode<1 or nmode>6 or int(ns.value)!=8*n:
        raise SolverLibraryError("Level 1 native sizing contract is inconsistent")

    q=np.empty(num,dtype=np.float64)
    selected=np.empty(num,dtype=np.float64)
    selected_mode=np.empty(num,dtype=np.int32)
    directions=np.empty((nmode,num),dtype=np.int32,order="F")
    modal=[np.empty((nmode,num),dtype=np.float64,order="F") for _ in range(6)]
    p=backend._ptr
    status=full_fn(
        n,p(z),sh.shape[1],p(sh),di.shape[1],p(di),be.shape[1],p(be),
        speed,node,q0,q1,num,nmode,
        p(q),p(selected),backend._iptr(selected_mode),backend._iptr(directions),
        *[p(x) for x in modal],
    )
    if status:
        reason={10:"invalid Level 1 input",20:"unsupported topology or no admissible non-backward mode",30:"native eigensolver failure"}.get(status,"native failure")
        raise SolverLibraryError(f"Level 1 rd_level1_v1 returned status={status}: {reason}")
    arrays=[q,selected,selected_mode,directions,*modal]
    if not all(np.isfinite(np.asarray(a,dtype=float)).all() for a in arrays):
        raise SolverLibraryError("Level 1 native output contains NaN/Inf")
    expected=np.linspace(q0,q1,num,dtype=float)
    if not np.array_equal(q,expected):
        raise SolverLibraryError("Level 1 native Q grid violated exact linear linspace semantics")
    return dict(
        cross_coupled_stiffness_n_m=q,
        log_dec=selected,
        selected_mode_index=selected_mode.astype(int)-1,
        mode_direction_code=directions,
        eigenvalue_real=modal[0],
        eigenvalue_imag=modal[1],
        natural_frequency_rad_s=modal[2],
        damped_frequency_rad_s=modal[3],
        damping_ratio=modal[4],
        modal_log_dec=modal[5],
        rotor_speed_rad_s=speed,
        cross_coupling_node=node,
    )


def matrices(backend,model,rotor_speed_rad_s,cross_coupling_node,Q_n_m):
    speed,node,_,_,_=_validate(
        model,rotor_speed_rad_s,cross_coupling_node,(0.0,max(float(Q_n_m),1.0)),2
    )
    Q=float(Q_n_m)
    if not np.isfinite(Q) or Q<0:
        raise ValueError("Q_n_m must be finite and >= 0")
    n,z,sh,di,be=backend._arrays(model,speed_rad_s=speed,frequency_rad_s=speed)
    _,matrix_fn,_=configure_level1(backend.lib)
    outs=[np.empty((4*n,4*n),dtype=np.float64,order="F") for _ in range(4)]
    status=matrix_fn(
        n,backend._ptr(z),sh.shape[1],backend._ptr(sh),di.shape[1],backend._ptr(di),
        be.shape[1],backend._ptr(be),speed,node,Q,*[backend._ptr(x) for x in outs]
    )
    if status:
        raise SolverLibraryError(f"Level 1 rd_level1_matrix_v1 returned status={status}")
    if not all(np.isfinite(a).all() for a in outs):
        raise SolverLibraryError("Level 1 matrix sentinel contains NaN/Inf")
    return dict(zip(("M","C","G","K"),outs))
