from __future__ import annotations
from .assembly import run_assembly
from .modal import run_modal, run_campbell
from .frequency_response import run_frequency_response
from .critical_speed import run_critical_speeds

class AnalysisService:
    """GUI-independent application service for Stage 1 and future Stage-2 workers."""
    def __init__(self,library_path=None):
        self.library_path=library_path
    def assembly(self,model,speed_rad_s=0.0):
        return run_assembly(model,speed_rad_s,self.library_path)
    def modal(self,model,speed_rad_s):
        return run_modal(model,speed_rad_s,self.library_path)
    def campbell(self,model,speeds_rad_s):
        return run_campbell(model,speeds_rad_s,self.library_path)
    def frequency_response(self,model,speeds_rad_s):
        return run_frequency_response(model,speeds_rad_s,self.library_path)
    def critical_speeds(self,model,**kwargs):
        return run_critical_speeds(model,library_path=self.library_path,**kwargs)
