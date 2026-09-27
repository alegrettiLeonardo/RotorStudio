import numpy as np
import pytest
from forced_cases import case
from drm_studio.analysis_pages.forced_response_setup import ForcedResponseSetupDialog
from drm_studio.result_views.forced_response_view import orbit_xy

def test_real_forced_gui(qapp,tmp_path):
    from drm_studio.forced_response_qualification import run_forced_response_gui_smoke
    assert run_forced_response_gui_smoke(tmp_path)['status']=='PASS'

def test_force_entry_contract(qapp):
    m,_=case('fixed_speed');d=ForcedResponseSetupDialog(m);d.points.setValue(3);d.forces.setRowCount(0)
    d.add_force(2,2,'17,19,23','-31');d.add_force(2,2,'1','2')
    c=d.analysis_case();np.testing.assert_array_equal(np.array(c.parameters['force_real'])[6],[18,20,24]);np.testing.assert_array_equal(np.array(c.parameters['force_imag'])[6],[-29]*3)
    d.add_force(1,0,'1,2','0')
    with pytest.raises(ValueError,match='3 finite'):d.analysis_case()
    d.forces.setRowCount(0)
    with pytest.raises(ValueError,match='at least one'):d.analysis_case()
    d.deleteLater()

def test_orbit_phase_convention():
    from types import SimpleNamespace
    q=np.zeros((8,1),complex);q[0,0]=2+3j;q[1,0]=5-7j
    xy=orbit_xy(SimpleNamespace(displacement=q),0,0,[0,np.pi/2,np.pi])
    np.testing.assert_allclose(xy,[[2,-3,-2],[5,7,-5]],atol=1e-14)
