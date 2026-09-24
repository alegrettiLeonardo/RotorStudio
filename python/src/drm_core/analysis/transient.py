from __future__ import annotations
from dataclasses import dataclass,field
import numpy as np
from drm_core.solver.facade import SolverFacade
from drm_core.provenance import result_metadata

@dataclass(frozen=True)
class TransientResult:
    time_s:np.ndarray
    response:np.ndarray
    forcing:np.ndarray|None=None
    speed_rad_s:np.ndarray|None=None
    metadata:dict=field(default_factory=dict)

def run_foundation_time_response(model,rotor_speed_rad_s,dt,npts,library_path=None,nr=0,rtol=1e-3,atol=1e-6,h_init=0.0,h_max=0.0):
    t,r,f,diag=SolverFacade(library_path).foundation_time_response(model,rotor_speed_rad_s,dt,npts,nr=nr,rtol=rtol,atol=atol,h_init=h_init,h_max=h_max)
    opts={'rotor_speed_rad_s':float(rotor_speed_rad_s),'dt':float(dt),'npts':int(npts),'nr':int(nr),'rtol':float(rtol),'atol':float(atol),'h_init':float(h_init),'h_max':float(h_max)}
    return TransientResult(t,r,f,None,result_metadata(model,'time_fdn',opts,reduction='V2 eig(K,M) modal truncation',integrator='Dormand-Prince 5(4) adaptive',**diag))

def run_runup(model,alpha,tspan,library_path=None,nr=0,rtol=1e-3,atol=1e-6,h_init=0.0,h_max=0.0,max_points=200000):
    aa=np.asarray(alpha,float);tt=np.asarray(tspan,float)
    t,r,s,diag=SolverFacade(library_path).runup(model,aa,tt,nr=nr,rtol=rtol,atol=atol,h_init=h_init,h_max=h_max,max_points=max_points)
    opts={'alpha':aa,'tspan':tt,'nr':int(nr),'rtol':float(rtol),'atol':float(atol),'h_init':float(h_init),'h_max':float(h_max),'max_points':int(max_points)}
    return TransientResult(t,r,None,s,result_metadata(model,'runup',opts,reduction='V2 eig(K,M) modal truncation',integrator='Dormand-Prince 5(4) adaptive',**diag))
