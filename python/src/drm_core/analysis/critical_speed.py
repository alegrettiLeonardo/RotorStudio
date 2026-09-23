from dataclasses import dataclass,field
from datetime import datetime,timezone
import numpy as np
from drm_core.solver.facade import SolverFacade
@dataclass(frozen=True)
class CriticalSpeedResult:
    critical_speeds_rad_s:np.ndarray; metadata:dict=field(default_factory=dict)
def run_critical_speeds(model,library_path=None,**kwargs):
    r=SolverFacade(library_path).critical_speeds(model,**kwargs)
    return CriticalSpeedResult(r,{"solver_version":"0.2.0","model_hash":model.model_hash(),"timestamp":datetime.now(timezone.utc).isoformat(),"backend":"Fortran2018/ctypes"})
