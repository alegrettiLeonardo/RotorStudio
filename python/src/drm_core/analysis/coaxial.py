from dataclasses import dataclass,field
from datetime import datetime,timezone
import numpy as np
from drm_core.solver.facade import SolverFacade
@dataclass(frozen=True)
class CoaxialModalResult:
    speed_rad_s:float;eigenvalues:np.ndarray;eigenvectors:np.ndarray;metadata:dict=field(default_factory=dict)
@dataclass(frozen=True)
class CoaxialFrequencyResponseResult:
    speeds_rad_s:np.ndarray;response:np.ndarray;metadata:dict=field(default_factory=dict)
def run_coaxial_modal(model,speed_rad_s,library_path=None):
    e,v=SolverFacade(library_path).coaxial_modal(model,speed_rad_s)
    return CoaxialModalResult(speed_rad_s,e,v,{"solver_version":"0.3.0","model_hash":model.model_hash(),"timestamp":datetime.now(timezone.utc).isoformat(),"legacy_bearing_speed_rule":"speed-dependent bearings use reference rotor speed, matching V2"})
def run_coaxial_frequency_response(model,speeds_rad_s,library_path=None):
    sp=np.asarray(speeds_rad_s,float);r=SolverFacade(library_path).coaxial_frequency_response(model,sp)
    return CoaxialFrequencyResponseResult(sp,r,{"solver_version":"0.3.0","model_hash":model.model_hash(),"timestamp":datetime.now(timezone.utc).isoformat()})
