from dataclasses import dataclass,field
import numpy as np
from drm_core.solver.facade import SolverFacade
from drm_core.provenance import result_metadata

@dataclass(frozen=True)
class AsymmetricModalResult:
    speed_rad_s:float;eigenvalues:np.ndarray;eigenvectors:np.ndarray|None;metadata:dict=field(default_factory=dict)
@dataclass(frozen=True)
class AsymmetricFrequencyResponseResult:
    speeds_rad_s:np.ndarray;response:np.ndarray;metadata:dict=field(default_factory=dict)

def run_asymmetric_modal(model,speed_rad_s,library_path=None,with_eigenvectors=False):
    e,v=SolverFacade(library_path).asymmetric_modal(model,speed_rad_s,with_eigenvectors)
    return AsymmetricModalResult(speed_rad_s,e,v if with_eigenvectors else None,result_metadata(model,'chr_asym',{'speed_rad_s':float(speed_rad_s),'with_eigenvectors':bool(with_eigenvectors)},legacy_chr_asym_nargout_semantics=True))

def run_asymmetric_frequency_response(model,speeds_rad_s,library_path=None):
    sp=np.asarray(speeds_rad_s,float);r=SolverFacade(library_path).asymmetric_frequency_response(model,sp)
    return AsymmetricFrequencyResponseResult(sp,r,result_metadata(model,'freq_asym',{'speeds_rad_s':sp}))
