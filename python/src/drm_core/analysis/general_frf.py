from dataclasses import dataclass,field
import numpy as np
import ctypes as ct
from drm_core.solver.facade import SolverFacade

@dataclass(frozen=True)
class FrequencyResponseMatrixResult:
    frequency_rad_s:np.ndarray
    rotor_speed_rad_s:np.ndarray
    H_disp:np.ndarray
    H_vel:np.ndarray
    H_acc:np.ndarray
    residual:np.ndarray
    metadata:dict=field(default_factory=dict)

def run_general_frf(model,frequency_rad_s,speed=None,free_free=False,modes=None,library_path=None):
    facade=SolverFacade(library_path)
    f,omega,hd,hv,ha,res,policy,bearings=facade.general_frf(model,frequency_rad_s,speed,free_free)
    version=[ct.c_int() for _ in range(3)]
    fn=facade.backend.lib.rd_version;fn.argtypes=[ct.POINTER(ct.c_int)]*3;fn.restype=ct.c_int
    if fn(*(ct.byref(v) for v in version)):raise RuntimeError("Cannot read native solver version")
    version=".".join(str(v.value) for v in version)
    return FrequencyResponseMatrixResult(f,omega,hd,hv,ha,res,dict(model_hash=model.model_hash(),native_abi='rd_frf_general_v1',solver_version=version,backend='Fortran2018/ctypes',omega_policy=policy,frequency_axis='excitation rad/s',dof_order=['x','y','alpha','beta'],matrix_order='output,input,frequency',dof_indexing='zero-based',ross_authority='6320eab9f890f1b3cc1710d508b446fe063ca68d',bearing_evaluation=bearings,full_order=True,modes_argument_ignored=None if modes is None else list(modes),units='SI: translational m/N; rotation/moment DOFs retain rad and N m'))
