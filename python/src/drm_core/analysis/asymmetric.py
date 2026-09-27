from dataclasses import dataclass,field
from datetime import datetime,timezone
import numpy as np
from drm_core.solver.facade import SolverFacade

B21_ROTATING_ADVANCED_POLICY="ROTATION_INVARIANT_SYNCHRONOUS"

@dataclass(frozen=True)
class AsymmetricModalResult:
    speed_rad_s:float;eigenvalues:np.ndarray;eigenvectors:np.ndarray|None;metadata:dict=field(default_factory=dict)

@dataclass(frozen=True)
class AsymmetricFrequencyResponseResult:
    speeds_rad_s:np.ndarray;response:np.ndarray;metadata:dict=field(default_factory=dict)

def _metadata(model):
    payload={
        "solver_version":"0.5.0",
        "model_hash":model.model_hash(),
        "timestamp":datetime.now(timezone.utc).isoformat(),
        "legacy_chr_asym_nargout_semantics":True,
    }
    if model.advanced_bearings:
        payload.update({
            "advanced_bearing_policy":B21_ROTATING_ADVANCED_POLICY,
            "frame_transform":"q_inertial = R(Omega*t) q_rotating",
            "rotation_invariance_requirement":"A*J = J*A for K,C,M",
            "advanced_bearing_frequency":"omega = Omega",
        })
    return payload

def run_asymmetric_modal(model,speed_rad_s,library_path=None,with_eigenvectors=False):
    e,v=SolverFacade(library_path).asymmetric_modal(model,speed_rad_s,with_eigenvectors)
    return AsymmetricModalResult(
        speed_rad_s,e,v if with_eigenvectors else None,_metadata(model)
    )

def run_asymmetric_frequency_response(model,speeds_rad_s,library_path=None):
    sp=np.asarray(speeds_rad_s,float)
    r=SolverFacade(library_path).asymmetric_frequency_response(model,sp)
    return AsymmetricFrequencyResponseResult(sp,r,_metadata(model))
