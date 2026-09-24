from __future__ import annotations
import importlib,sys
from pathlib import Path
import numpy as np
import pytest

from drm_core import RotorModel,Node,ShaftElement,Disk,Bearing,Seal,RotorProject,AnalysisCase,AnalysisService,save_project,load_project
from drm_core.post import fftscale,plot_campbell,plot_root_locus,plot_eigenvalues,plot_orbits,plot_response,plot_frf,save_figure,export_array_csv,export_npz
from drm_core.validation.model import validate_model,ModelValidationError
from drm_core.units import rpm_to_rad_s,rad_s_to_rpm,mm_to_m,m_to_mm,mpa_to_pa,gpa_to_pa,kn_to_n,hz_to_rad_s

def model():
    return RotorModel(
        [Node(1,0.0),Node(2,0.5)],
        [ShaftElement(2,1,2,0.05,0.0,7810.0,211e9,81.2e9)],
        [Disk.inertial(2,10.0,0.1,0.2)],
        [Bearing(3,1,(1e6,1e6,1e3,1e3))],
    )

def test_phase9_fftscale_matches_legacy_definition():
    t=np.linspace(0,1,9);y=np.vstack([np.sin(2*np.pi*t),np.cos(2*np.pi*t)])
    got,f=fftscale(y,t)
    np.testing.assert_allclose(got,(2/y.shape[1])*np.fft.fft(y,axis=1))
    np.testing.assert_allclose(f,np.arange(t.size)/(t.max()-t.min()))

def test_phase9_fftscale_rejects_nonuniform_time():
    with pytest.raises(ValueError,match='equal increments'):fftscale(np.ones((1,4)),[0,.1,.25,.3])

def test_project_roundtrip_and_hashes(tmp_path):
    p=RotorProject('qualified',model(),[AnalysisCase('m','modal',{'speed_rad_s':0.0})],{'owner':'test'})
    path=save_project(p,tmp_path/'p.json');q=load_project(path)
    assert q.project_hash()==p.project_hash()
    assert q.get_analysis('m').analysis_hash()==p.get_analysis('m').analysis_hash()

def test_analysis_service_is_gui_independent():
    service=AnalysisService()
    assert service.library_path is None
    forbidden=('PySide6','PyQt5','PyQt6','tkinter','wx')
    imported=' '.join(sys.modules)
    assert not any(x in imported for x in forbidden)

def test_units_roundtrip_and_si_conversions():
    rpm=np.array([0.,60.,3600.]);np.testing.assert_allclose(rad_s_to_rpm(rpm_to_rad_s(rpm)),rpm)
    assert mm_to_m(1000)==1;assert m_to_mm(1)==1000;assert mpa_to_pa(1)==1e6;assert gpa_to_pa(1)==1e9;assert kn_to_n(1)==1000;assert hz_to_rad_s(1)==pytest.approx(2*np.pi)

def test_bearing_contract_validation_and_seal():
    validate_model(model())
    bad=model();bad.bearings=[Bearing(3,1,(1,2,3))]
    with pytest.raises(ModelValidationError,match='expected exactly 4'):validate_model(bad)
    m=model();m.bearings=[Seal.from_legacy(1,(1e5,.05,.02,1e-4,10.,.01))]
    validate_model(m)

def test_headless_plots_and_exports(tmp_path):
    import matplotlib.pyplot as plt
    sp=np.array([0.,100.]);eig=np.array([[-1+20j,-2+30j],[-1-20j,-2-30j]])
    ax=plot_campbell(sp,eig);fig=ax.figure
    written=save_figure(fig,tmp_path/'campbell',formats=('png','svg','pdf'))
    assert all(p.is_file() and p.stat().st_size>0 for p in written);plt.close(fig)
    for fn in (plot_root_locus,):
        ax=fn(sp,eig);plt.close(ax.figure)
    axes=plot_eigenvalues(sp,eig);plt.close(axes[0].figure)
    mode=np.array([1+0j,1j,0,0,1,1j,0,0],complex)
    ax=plot_orbits(mode,[1,2],eigenvalue=1j);plt.close(ax.figure)
    rsp=np.ones((8,2),complex)*(1+1j)
    axes=plot_response(sp,rsp,[1.1,2.2]);plt.close(axes[0].figure)
    axes=plot_frf(sp,rsp,[1.1]);plt.close(axes[0].figure)
    export_array_csv(tmp_path/'complex.csv',np.array([1+2j,3+4j]))
    export_npz(tmp_path/'data.npz',x=np.arange(3))
    assert (tmp_path/'complex.csv').is_file() and (tmp_path/'data.npz').is_file()

def test_no_desktop_ui_dependency_in_core_source():
    root=Path(importlib.import_module('drm_core').__file__).resolve().parent
    forbidden=('PySide6','PyQt5','PyQt6','QMainWindow','tkinter','wxPython')
    offenders=[]
    for p in root.rglob('*.py'):
        txt=p.read_text(encoding='utf-8')
        if any(x in txt for x in forbidden):offenders.append(str(p.relative_to(root)))
    assert offenders==[]
