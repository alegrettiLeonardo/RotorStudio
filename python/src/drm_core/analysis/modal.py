from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import numpy as np
from drm_core.solver.facade import SolverFacade
@dataclass(frozen=True)
class ModalResult:
    speed_rad_s: float
    eigenvalues: np.ndarray
    natural_frequency_hz: np.ndarray
    damping_ratio: np.ndarray
    metadata: dict=field(default_factory=dict)
def run_modal(model,speed_rad_s:float,library_path=None)->ModalResult:
    eig=SolverFacade(library_path).modal(model,speed_rad_s)
    wn=np.abs(eig); hz=wn/(2*np.pi); zeta=np.divide(-eig.real,wn,out=np.zeros_like(wn),where=wn!=0)
    return ModalResult(speed_rad_s,eig,hz,zeta,{"solver_version":"0.2.0","model_hash":model.model_hash(),"timestamp":datetime.now(timezone.utc).isoformat(),"backend":"Fortran2018/ctypes"})
