from .backend import FortranBackend

class SolverFacade:
    def __init__(self,library_path=None):
        self.backend=FortranBackend(library_path)
    def version(self):
        return self.backend.version()
    def assemble(self,model,speed_rad_s=0.0):
        return self.backend.assemble_stationary(model,speed_rad_s)
    def modal(self,model,speed_rad_s):
        return self.backend.modal_solution(model,speed_rad_s)
    def frequency_response(self,model,speeds_rad_s):
        return self.backend.frequency_response(model,speeds_rad_s)
    def critical_speeds(self,model,**kwargs):
        return self.backend.critical_speeds(model,**kwargs)
