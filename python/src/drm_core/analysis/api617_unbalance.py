from __future__ import annotations
from dataclasses import dataclass,field
import numpy as np
from drm_core.solver.facade import SolverFacade

ROSS_A7_AUTHORITY="6320eab9f890f1b3cc1710d508b446fe063ca68d"


@dataclass(frozen=True)
class API617UnbalanceResult:
    nodes:np.ndarray
    unbalance_magnitude_kg_m:np.ndarray
    unbalance_phase_rad:np.ndarray
    static_load_kg:np.ndarray
    mode_index:int
    mode_frequency_rad_s:float
    whirl_ratio:np.ndarray
    mode_major_axis:np.ndarray
    mode_kappa:np.ndarray
    mode_major_angle_rad:np.ndarray
    reference_projection_product_real:np.ndarray
    mode_sign:np.ndarray
    maximum_continuous_speed_rad_s:float
    requested_forward_mode:int
    metadata:dict=field(default_factory=dict)


def run_api617_unbalance(
    model,
    mode:int,
    maximum_continuous_speed_rad_s:float,
    num_modes:int=12,
    library_path=None,
)->API617UnbalanceResult:
    values=SolverFacade(library_path).api617_unbalance(
        model,mode,maximum_continuous_speed_rad_s,num_modes
    )
    return API617UnbalanceResult(**values,metadata={
        "model_hash":model.model_hash(),
        "backend":"Fortran2018/ctypes",
        "native_abi":"rd_api617_unbalance_v1",
        "ross_authority":ROSS_A7_AUTHORITY,
        "analysis":"api617_unbalance_placement",
        "speed_policy":"explicit maximum continuous speed; synchronous coefficients",
        "mode_policy":"input indexes frozen ROSS forward-mode filtered list",
        "forward_whirl_ratio_threshold":0.25,
        "lobe_threshold_fraction":0.02,
        "inboard_antinode_threshold_fraction":0.10,
        "outboard_antinode_threshold_fraction":0.50,
        "unbalance_policy":"Ua=2*Ur; Ur=6350*W/Nmc g-mm below 25000 rpm else W/3.937 g-mm",
        "node_indexing":"one-based RotorStudio output; frozen ROSS authority nodes are zero-based",
        "dof_order":["x","y","alpha","beta"],
    })
