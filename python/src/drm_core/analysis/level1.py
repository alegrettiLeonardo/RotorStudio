from __future__ import annotations
from dataclasses import dataclass,field
import numpy as np
from drm_core.solver.facade import SolverFacade

ROSS_A6_AUTHORITY="6320eab9f890f1b3cc1710d508b446fe063ca68d"
DIRECTION_LABELS={1:"Forward",2:"Mixed",3:"Backward"}


@dataclass(frozen=True)
class Level1Result:
    cross_coupled_stiffness_n_m:np.ndarray
    log_dec:np.ndarray
    selected_mode_index:np.ndarray
    mode_direction_code:np.ndarray
    eigenvalue_real:np.ndarray
    eigenvalue_imag:np.ndarray
    natural_frequency_rad_s:np.ndarray
    damped_frequency_rad_s:np.ndarray
    damping_ratio:np.ndarray
    modal_log_dec:np.ndarray
    rotor_speed_rad_s:float
    cross_coupling_node:int
    metadata:dict=field(default_factory=dict)

    @property
    def mode_direction(self)->np.ndarray:
        mapper=np.vectorize(lambda x:DIRECTION_LABELS.get(int(x),"Unknown"))
        return mapper(self.mode_direction_code)


def run_level1(
    model,
    rotor_speed_rad_s:float,
    cross_coupling_node:int,
    stiffness_range_n_m,
    num:int=5,
    library_path=None,
)->Level1Result:
    values=SolverFacade(library_path).level1(
        model,rotor_speed_rad_s,cross_coupling_node,stiffness_range_n_m,num
    )
    return Level1Result(**values,metadata={
        "model_hash":model.model_hash(),
        "backend":"Fortran2018/ctypes",
        "native_abi":"rd_level1_v1",
        "ross_authority":ROSS_A6_AUTHORITY,
        "analysis":"level_1_stability",
        "speed_policy":"explicit fixed rotor speed; synchronous bearing coefficients",
        "q_range_semantics":"explicit physical N/m; linear np.linspace equivalent",
        "cross_coupling":"Kxy=+Q; Kyx=-Q at explicit one-based node",
        "selection":"frozen ROSS first mode whose whirl direction is not Backward; no Q-branch tracking",
        "direction_codes":{"1":"Forward","2":"Mixed","3":"Backward"},
        "default_range_policy":"unsupported/fail-closed; explicit stiffness_range_n_m required",
        "dof_order":["x","y","alpha","beta"],
    })
