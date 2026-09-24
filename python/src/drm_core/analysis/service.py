from __future__ import annotations
from drm_core.domain.project import AnalysisCase
from .modal import run_modal
from .frequency_response import run_frequency_response,run_auxiliary_frequency_response,run_foundation_frequency_response
from .critical_speed import run_critical_speeds
from .coaxial import run_coaxial_modal,run_coaxial_frequency_response
from .asymmetric import run_asymmetric_modal,run_asymmetric_frequency_response
from .transient import run_foundation_time_response,run_runup

class AnalysisService:
    """GUI-independent orchestration facade for Stage 1 and future UI workers."""
    def __init__(self,library_path=None): self.library_path=library_path
    def run(self,model,case:AnalysisCase):
        t=case.analysis_type; o=dict(case.options); lib=o.pop('library_path',self.library_path)
        if t=='modal': return run_modal(model,library_path=lib,**o)
        if t=='frequency_response': return run_frequency_response(model,library_path=lib,**o)
        if t=='auxiliary_frequency_response': return run_auxiliary_frequency_response(model,library_path=lib,**o)
        if t=='foundation_frequency_response': return run_foundation_frequency_response(model,library_path=lib,**o)
        if t=='critical_speeds': return run_critical_speeds(model,library_path=lib,**o)
        if t=='coaxial_modal': return run_coaxial_modal(model,library_path=lib,**o)
        if t=='coaxial_frequency_response': return run_coaxial_frequency_response(model,library_path=lib,**o)
        if t=='asymmetric_modal': return run_asymmetric_modal(model,library_path=lib,**o)
        if t=='asymmetric_frequency_response': return run_asymmetric_frequency_response(model,library_path=lib,**o)
        if t=='foundation_time_response': return run_foundation_time_response(model,library_path=lib,**o)
        if t=='runup': return run_runup(model,library_path=lib,**o)
        raise ValueError(f'unsupported analysis_type={t!r}')
