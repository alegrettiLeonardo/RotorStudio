from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib, json
import numpy as np
from drm_core.solver.facade import SolverFacade

@dataclass(frozen=True)
class FrequencyResponseResult:
    speeds_rad_s: np.ndarray
    response: np.ndarray
    metadata: dict=field(default_factory=dict)

def run_frequency_response(model,speeds_rad_s,library_path=None)->FrequencyResponseResult:
    speeds=np.asarray(speeds_rad_s,dtype=float)
    if speeds.ndim!=1 or speeds.size==0:
        raise ValueError('speeds_rad_s must be a non-empty 1-D sequence')
    facade=SolverFacade(library_path)
    resp=facade.frequency_response(model,speeds)
    opts={'speeds_rad_s':speeds.tolist()}
    ah=hashlib.sha256(json.dumps({'kind':'frequency_response',**opts},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return FrequencyResponseResult(
        speeds,resp,
        {
            'solver_version':facade.version(),
            'model_hash':model.model_hash(),
            'analysis_hash':ah,
            'timestamp':datetime.now(timezone.utc).isoformat(),
            'legacy_function':'freq_rsp.m',
            'options':opts,
        }
    )
