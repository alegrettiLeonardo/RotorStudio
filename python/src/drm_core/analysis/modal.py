from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib, json
import numpy as np
from drm_core.solver.facade import SolverFacade
from drm_core.post.whirl import whirl

@dataclass(frozen=True)
class ModalResult:
    speed_rad_s: float
    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    natural_frequency_hz: np.ndarray
    damping_ratio: np.ndarray
    bearing_eccentricity: np.ndarray
    kappa: np.ndarray
    metadata: dict=field(default_factory=dict)

@dataclass(frozen=True)
class CampbellResult:
    speeds_rad_s: np.ndarray
    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    kappa: np.ndarray
    metadata: dict=field(default_factory=dict)

def _kappa_from_modes(eigenvalues,eigenvectors):
    eig=np.asarray(eigenvalues,dtype=complex)
    vec=np.asarray(eigenvectors,dtype=complex)
    if vec.ndim!=2:
        raise ValueError('eigenvectors must be 2-D')
    ndof,nm=vec.shape
    out=np.zeros((ndof,nm),dtype=float)
    for j in range(nm):
        kk,_=whirl(vec[0::2,j],vec[1::2,j])
        if eig[j].imag<0:
            kk=-kk
        out[0::2,j]=kk
        out[1::2,j]=kk
    return out

def _analysis_hash(kind,options):
    return hashlib.sha256(json.dumps({'kind':kind,**options},sort_keys=True,separators=(',',':')).encode()).hexdigest()

def run_modal(model,speed_rad_s:float,library_path=None)->ModalResult:
    facade=SolverFacade(library_path)
    eig,vec,ecc=facade.modal(model,float(speed_rad_s))
    wn=np.abs(eig)
    hz=wn/(2*np.pi)
    zeta=np.divide(-eig.real,wn,out=np.zeros_like(wn,dtype=float),where=wn!=0)
    kap=_kappa_from_modes(eig,vec)
    opts={'speed_rad_s':float(speed_rad_s)}
    return ModalResult(
        float(speed_rad_s),eig,vec,hz,zeta,ecc,kap,
        {
            'solver_version':facade.version(),
            'model_hash':model.model_hash(),
            'analysis_hash':_analysis_hash('modal',opts),
            'timestamp':datetime.now(timezone.utc).isoformat(),
            'backend':'Fortran2018/ISO_C_BINDING/ctypes',
            'legacy_function':'chr_root.m',
            'options':opts,
        }
    )

def run_campbell(model,speeds_rad_s,library_path=None)->CampbellResult:
    speeds=np.asarray(speeds_rad_s,dtype=float)
    if speeds.ndim!=1 or speeds.size==0:
        raise ValueError('speeds_rad_s must be a non-empty 1-D sequence')
    runs=[run_modal(model,float(s),library_path) for s in speeds]
    eig=np.column_stack([r.eigenvalues for r in runs])
    vec=np.stack([r.eigenvectors for r in runs],axis=2)
    kap=np.stack([r.kappa for r in runs],axis=2)
    facade=SolverFacade(library_path)
    opts={'speeds_rad_s':speeds.tolist()}
    return CampbellResult(
        speeds,eig,vec,kap,
        {
            'solver_version':facade.version(),
            'model_hash':model.model_hash(),
            'analysis_hash':_analysis_hash('campbell',opts),
            'timestamp':datetime.now(timezone.utc).isoformat(),
            'legacy_ordering':'numeric complex sort at each speed; no branch tracking',
            'options':opts,
        }
    )
