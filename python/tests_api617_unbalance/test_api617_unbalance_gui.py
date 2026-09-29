import os
import pytest

from drm_studio.api617_unbalance_qualification import run_api617_unbalance_gui_smoke


@pytest.mark.skipif(not os.environ.get("DRMROTOR_LIB"),reason="real Fortran library required")
def test_api617_unbalance_gui_service_persistence_exports(qapp,tmp_path):
    payload=run_api617_unbalance_gui_smoke(tmp_path)
    assert payload["status"]=="PASS"
    assert payload["native_abi"]=="rd_api617_unbalance_v1"
    assert payload["persistence"].startswith("save-close-reopen-recompute")
