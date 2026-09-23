from dataclasses import dataclass,field
from datetime import datetime,timezone
import numpy as np
from drm_core.solver.facade import SolverFacade
@dataclass(frozen=True)
class CriticalSpeedResult:
    critical_speeds_rad_s:np.ndarray;iterations:np.ndarray|None=None;converged:np.ndarray|None=None;metadata:dict=field(default_factory=dict)
def run_critical_speeds(model,library_path=None,**kwargs):
    want_diag=kwargs.pop("return_diagnostics",True)
    if want_diag:
        if "method" in kwargs or "initial_estimates" in kwargs:
            r,it,cv=SolverFacade(library_path).critical_speeds(model,return_diagnostics=True,**kwargs)
        else:
            r=SolverFacade(library_path).critical_speeds(model,**kwargs);it=cv=None
    else:
        r=SolverFacade(library_path).critical_speeds(model,**kwargs);it=cv=None
    return CriticalSpeedResult(np.asarray(r),None if it is None else np.asarray(it),None if cv is None else np.asarray(cv),{"solver_version":"0.3.0","model_hash":model.model_hash(),"timestamp":datetime.now(timezone.utc).isoformat(),"backend":"Fortran2018/ctypes"})
