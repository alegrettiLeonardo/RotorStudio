from dataclasses import dataclass,field
import numpy as np
from drm_core.solver.facade import SolverFacade

@dataclass(frozen=True)
class ForcedResponseResult:
    frequency_rad_s:np.ndarray
    rotor_speed_rad_s:np.ndarray
    force_complex:np.ndarray
    displacement:np.ndarray
    velocity:np.ndarray
    acceleration:np.ndarray
    residual:np.ndarray
    condition_estimate:np.ndarray
    coefficient_policy:str
    metadata:dict=field(default_factory=dict)

def run_forced_response(model,frequency_rad_s=None,force_real=None,force_imag=None,speed=None,modes=None,library_path=None):
    if frequency_rad_s is None: raise ValueError('Forced Response requires explicit frequency_rad_s; no automatic modal sweep.')
    result=SolverFacade(library_path).forced_response(model,frequency_rad_s,force_real,force_imag,speed)
    f,omega,force,q,v,a,res,cond,policy,bearings=result
    return ForcedResponseResult(f,omega,force,q,v,a,res,cond,policy,dict(model_hash=model.model_hash(),native_abi='rd_forced_response_v1',backend='Fortran2018/ctypes',omega_policy=policy,dof_order=['x','y','alpha','beta'],array_order='dof,frequency',dof_indexing='zero-based',ross_authority='6320eab9f890f1b3cc1710d508b446fe063ca68d',bearing_evaluation=bearings,full_order=True,modes_argument_ignored=None if modes is None else list(modes),force_units=['N','N','N m','N m'],displacement_units=['m','m','rad','rad'],velocity_units=['m/s','m/s','rad/s','rad/s'],acceleration_units=['m/s²','m/s²','rad/s²','rad/s²'],complex_convention='real in-phase, imaginary quadrature; physical response Re(q exp(jωt))',condition_norm='LAPACK ZGECON 1-norm estimate'))
