from dataclasses import dataclass,field
from datetime import datetime,timezone
import numpy as np
from drm_core.solver.facade import SolverFacade
@dataclass(frozen=True)
class CriticalSpeedResult:
    critical_speeds_rad_s:np.ndarray
    iterations:np.ndarray|None=None
    converged:np.ndarray|None=None
    mode_shapes:np.ndarray|None=None
    metadata:dict=field(default_factory=dict)
def _mode_shapes(facade,model,crit,method,NX,damped):
    cols=[]
    for ic,w in enumerate(crit):
        eig,vec,_=facade.modal_eigensystem(model,float(w))
        if method==2:
            # MATLAB sort places an exact conjugate pair by phase; negative-imaginary
            # member comes first. LAPACK roundoff can perturb pair magnitudes enough
            # to reverse them, so restore the conjugate-pair convention explicitly.
            base=min(2*ic,len(eig)-1); candidates=[base]
            if base+1<len(eig): candidates.append(base+1)
            idx=next((j for j in candidates if eig[j].imag<0),base)
        elif method==3:
            est=(np.abs(eig.imag) if damped else np.abs(eig))/max(abs(NX),.2);idx=int(np.argmin(np.abs(est-w)))
        else: raise ValueError("with_mode_shapes is supported for iterative methods 2 and 3; V2 direct-method mode shapes use a different polynomial eigenproblem")
        cols.append(vec[:,idx])
    return np.column_stack(cols) if cols else np.empty((4*len(model.nodes),0),complex)
def run_critical_speeds(model,library_path=None,**kwargs):
    want_diag=kwargs.pop("return_diagnostics",True);want_modes=kwargs.pop("with_mode_shapes",False);method=kwargs.get("method")
    facade=SolverFacade(library_path)
    if want_diag and (method is not None or "initial_estimates" in kwargs):
        r,it,cv=facade.critical_speeds(model,return_diagnostics=True,**kwargs)
    else:
        r=facade.critical_speeds(model,**kwargs);it=cv=None
    modes=None
    if want_modes:
        effective=method if method is not None else 2
        modes=_mode_shapes(facade,model,np.asarray(r),effective,kwargs.get("NX",1.0),kwargs.get("damped",True))
    return CriticalSpeedResult(np.asarray(r),None if it is None else np.asarray(it),None if cv is None else np.asarray(cv),modes,{"solver_version":"0.5.0","model_hash":model.model_hash(),"timestamp":datetime.now(timezone.utc).isoformat(),"backend":"Fortran2018/ctypes"})
