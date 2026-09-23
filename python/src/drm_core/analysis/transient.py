from __future__ import annotations
from dataclasses import dataclass,field
from datetime import datetime,timezone
import numpy as np
from drm_core.solver.facade import SolverFacade

@dataclass(frozen=True)
class TransientResult:
    time_s:np.ndarray
    response:np.ndarray
    forcing:np.ndarray|None=None
    speed_rad_s:np.ndarray|None=None
    metadata:dict=field(default_factory=dict)

def run_foundation_time_response(model,rotor_speed_rad_s,dt,npts,library_path=None,nr=0,rtol=1e-3,atol=1e-6,h_init=0.0,h_max=0.0):
    t,r,f,diag=SolverFacade(library_path).foundation_time_response(model,rotor_speed_rad_s,dt,npts,nr=nr,rtol=rtol,atol=atol,h_init=h_init,h_max=h_max)
    return TransientResult(t,r,f,None,{"solver_version":"0.5.0","model_hash":model.model_hash(),"timestamp":datetime.now(timezone.utc).isoformat(),"backend":"Fortran2018/ctypes","analysis":"time_fdn","reduction":"V2 eig(K,M) modal truncation","integrator":"Dormand-Prince 5(4) adaptive",**diag})

def run_runup(model,alpha,tspan,library_path=None,nr=0,rtol=1e-3,atol=1e-6,h_init=0.0,h_max=0.0,max_points=200000):
    t,r,s,diag=SolverFacade(library_path).runup(model,alpha,tspan,nr=nr,rtol=rtol,atol=atol,h_init=h_init,h_max=h_max,max_points=max_points)
    return TransientResult(t,r,None,s,{"solver_version":"0.5.0","model_hash":model.model_hash(),"timestamp":datetime.now(timezone.utc).isoformat(),"backend":"Fortran2018/ctypes","analysis":"runup","reduction":"V2 eig(K,M) modal truncation","integrator":"Dormand-Prince 5(4) adaptive",**diag})
