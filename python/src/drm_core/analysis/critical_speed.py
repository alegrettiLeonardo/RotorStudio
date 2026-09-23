from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib, json
import numpy as np
from drm_core.solver.facade import SolverFacade

@dataclass(frozen=True)
class CriticalSpeedResult:
    critical_speeds_rad_s: np.ndarray
    mode_shapes: np.ndarray
    iterations: np.ndarray
    converged: np.ndarray
    metadata: dict=field(default_factory=dict)

def run_critical_speeds(model,NX=1.0,damped_NF=True,number_criticals=5,max_iterations=20,
                        convergence_tol=1e-6,method='auto',initial_estimates=None,library_path=None)->CriticalSpeedResult:
    facade=SolverFacade(library_path)
    speeds,modes,it,conv=facade.critical_speeds(
        model,NX=NX,damped_NF=damped_NF,number_criticals=number_criticals,
        max_iterations=max_iterations,convergence_tol=convergence_tol,
        method=method,initial_estimates=initial_estimates,
    )
    opts={
        'NX':float(NX),'damped_NF':bool(damped_NF),'number_criticals':int(len(speeds)),
        'max_iterations':int(max_iterations),'convergence_tol':float(convergence_tol),
        'method':method,'initial_estimates':None if initial_estimates is None else np.asarray(initial_estimates,dtype=float).tolist(),
    }
    ah=hashlib.sha256(json.dumps({'kind':'critical_speed',**opts},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if method=='auto':
        resolved='iterative-index' if any(b.bearing_type in (7,8) for b in model.bearings) else 'direct'
    elif method=='iterative':
        resolved='iterative-index'
    else:
        resolved=method
    return CriticalSpeedResult(
        speeds,modes,it,conv,
        {
            'solver_version':facade.version(),
            'model_hash':model.model_hash(),
            'analysis_hash':ah,
            'timestamp':datetime.now(timezone.utc).isoformat(),
            'legacy_function':'crit_spd.m',
            'resolved_method':resolved,
            'options':opts,
        }
    )
