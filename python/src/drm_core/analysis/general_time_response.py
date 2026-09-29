from dataclasses import dataclass,field
import numpy as np
from drm_core.solver.facade import SolverFacade

@dataclass(frozen=True)
class GeneralTimeResponseResult:
    time_s:np.ndarray
    rotor_speed_rad_s:np.ndarray
    angular_acceleration_rad_s2:np.ndarray
    force_external:np.ndarray
    force:np.ndarray
    displacement:np.ndarray
    velocity:np.ndarray
    acceleration:np.ndarray
    iterations:np.ndarray
    residual:np.ndarray
    absolute_residual:np.ndarray
    condition_estimate:np.ndarray
    metadata:dict=field(default_factory=dict)

def run_general_time_response(model,time_s,force_real,speed=0.,weight=False,gamma=.5,beta=.25,tol=1e-6,library_path=None):
    *values,bearings=SolverFacade(library_path).general_time_response(model,time_s,force_real,speed,weight,gamma,beta,tol)
    return GeneralTimeResponseResult(*values,metadata=dict(model_hash=model.model_hash(),native_abi='rd_general_time_response_v1',backend='Fortran2018/ctypes',ross_authority='6320eab9f890f1b3cc1710d508b446fe063ca68d',method='newmark',newmark_type='simple',gamma=gamma,beta=beta,tol=tol,max_iterations=50,weight=weight,gravity_m_s2=-9.8065,initial_state='q0=v0=a0=0; t0 prescribed, not equilibrium solved',array_order='dof,time',dof_order=['x','y','alpha','beta'],force_units=['N','N','N m','N m'],coefficient_query='(Omega(t),Omega(t)); M constant',bearing_evaluation=bearings,condition_norm='LAPACK DGECON 1-norm estimate of J; t0 unavailable=0',cancellation='monolithic native call; no mid-step cancellation'))
