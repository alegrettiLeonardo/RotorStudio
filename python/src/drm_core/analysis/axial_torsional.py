"""B3 application-facing dedicated axial/torsional workflows."""
from __future__ import annotations
from drm_core.solver.axial_torsional import (
    AxialTorsionalModalResult,AxialTorsionalSweepResult,
    run_axial_modal_6dof,run_torsional_modal_6dof,
    run_axial_sweep_6dof,run_torsional_sweep_6dof,
)

def run_axial_modal(model,speed_rad_s:float=0.0,library_path=None)->AxialTorsionalModalResult:
    return run_axial_modal_6dof(model,speed_rad_s,library_path)

def run_torsional_modal(model,speed_rad_s:float=0.0,library_path=None)->AxialTorsionalModalResult:
    return run_torsional_modal_6dof(model,speed_rad_s,library_path)

def run_axial_sweep(model,speed_range_rad_s,library_path=None)->AxialTorsionalSweepResult:
    return run_axial_sweep_6dof(model,speed_range_rad_s,library_path)

def run_torsional_sweep(model,speed_range_rad_s,library_path=None)->AxialTorsionalSweepResult:
    return run_torsional_sweep_6dof(model,speed_range_rad_s,library_path)
