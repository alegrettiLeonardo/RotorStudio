from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import numpy as np
from drm_core.solver.facade import SolverFacade
from drm_core.post.whirl import whirl
@dataclass(frozen=True)
class ModalResult:
    speed_rad_s: float
    eigenvalues: np.ndarray
    natural_frequency_hz: np.ndarray
    damping_ratio: np.ndarray
    eigenvectors: np.ndarray|None=None
    kappa: np.ndarray|None=None
    bearing_eccentricity: np.ndarray|None=None
    metadata: dict=field(default_factory=dict)
def _kappa(eig,vec):
    if vec is None:return None
    ndof,nmode=vec.shape;out=np.zeros((ndof,nmode),float)
    for j in range(nmode):
        kk,_=whirl(vec[0::2,j],vec[1::2,j])
        if eig[j].imag<0:kk=-kk
        out[0::2,j]=kk;out[1::2,j]=kk
    return out
def run_modal(model,speed_rad_s:float,library_path=None,with_eigenvectors:bool=False,with_kappa:bool=False)->ModalResult:
    facade=SolverFacade(library_path)
    if with_eigenvectors or with_kappa:
        eig,vec,ecc=facade.modal_eigensystem(model,speed_rad_s)
    else:
        eig=facade.modal(model,speed_rad_s);vec=None;ecc=None
    wn=np.abs(eig); hz=wn/(2*np.pi); zeta=np.divide(-eig.real,wn,out=np.zeros_like(wn),where=wn!=0)
    kp=_kappa(eig,vec) if with_kappa else None
    return ModalResult(speed_rad_s,eig,hz,zeta,vec,kp,ecc,{"solver_version":"0.5.0","model_hash":model.model_hash(),"timestamp":datetime.now(timezone.utc).isoformat(),"backend":"Fortran2018/ctypes"})
