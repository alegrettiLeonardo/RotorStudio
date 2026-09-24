from dataclasses import dataclass,field
import numpy as np
from drm_core.solver.facade import SolverFacade
from drm_core.provenance import result_metadata

@dataclass(frozen=True)
class CoaxialModalResult:
    speed_rad_s:float;eigenvalues:np.ndarray;eigenvectors:np.ndarray;metadata:dict=field(default_factory=dict)
@dataclass(frozen=True)
class CoaxialFrequencyResponseResult:
    speeds_rad_s:np.ndarray;response:np.ndarray;metadata:dict=field(default_factory=dict)

def run_coaxial_modal(model,speed_rad_s,library_path=None):
    e,v=SolverFacade(library_path).coaxial_modal(model,speed_rad_s)
    return CoaxialModalResult(speed_rad_s,e,v,result_metadata(model,'chr_root_coax',{'speed_rad_s':float(speed_rad_s)},legacy_bearing_speed_rule='speed-dependent bearings use reference rotor speed, matching V2'))

def run_coaxial_frequency_response(model,speeds_rad_s,library_path=None):
    sp=np.asarray(speeds_rad_s,float);r=SolverFacade(library_path).coaxial_frequency_response(model,sp)
    return CoaxialFrequencyResponseResult(sp,r,result_metadata(model,'freq_rsp_coax',{'speeds_rad_s':sp}))
