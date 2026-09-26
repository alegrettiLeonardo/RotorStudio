from drm_core import CoefficientBearing, Node, RotorModel, RotorProject, ShaftElement, Force, Bearing
from drm_core.analysis.transient import run_runup
from drm_core.solver.ffi import SolverLibraryError
from drm_studio.analysis_pages.transient_setup import RunupSetupDialog


def test_b18_runup_dialog_defaults_to_full_order(qtbot):
    dialog=RunupSetupDialog()
    qtbot.addWidget(dialog)
    assert dialog.nr.value()==0
    case=dialog.analysis_case()
    assert case.kind=="runup"
    assert case.parameters["nr"]==0
