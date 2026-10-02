"""C1 application-facing misalignment analysis."""
from __future__ import annotations
from drm_core.solver.misalignment import (
    MisalignmentResult,run_misalignment_6dof,node_orbit,response_dfft,
)

def run_misalignment(model,library_path=None,**parameters)->MisalignmentResult:
    return run_misalignment_6dof(model,library_path=library_path,**parameters)
