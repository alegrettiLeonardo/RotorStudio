from dataclasses import dataclass,field
import numpy as np
from drm_core.solver.facade import SolverFacade

ROSS_A5_AUTHORITY="6320eab9f890f1b3cc1710d508b446fe063ca68d"

@dataclass(frozen=True)
class UCSResult:
    stiffness_range_exponents:np.ndarray
    stiffness_log_n_m:np.ndarray
    natural_frequency_rad_s:np.ndarray
    bearing_speed_rad_s:np.ndarray
    bearing_kxx_n_m:np.ndarray
    bearing_kyy_n_m:np.ndarray
    intersection_stiffness_n_m:np.ndarray
    intersection_speed_rad_s:np.ndarray
    intersection_mode_index:np.ndarray
    intersection_coefficient:np.ndarray
    critical_eigenvalue_real:np.ndarray
    critical_eigenvalue_imag:np.ndarray
    critical_wn_rad_s:np.ndarray
    critical_wd_rad_s:np.ndarray
    critical_damping_ratio:np.ndarray
    critical_log_dec:np.ndarray
    synchronous:bool
    bearing_evaluation:list
    bearing_speed_policy:str
    coefficient_families:tuple[str,...]
    metadata:dict=field(default_factory=dict)

def run_ucs(model,stiffness_range_exponents,num=20,num_modes=16,bearing_speed_range=None,synchronous=False,library_path=None):
    values=SolverFacade(library_path).ucs(model,stiffness_range_exponents,num,num_modes,bearing_speed_range,synchronous)
    return UCSResult(**values,metadata=dict(
        model_hash=model.model_hash(),backend="Fortran2018/ctypes",native_abi="rd_ucs_v1",
        ross_authority=ROSS_A5_AUTHORITY,analysis="undamped_critical_speed_map",
        stiffness_range_semantics="base-10 exponents; grid=logspace(start,stop,num)",
        temporary_rotor="shaft damping removed; seals excluded; all supports isotropic kxx=kyy=k,c=0",
        map_speed_rad_s=0.0,critical_modal="standard non-Rouch modal at each nonzero critical speed",
        dof_order=["x","y","alpha","beta"],point_mass="out_of_scope",linked_housing="out_of_scope",
        rated_speed_policy="explicit stiffness exponent range required; no rated_w equivalent in RotorStudio domain",
    ))
