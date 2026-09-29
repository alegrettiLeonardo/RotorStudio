"""Thin A7 API 617 unbalance placement binding.

Production forward-mode selection, orbit/lobe logic, static-load selection,
overhung-mass evaluation and API 617 magnitude/phase equations are native
Fortran. Python validates the declared scope, materializes already-qualified
bearing coefficients at Nmc and marshals arrays.
"""
from __future__ import annotations

import ctypes as ct
import warnings
import numpy as np

from drm_core.domain.model import ShaftElement
from drm_core.domain.bearings import CoefficientBearing
from .ffi import configure_api617_unbalance,SolverLibraryError


ROSS_SHA="6320eab9f890f1b3cc1710d508b446fe063ca68d"


def _validate(model,mode,maximum_continuous_speed_rad_s,num_modes):
    speed=float(maximum_continuous_speed_rad_s)
    if not np.isfinite(speed) or speed<=0:
        raise ValueError(
            f"maximum_continuous_speed_rad_s={maximum_continuous_speed_rad_s!r}; "
            "expected finite > 0"
        )
    mode=int(mode)
    if mode<0:
        raise ValueError(f"mode={mode}; expected forward-mode index >= 0")
    num_modes=int(num_modes)
    if num_modes<4 or num_modes%2 or num_modes>64:
        raise ValueError("num_modes must be an even integer in 4..64")

    nn=len(model.nodes)
    if nn<2 or nn>128 or [n.number for n in model.nodes]!=list(range(1,nn+1)):
        raise ValueError("A7 requires 2..128 consecutive one-based shaft nodes")
    if model.rotors or model.bend:
        raise ValueError("A7 API 617 placement is a single straight shaft line")
    if len(model.shafts)!=nn-1:
        raise ValueError("A7 requires one shaft element between each consecutive node")
    for i,shaft in enumerate(model.shafts):
        if not isinstance(shaft,ShaftElement) or shaft.shaft_type!=2 or (shaft.node1,shaft.node2)!=(i+1,i+2):
            raise ValueError("A7 qualified shaft scope is the ordered circular type-2 4-DOF chain")
        if shaft.axial_force_n!=0 or shaft.torque_nm!=0:
            raise ValueError("A7 axial preload and shaft torque are outside declared scope")
    if any(d.disk_type not in (1,2) for d in model.disks):
        raise ValueError("A7 supports disk types 1/2 only")
    if not model.bearings and not model.advanced_bearings:
        raise ValueError("A7 requires at least one radial support")
    for b in model.bearings:
        if b.bearing_type not in (3,5):
            raise ValueError(
                f"bearing type {b.bearing_type} at node {b.node}; "
                "A7 supports legacy radial type 3/5 only"
            )
    for b in model.advanced_bearings:
        if not isinstance(b,CoefficientBearing):
            raise ValueError(
                f"{type(b).__name__}: A7 accepts qualified coefficient/map-backed "
                "bearings only; generate an operating map first"
            )
    support_nodes=sorted(
        {b.node for b in model.bearings}
        | {b.node for b in model.advanced_bearings}
    )
    if len(support_nodes)<2:
        raise ValueError(
            f"A7 received support nodes {support_nodes}; expected at least two "
            "distinct radial support nodes for static-load recovery"
        )
    return speed,mode,num_modes


