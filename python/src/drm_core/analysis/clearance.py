from __future__ import annotations
from dataclasses import dataclass,field
import numpy as np
from drm_core.solver.facade import SolverFacade

ROSS_A8_AUTHORITY="6320eab9f890f1b3cc1710d508b446fe063ca68d"


@dataclass(frozen=True)
class ClearanceResult:
    speed_range_rad_s:np.ndarray
    minimum_allowable_speed_rad_s:float
    maximum_continuous_speed_rad_s:float
    unbalance_nodes:np.ndarray
    unbalance_magnitude_kg_m:np.ndarray
    unbalance_phase_rad:np.ndarray
    probe_tags:tuple[str,...]
    probe_nodes:np.ndarray
    probe_angles_rad:np.ndarray
    probe_response_m_pp:np.ndarray
    vibration_limit_m_pp:float
    max_probe_amplitude_m_pp:float
    scale_factor:float
    clearance_tags:tuple[str,...]
    clearance_nodes:np.ndarray
    clearance_positions_m:np.ndarray
    diametral_clearance_m:np.ndarray
    clearance_response_m_pp:np.ndarray
    max_clearance_response_m_pp:np.ndarray
    speed_at_max_response_rad_s:np.ndarray
    passed:np.ndarray
    scale_factor_cap:float|None
    mode:int|None
    mode_index:int|None
    mode_frequency_rad_s:float|None
    bearing_evaluation:list
    metadata:dict=field(default_factory=dict)

    @property
    def clearance_limit_m(self):
        return .75*np.asarray(self.diametral_clearance_m,float)

    @property
    def percent_of_limit(self):
        return 100*np.asarray(self.max_clearance_response_m_pp,float)/self.clearance_limit_m


def run_clearance(model,library_path=None,**kwargs)->ClearanceResult:
    values=SolverFacade(library_path).clearance(model,**kwargs)
    return ClearanceResult(**values,metadata={
        "model_hash":model.model_hash(),
        "backend":"Fortran2018/ctypes",
        "native_abi":"rd_clearance_v1",
        "ross_authority":ROSS_A8_AUTHORITY,
        "analysis":"api617_close_clearance",
        "speed_axis":"sorted unique union of user sweep with Nma/Nmc",
        "response":"synchronous full-order A3; Omega=omega at every point",
        "probe_amplitude":"2*abs(qx*cos(theta)+qy*sin(theta)) [m pk-pk]",
        "vibration_limit":"min(25.4,25.4*sqrt(12000/Nmc_rpm))*1e-6 m pk-pk",
        "clearance_response":"2*Scc*orbit major semi-axis [m pk-pk]",
        "clearance_limit":"0.75*(2*radial running clearance)",
        "pass_semantics":"strict max_response < clearance_limit",
        "clearance_domain":"analysis-local explicit one-based nodes and radial running clearances",
        "dof_order":["x","y","alpha","beta"],
    })
