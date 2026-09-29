import os
import pytest

from drm_studio.ucs_qualification import run_ucs_gui_smoke


@pytest.mark.skipif(not os.environ.get("DRMROTOR_LIB"), reason="real Fortran library required")
def test_ucs_gui_service_persistence_exports(qapp, tmp_path):
    payload=run_ucs_gui_smoke(tmp_path)
    assert payload["status"]=="PASS"
    assert payload["native_abi"]=="rd_ucs_v1"
    assert payload["synchronous_rouch"] is True
    assert payload["intersections"]>0
    assert payload["persistence"].startswith("save-close-reopen-recompute")
