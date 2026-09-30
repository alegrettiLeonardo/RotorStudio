import os
import pytest

from drm_studio.clearance_qualification import run_clearance_gui_smoke


@pytest.mark.skipif(not os.environ.get("DRMROTOR_LIB"),reason="real Fortran library required")
def test_clearance_gui_service_persistence_exports(qapp,tmp_path):
    payload=run_clearance_gui_smoke(tmp_path)
    assert payload["status"]=="PASS"
    assert payload["native_abi"]=="rd_clearance_v1"
    assert payload["persistence"].startswith("save-close-reopen-recompute")


def test_clearance_dialog_explicit_unbalance_and_cap(qapp):
    from drm_studio.api617_unbalance_qualification import _model
    from drm_studio.analysis_pages.clearance_setup import ClearanceSetupDialog
    d=ClearanceSetupDialog(_model())
    d.explicit.setChecked(True)
    d.ub_nodes.setText("4,5")
    d.ub_mag.setText("2e-5,3e-5")
    d.ub_phase_deg.setText("0,180")
    d.cap_enabled.setChecked(True);d.cap.setValue(0.75)
    c=d.analysis_case()
    assert c.kind=="clearance"
    assert c.parameters["unbalance_nodes"]==[4,5]
    assert c.parameters["unbalance_magnitude_kg_m"]==[2e-5,3e-5]
    assert c.parameters["scale_factor_cap"]==0.75
    assert len(c.parameters["unbalance_phase_rad"])==2
    d.deleteLater()
