"""Static result and orchestration. All load/solve/diagram physics is native."""
from dataclasses import dataclass,field
from datetime import datetime,timezone
import numpy as np
from drm_core.solver.facade import SolverFacade

@dataclass(frozen=True)
class StaticResult:
    displacement:np.ndarray
    displacement_y:np.ndarray
    reactions:np.ndarray
    shaft_weights:np.ndarray
    disk_loads:np.ndarray
    shear:np.ndarray
    bending_moment:np.ndarray
    station_positions:np.ndarray
    node_positions:np.ndarray
    disk_nodes:np.ndarray
    support_nodes:np.ndarray
    diagnostics:np.ndarray
    metadata:dict=field(default_factory=dict)

def run_static(model,library_path=None):
    q,reactions,sw,dw,shear,bending,stations,diagnostics,version=SolverFacade(library_path).static(model)
    return StaticResult(q,q[1::4].copy(),reactions,sw,dw,shear,bending,stations,
        np.asarray([n.z_m for n in model.nodes]),np.asarray([d.node for d in model.disks],dtype=int),
        np.asarray(sorted({b.node for b in model.bearings if b.bearing_type!=8}),dtype=int),diagnostics,
        dict(solver_version=version,native_abi='rd_static_v1',model_hash=model.model_hash(),
             timestamp=datetime.now(timezone.utc).isoformat(),backend='Fortran2018/ctypes',
             ross_authority='6320eab9f890f1b3cc1710d508b446fe063ca68d',
             scope='single circular shaft; simple radial supports; gravity only',
             dof_order=['x','y','alpha','beta'],node_indexing='one-based',units='SI'))
