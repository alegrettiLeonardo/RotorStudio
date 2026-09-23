from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib, json
import numpy as np
from drm_core.solver.facade import SolverFacade

@dataclass(frozen=True)
class AssemblyResult:
    speed_rad_s: float
    M: np.ndarray
    C0: np.ndarray
    G: np.ndarray
    K0: np.ndarray
    K1: np.ndarray
    zero_dof: np.ndarray
    bearing_eccentricity: np.ndarray
    metadata: dict=field(default_factory=dict)

    @property
    def C(self)->np.ndarray:
        return self.C0 + self.speed_rad_s*self.G

    @property
    def K(self)->np.ndarray:
        return self.K0 + self.speed_rad_s*self.K1


def run_assembly(model,speed_rad_s:float=0.0,library_path=None)->AssemblyResult:
    facade=SolverFacade(library_path)
    M,C0,G,K0,K1,zero,ecc=facade.assemble(model,float(speed_rad_s))
    opts={'speed_rad_s':float(speed_rad_s)}
    ah=hashlib.sha256(json.dumps({'kind':'assembly',**opts},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return AssemblyResult(
        float(speed_rad_s),M,C0,G,K0,K1,zero,ecc,
        {
            'solver_version':facade.version(),
            'model_hash':model.model_hash(),
            'analysis_hash':ah,
            'timestamp':datetime.now(timezone.utc).isoformat(),
            'legacy_functions':['rotormtx.m','bearmtx.m'],
            'matrix_contract':{
                'M':'M0+Mb',
                'C0':'shaft proportional damping + bearing Cb',
                'G':'C1 gyroscopic/speed-linear damping matrix',
                'K0':'K0+Kb',
                'K1':'speed-linear stiffness contribution from internal damping',
                'effective_C':'C0 + speed*G',
                'effective_K':'K0 + speed*K1',
            },
            'options':opts,
        }
    )
