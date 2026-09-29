import numpy as np
import pytest
from drm_studio.analysis_pages.general_time_setup import GeneralTimeSetupDialog
from drm_studio.result_views.general_time_view import dfft
from drm_studio.general_time_qualification import run_general_time_gui_smoke
from time_cases import case

@pytest.fixture(scope='module')
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])

def test_dfft_amplitude_frequency_nonuniform():
    t=np.arange(1000)/1000;v=2+3*np.sin(2*np.pi*37*t)
    f,a=dfft(t,v);assert abs(a[0]-2)<1e-12 and abs(a[37]-3)<1e-12 and f[37]==37
    assert dfft(t**1.1,v) is None
    _,a=dfft(t,(-1.)**np.arange(1000));assert abs(a[-1]-1)<1e-12

def test_gui_inputs_and_import(app,tmp_path):
    m,s=case('harmonic');d=GeneralTimeSetupDialog(m);d.forces.setRowCount(0)
    d.add_force(2,0,'Sine','137,317,0');d.add_force(2,0,'Constant','2');d.add_force(2,2,'Pulse','11,.004,.009')
    c=d.analysis_case();t=np.array(c.parameters['time_s']);F=np.array(c.parameters['force_real'])
    np.testing.assert_allclose(F[4],137*np.sin(317*t)+2);np.testing.assert_array_equal(F[6],np.where((t>=.004)&(t<=.009),11,0))
    t=np.array([0,.0001,.003,.011,.04]);F=np.arange(80).reshape(5,16);data=np.column_stack([t,23+17*t,F]);p=tmp_path/'input.csv'
    np.savetxt(p,data,delimiter=',',header=','.join(['time_s','speed_rad_s']+[f'F{i}' for i in range(16)]),comments='')
    d.import_csv(p);c=d.analysis_case();np.testing.assert_array_equal(c.parameters['force_real'],F.T);np.testing.assert_array_equal(c.parameters['time_s'],t)
    d.speed_values.setText('1,2')
    with pytest.raises(ValueError):d.analysis_case()
    d.close()

def test_gui_worker_persistence_exports(app,tmp_path):
    assert run_general_time_gui_smoke(tmp_path)['status']=='PASS'


def test_dfft_grid_classification_is_scale_invariant():
    values=np.array([0.,1.,2.,3.])
    for scale in (1e-15,1.,1e15):
        assert dfft(scale*np.array([0.,1.,3.,6.]),values) is None
        assert dfft(scale*np.arange(4),values) is not None
