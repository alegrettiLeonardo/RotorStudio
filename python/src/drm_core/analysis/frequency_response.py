from dataclasses import dataclass,field
import numpy as np
from drm_core.solver.facade import SolverFacade
from drm_core.provenance import result_metadata

@dataclass(frozen=True)
class FrequencyResponseResult:
    speeds_rad_s:np.ndarray
    response:np.ndarray
    metadata:dict=field(default_factory=dict)

def run_frequency_response(model,speeds_rad_s,library_path=None):
    sp=np.asarray(speeds_rad_s,float);r=SolverFacade(library_path).frequency_response(model,sp)
    return FrequencyResponseResult(sp,r,result_metadata(model,'freq_rsp',{'speeds_rad_s':sp}))

def run_auxiliary_frequency_response(model,rotor_speed_rad_s,omega_rad_s,direction=1.0,library_path=None):
    om=np.asarray(omega_rad_s,float);r=SolverFacade(library_path).auxiliary_frequency_response(model,rotor_speed_rad_s,om,direction)
    return FrequencyResponseResult(om,r,result_metadata(model,'freq_aux',{'rotor_speed_rad_s':float(rotor_speed_rad_s),'omega_rad_s':om,'direction':float(direction)}))

def run_foundation_frequency_response(model,rotor_speed_rad_s,omega_rad_s,library_path=None):
    om=np.asarray(omega_rad_s,float);r=SolverFacade(library_path).foundation_frequency_response(model,rotor_speed_rad_s,om)
    return FrequencyResponseResult(om,r,result_metadata(model,'freq_fdn',{'rotor_speed_rad_s':float(rotor_speed_rad_s),'omega_rad_s':om},legacy_bearing_predicate='>2 OR <9 preserved'))
