import json
from pathlib import Path
import numpy as np
import pytest
from drm_core.domain.model import RotorModel,Node,ShaftElement,Disk,Bearing
from drm_core.stage1 import AnalysisService,AnalysisCase,RotorProject,save_project,load_project
from drm_core.solver.ffi import configure_static,SolverLibraryError
from test_static_native import ROOT

def model(name='timoshenko_hollow'):
    spec=json.loads((ROOT/f'validation/ross_parity/static_extended/{name}.json').read_text())
    z=np.r_[0.,np.cumsum(spec['lengths_m'])]
    return RotorModel([Node(i+1,float(x)) for i,x in enumerate(z)],
        [ShaftElement(spec['shaft_type'],i+1,i+2,d,spec['inner_diameter_m'],spec['rho_kg_m3'],spec['E_Pa'],spec['G_Pa']) for i,d in enumerate(spec['outer_diameters_m'])],
        [Disk.inertial(d['node']+1,d['mass_kg'],d['Id_kg_m2'],d['Ip_kg_m2']) for d in spec['disks']],
        [Bearing(1,n+1) for n in spec['supports']]+[Bearing(8,n+1,(0.,.03,.02,.0001,1.,.01)) for n in spec.get('seal_nodes',[])])

@pytest.mark.parametrize('name',['timoshenko_hollow','rotary_eb','no_disk','seal_excluded','mass_disk'])
def test_service_persistence(name,tmp_path):
    m=model(name);case=AnalysisCase('static',name='Gravity')
    p=RotorProject('Static',m,[case]);service=AnalysisService()
    first=service.execute(p,case)
    save_project(p,tmp_path/'static.json');del p
    reopened=load_project(tmp_path/'static.json')
    second=service.execute(reopened,reopened.analyses[0])
    for field in ('displacement','reactions','shaft_weights','disk_loads','shear','bending_moment','station_positions','diagnostics'):
        np.testing.assert_array_equal(getattr(first.result,field),getattr(second.result,field))
    assert first.analysis_hash==second.analysis_hash
    assert first.result.metadata['model_hash']==m.model_hash()
    assert first.result.metadata['solver_version']
    assert first.result.metadata['analysis_hash']==first.analysis_hash
    with np.load(ROOT/f'validation/ross_parity/static_extended/{name}.npz') as ref:
        np.testing.assert_allclose(first.result.displacement_y,ref['displacement_y_m'],rtol=1e-8,atol=1e-13)

def test_missing_symbol_fail_closed():
    with pytest.raises(SolverLibraryError,match='rd_static_v1'):configure_static(object())

@pytest.mark.parametrize('count',[0,1])
def test_insufficient_supports(count):
    m=model();m.bearings=m.bearings[:count]
    with pytest.raises(SolverLibraryError,match='status='):AnalysisService().execute(m,AnalysisCase('static'))

@pytest.mark.parametrize('name',['timoshenko_hollow','rotary_eb','no_disk','mass_disk'])
def test_global_assembly_and_load(name):
    from drm_core.solver.backend import FortranBackend
    m=model(name);m.bearings=[]
    M,C,K,G=FortranBackend().assemble_matrices(m,0.)
    with np.load(ROOT/f'validation/ross_parity/static_extended/{name}.npz') as ref:
        np.testing.assert_allclose(M,ref['M'],rtol=1e-10,atol=1e-12)
        np.testing.assert_allclose(K,ref['K'],rtol=1e-10,atol=1e-7)
        g=np.zeros(len(M));g[1::4]=-9.8065
        np.testing.assert_allclose(M@g,ref['Fg'],rtol=1e-10,atol=1e-12)

@pytest.mark.parametrize('change',['taper','preload','advanced','nonfinite','link','rotors'])
def test_out_of_scope_fail_closed(change):
    from dataclasses import replace
    from drm_core.domain.model import TaperedShaftElement,RotorDefinition
    m=model()
    if change=='taper':m.shafts[0]=TaperedShaftElement(22,1,2,.05,.04,0.,0.,7800.,2e11,8e10)
    elif change=='preload':m.shafts[0]=replace(m.shafts[0],axial_force_n=1.)
    elif change=='advanced':m.advanced_bearings=[object()]
    elif change=='nonfinite':m.shafts[0]=replace(m.shafts[0],damping_factor=float('nan'))
    elif change=='link':m.bearings[0]=Bearing(20,1,(2,1e6,1e6,0.,0.))
    elif change=='rotors':m.rotors=[RotorDefinition(1,len(m.nodes),1.)]
    with pytest.raises((SolverLibraryError,ValueError)):AnalysisService().execute(m,AnalysisCase('static'))
