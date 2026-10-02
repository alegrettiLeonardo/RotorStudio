"""I9 orchestration for the qualified iRdin rotor-bearing-support path.

All eigenvalue and dynamic-response solves remain native. Python only prepares
already-qualified domain inputs, calls native bearing interpolation/assembly,
and applies the documented legacy response-coordinate rotation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
import numpy as np

from drm_core.domain.model import Disk, RotorModel, ResponseProbe
from drm_core.domain.bearings import CoefficientBearing
from drm_core.solver.facade import SolverFacade
from drm_core.solver.irdin_support_global import (
    assemble_support_global_matrices,
    support_arrays,
)
from drm_core.solver.irdin_support_analysis import (
    IrdinExpandedModal,
    IrdinExpandedResponse,
    expanded_modal,
    expanded_synchronous,
)


@dataclass(frozen=True)
class IrdinExpandedState:
    speed_rad_s: float
    M: np.ndarray
    C: np.ndarray
    G: np.ndarray
    K: np.ndarray
    bearing_metadata: tuple[dict, ...]


@dataclass(frozen=True)
class IrdinProbeSweep:
    speed_rad_s: np.ndarray
    full_response: np.ndarray
    probe_response: np.ndarray
    residual: np.ndarray


def _require_component(project, name: str, allowed: tuple[str, ...]) -> None:
    value=(project.metadata.get("numerical_readiness",{})
           .get("components",{}).get(name,"NOT_QUALIFIED"))
    if value not in allowed:
        raise ValueError(f"I9 requires {name} in {allowed}; received {value!r}")


def _check_project(project) -> None:
    if project.metadata.get("source_format")!="iRdin/VB6 INI":
        raise ValueError("I9 requires an imported iRdin/VB6 project")
    _require_component(project,"mass_native_materialization",("PASS_I7_DISK_MATERIALIZATION","NOT_APPLICABLE"))
    _require_component(project,"bearing_extrapolation",("PASS_I5_LEGACY_POLICY","NOT_APPLICABLE"))
    _require_component(project,"support_semantics",("PASS_I3_DOMAIN_ONLY","NOT_APPLICABLE"))
    _require_component(project,"support_native_assembly",("PASS_I8_GLOBAL_MATRICES",))
    _require_component(project,"unbalance",("PASS_I6_LEGACY_UNBALANCE","NOT_APPLICABLE"))
    _require_component(project,"probes",("PASS_I6_RESPONSE_PROBES","NOT_APPLICABLE"))
    if not project.model.supports:
        raise ValueError("I9 declared scope requires at least one flexible support")
    if len(project.model.advanced_bearings)<max(s.bearing_number for s in project.model.supports):
        raise ValueError("I9 support references a missing advanced bearing")


def build_expanded_state(project, speed_rad_s: float, *, library_path: str|Path|None=None) -> IrdinExpandedState:
    _check_project(project)
    speed=float(speed_rad_s)
    if not math.isfinite(speed) or speed<0:
        raise ValueError("I9 rotor speed must be finite and >= 0")
    model=project.model
    rotor_disks=list(model.disks)
    for coupling in model.half_couplings:
        rotor_disks.append(Disk.inertial(
            coupling.node,
            coupling.mass_kg,
            coupling.diametral_inertia_kgm2,
            coupling.polar_inertia_kgm2,
        ))
    rotor=RotorModel(
        nodes=list(model.nodes),
        shafts=list(model.shafts),
        disks=rotor_disks,
    )
    facade=SolverFacade(library_path)
    # Existing native assembly returns (M,C,K,G); C already contains Omega*G.
    mr,cr,kr,gr=facade.assemble(rotor,speed)
    nodes,mass,ks,cs=support_arrays(model.supports)
    kb=[];cb=[];details=[]
    for support in model.supports:
        bearing=model.advanced_bearings[support.bearing_number-1]
        if type(bearing) is not CoefficientBearing:
            raise ValueError(
                f"I9 initial iRdin scope requires a precomputed CoefficientBearing; received {type(bearing).__name__}"
            )
        if bearing.frequency_rad_s:
            raise ValueError("I9 initial iRdin scope accepts only 1-D speed-dependent coefficient tables")
        if bearing.interpolation!="irdin_lagrange":
            raise ValueError(
                f"I9 requires the qualified iRdin interpolation policy; received {bearing.interpolation!r}"
            )
        if int(bearing.node)!=int(support.node):
            raise ValueError(
                f"I9 support/bearing node mismatch: support node {support.node}, bearing node {bearing.node}"
            )
        evaluation=facade.advanced_bearing(
            bearing,
            speed,
            frequency_rad_s=speed,
        )
        if np.max(np.abs(evaluation.M))>1e-14:
            raise ValueError("I9 initial scope cannot silently discard nonzero bearing mass matrix")
        kb.append(np.asarray(evaluation.K,dtype=float))
        cb.append(np.asarray(evaluation.C,dtype=float))
        details.append(dict(evaluation.details)|{
            "bearing_number":int(support.bearing_number),
            "node":int(support.node),
            "model_family":evaluation.model_family,
        })
    expanded=assemble_support_global_matrices(
        rotor_M=mr,rotor_C=cr,rotor_G=gr,rotor_K=kr,
        support_nodes=nodes,support_masses=mass,
        bearing_K=np.asarray(kb),bearing_C=np.asarray(cb),
        support_K=ks,support_C=cs,
        library_path=library_path,
    )
    return IrdinExpandedState(
        speed,
        expanded.M,
        expanded.C,
        expanded.G,
        expanded.K,
        tuple(details),
    )


def run_irdin_modal(project, speed_rad_s: float, *, library_path: str|Path|None=None) -> IrdinExpandedModal:
    state=build_expanded_state(project,speed_rad_s,library_path=library_path)
    return expanded_modal(state.M,state.C,state.K,library_path=library_path)


def run_irdin_synchronous(project, speed_rad_s: float, *, library_path: str|Path|None=None) -> IrdinExpandedResponse:
    state=build_expanded_state(project,speed_rad_s,library_path=library_path)
    return expanded_synchronous(
        state.M,state.C,state.K,
        nnode=len(project.model.nodes),
        omega_rad_s=float(speed_rad_s),
        forces=list(project.model.forces),
        library_path=library_path,
    )


def rotate_probe_pair(x: complex, z: complex, angle_rad: float) -> tuple[complex,complex]:
    """Exact legacy vrotate convention from frontend_rotordin resp_f/matfun."""
    angle=float(angle_rad)
    if not math.isfinite(angle):
        raise ValueError("probe angle must be finite")
    ca=math.cos(angle);sa=math.sin(angle)
    return x*ca+z*sa, z*ca-x*sa


def probe_value(response, probe: ResponseProbe) -> complex:
    q=np.asarray(response,dtype=np.complex128)
    base=4*int(probe.node)-4
    if base<0 or base+1>=q.size:
        raise ValueError("probe node is outside rotor response vector")
    xr,zr=rotate_probe_pair(q[base],q[base+1],probe.orientation_rad)
    if probe.coordinate==1:
        return complex(xr)
    if probe.coordinate==2:
        return complex(zr)
    raise ValueError(f"unsupported iRdin probe coordinate={probe.coordinate}")


def run_irdin_synchronous_sweep(project, speed_rad_s, *, library_path: str|Path|None=None) -> IrdinProbeSweep:
    speeds=np.asarray(speed_rad_s,dtype=np.float64)
    if speeds.ndim!=1 or speeds.size<1 or not np.isfinite(speeds).all() or np.any(speeds<0):
        raise ValueError("I9 speed sweep must be a nonempty finite nonnegative vector")
    full=[];probe=[];residual=[]
    for speed in speeds:
        solved=run_irdin_synchronous(project,float(speed),library_path=library_path)
        full.append(solved.response)
        probe.append([probe_value(solved.response,p) for p in project.model.probes])
        residual.append(solved.residual)
    return IrdinProbeSweep(
        speeds.copy(),
        np.column_stack(full),
        np.asarray(probe,dtype=np.complex128).T,
        np.asarray(residual,dtype=np.float64),
    )


__all__=[
    "IrdinExpandedState","IrdinProbeSweep","build_expanded_state",
    "run_irdin_modal","run_irdin_synchronous","run_irdin_synchronous_sweep",
    "rotate_probe_pair","probe_value",
]
