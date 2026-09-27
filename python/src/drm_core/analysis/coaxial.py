from dataclasses import dataclass,field
from datetime import datetime,timezone
import numpy as np
from drm_core.solver.facade import SolverFacade

B20_COAXIAL_ADVANCED_POLICY="COAXIAL_REFERENCE_SPEED_SYNCHRONOUS"

@dataclass(frozen=True)
class CoaxialModalResult:
    speed_rad_s:float;eigenvalues:np.ndarray;eigenvectors:np.ndarray;metadata:dict=field(default_factory=dict)

@dataclass(frozen=True)
class CoaxialFrequencyResponseResult:
    speeds_rad_s:np.ndarray;response:np.ndarray;metadata:dict=field(default_factory=dict)

def _metadata(model):
    payload={
        "solver_version":"0.5.0",
        "model_hash":model.model_hash(),
        "timestamp":datetime.now(timezone.utc).isoformat(),
        "legacy_bearing_speed_rule":"speed-dependent bearings use reference rotor speed, matching V2",
    }
    if model.advanced_bearings:
        payload.update({
            "advanced_bearing_policy":B20_COAXIAL_ADVANCED_POLICY,
            "advanced_bearing_base_flow_speed":"reference_rotor_speed",
            "advanced_bearing_frequency":"reference_rotor_speed",
        })
    return payload

def run_coaxial_modal(model,speed_rad_s,library_path=None):
    e,v=SolverFacade(library_path).coaxial_modal(model,speed_rad_s)
    return CoaxialModalResult(speed_rad_s,e,v,_metadata(model))

def run_coaxial_frequency_response(model,speeds_rad_s,library_path=None):
    sp=np.asarray(speeds_rad_s,float);r=SolverFacade(library_path).coaxial_frequency_response(model,sp)
    return CoaxialFrequencyResponseResult(sp,r,_metadata(model))