def execute(
    backend,
    model,
    mode:int,
    maximum_continuous_speed_rad_s:float,
    num_modes:int=12,
):
    speed,mode,num_modes=_validate(
        model,mode,maximum_continuous_speed_rad_s,num_modes
    )
    # ROSS evaluates modal coefficients synchronously at Nmc. Materialize the
    # same already-qualified bearing tables into the native 4-DOF bridge.
    n,z,sh,di,be=backend._arrays(
        model,speed_rad_s=speed,frequency_rad_s=speed
    )
    if not all(np.isfinite(a).all() for a in (z,sh,di,be)):
        raise ValueError("A7 input contains NaN/Inf")

    required,full=configure_api617_unbalance(backend.lib)
    nphysical=ct.c_int();maxout=ct.c_int()
    status=required(n,num_modes,ct.byref(nphysical),ct.byref(maxout))
    if status:
        raise ValueError(f"A7 size query rejected inputs with status={status}")
    np_mode=int(nphysical.value);max_out=int(maxout.value)
    if np_mode!=num_modes//2 or max_out!=n:
        raise SolverLibraryError("A7 native sizing contract is inconsistent")

    nout=ct.c_int();mode_index=ct.c_int();mode_frequency=ct.c_double()
    nodes=np.empty(max_out,dtype=np.int32)
    magnitude=np.empty(max_out,dtype=np.float64)
    phase=np.empty(max_out,dtype=np.float64)
    static_load=np.empty(max_out,dtype=np.float64)
    whirl_ratio=np.empty(np_mode,dtype=np.float64)
    major=np.empty(n,dtype=np.float64)
    kappa=np.empty(n,dtype=np.float64)
    major_angle=np.empty(n,dtype=np.float64)
    projection_real=np.empty(n,dtype=np.float64)
    sign=np.empty(n,dtype=np.float64)

    status=full(
        n,backend._ptr(z),sh.shape[1],backend._ptr(sh),
        di.shape[1],backend._ptr(di),be.shape[1],backend._ptr(be),
        speed,mode,num_modes,max_out,
        ct.byref(nout),backend._iptr(nodes),
        backend._ptr(magnitude),backend._ptr(phase),backend._ptr(static_load),
        ct.byref(mode_index),ct.byref(mode_frequency),
        backend._ptr(whirl_ratio),backend._ptr(major),backend._ptr(kappa),
        backend._ptr(major_angle),backend._ptr(projection_real),backend._ptr(sign),
    )
    if status:
        reason={
            10:"invalid API 617 input",
            20:"requested forward mode unavailable or unsupported topology",
            30:"native modal/static solve failure",
        }.get(status,"native failure")
        raise SolverLibraryError(
            f"A7 rd_api617_unbalance_v1 returned status={status}: {reason}"
        )
    if not np.any(np.asarray(whirl_ratio)>0.25) and np.any(np.asarray(whirl_ratio)>0.0):
        warnings.warn(
            "No mode with predominantly forward orbits was found (all whirl "
            "ratios are below 0.25); using the modes with positive whirl ratio instead.",
            UserWarning,
            stacklevel=2,
        )
    count=int(nout.value)
    if count<1 or count>max_out:
        raise SolverLibraryError("A7 native unbalance count violated sizing contract")
    arrays=[
        nodes[:count],magnitude[:count],phase[:count],static_load[:count],
        whirl_ratio,major,kappa,major_angle,projection_real,sign,
    ]
    if not all(np.isfinite(np.asarray(a,dtype=float)).all() for a in arrays):
        raise SolverLibraryError("A7 native output contains NaN/Inf")

    return dict(
        nodes=np.asarray(nodes[:count],dtype=int),
        unbalance_magnitude_kg_m=np.asarray(magnitude[:count],dtype=float),
        unbalance_phase_rad=np.asarray(phase[:count],dtype=float),
        static_load_kg=np.asarray(static_load[:count],dtype=float),
        mode_index=int(mode_index.value),
        mode_frequency_rad_s=float(mode_frequency.value),
        whirl_ratio=np.asarray(whirl_ratio,dtype=float),
        mode_major_axis=np.asarray(major,dtype=float),
        mode_kappa=np.asarray(kappa,dtype=float),
        mode_major_angle_rad=np.asarray(major_angle,dtype=float),
        reference_projection_product_real=np.asarray(projection_real,dtype=float),
        mode_sign=np.asarray(sign,dtype=float),
        maximum_continuous_speed_rad_s=speed,
        requested_forward_mode=mode,
    )
