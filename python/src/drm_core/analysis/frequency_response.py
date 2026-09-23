from dataclasses import dataclass,field
from datetime import datetime,timezone
import numpy as np
from drm_core.solver.facade import SolverFacade
@dataclass(frozen=True)
class FrequencyResponseResult:
    speeds_rad_s:np.ndarray; response:np.ndarray; metadata:dict=field(default_factory=dict)
def run_frequency_response(model,speeds_rad_s,library_path=None):
    sp=np.asarray(speeds_rad_s,float);r=SolverFacade(library_path).frequency_response(model,sp)
    return FrequencyResponseResult(sp,r,{"solver_version":"0.2.0","model_hash":model.model_hash(),"timestamp":datetime.now(timezone.utc).isoformat(),"backend":"Fortran2018/ctypes"})
