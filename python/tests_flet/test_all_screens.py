"""Screen parity, real native pipelines, typed editing and result semantics.

PageStub tests are handler/control-tree tests only. Actual desktop rendering is
independently exercised by scripts/flet_all_screens_smoke.py.
"""
from __future__ import annotations
import ast
import asyncio
from copy import deepcopy
from dataclasses import fields,replace
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import zipfile
import flet as ft
import numpy as np
import pytest
from drm_core import AnalysisService,AnalysisCase,RotorProject,load_project,save_project,Force,Node,Bearing,CoefficientBearing
from drm_core.domain.bearings import validate_advanced_bearing,advanced_bearing_to_dict
from drm_core.solver.bearings_backend import AdvancedBearingBackend
from drm_flet.analysis_catalog import CATALOG,BY_KIND,default_values,build_case,loads_matrix,materialize_grid,import_history_csv
from drm_flet.analysis_forms import AnalysisForm
from drm_flet.entity_forms import EntityForm,ADVANCED_CLASSES,advanced_values,advanced_from_values,make_entity,parse_data
from drm_flet.editing import form_values,from_form,specs,validate_editable_model
from drm_flet.session import StudioSession,EntityRef
from drm_flet.jobs import NativeJob,arrays_of,csv_bytes,npz_bytes,report_bytes
from drm_flet.result_presenter import present,tabs_for,time_spectrum,AsymmetricFrequencyResponseResult
from drm_flet.ui_results import old_modal
from drm_flet.bearing_jobs import BearingFieldResult,BearingMapResult,map_cache
from drm_flet.ui_bearings import field_present,map_present,FIELD_TABS,MAP_TABS
from drm_flet.ui import StudioApp
from scripts.flet_screen_cases import screen_case,bearing_case,simple_model,coax_model,asymmetric_model
from test_flet_core_adapter import PageStub

ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture(scope='module')
def library():
    assert Path(os.environ['DRMROTOR_LIB']).is_file()
    assert Path(os.environ['DRMBEARINGS_LIB']).is_file()
    return os.environ['DRMROTOR_LIB']

@pytest.fixture
def app_factory(monkeypatch,library):
    monkeypatch.setattr(ft.Control,'update',lambda self:None)
    def create(project):return StudioApp(PageStub(),StudioSession(project),library_path=library)
    return create

@pytest.fixture(scope='module')
def native_records(library):
    result={}
    for spec in CATALOG:
        project,case=screen_case(spec.kind)
        result[spec.kind]=NativeJob(project,case,library).future.result(40)
    return result


def compare_arrays(actual,expected):
    a,b=arrays_of(actual),arrays_of(expected)
    assert set(a)==set(b)
    for key in a:
        if a[key].dtype.kind in 'US':np.testing.assert_array_equal(a[key],b[key],err_msg=key)
        else:np.testing.assert_allclose(a[key],b[key],rtol=1e-11,atol=1e-12,err_msg=key,equal_nan=True)


def test_exact_current_native_contracts_and_all_qt_setup_result_screens():
    import drm_core.stage1 as core
    source=Path(core.__file__).read_text(encoding='utf-8')
    # Dispatch literals, not method names guessed from the GUI.
    tree=ast.parse(source);kinds=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Compare) and ast.unparse(node.left)=='k':
            for op in node.comparators:
                if isinstance(op,ast.Constant) and isinstance(op.value,str):kinds.add(op.value)
    assert set(BY_KIND)==kinds and len(kinds)==21
    for folder,key in [('analysis_pages','qt_screen'),('result_views','result_screen')]:
        names={x.name for file in (ROOT/'python/src/drm_studio'/folder).glob('*.py') for x in ast.parse(file.read_text(encoding='utf-8')).body if isinstance(x,ast.ClassDef)}
        assert names=={getattr(s,key) for s in CATALOG}-{"BearingPerformancePage"},(folder,names)


@pytest.mark.parametrize('kind',list(BY_KIND))
def test_configuration_handler_native_display_save_reopen_recompute_all_current(kind,app_factory,library,tmp_path):
    project,case=screen_case(kind);app=app_factory(project)
    app.analysis_dialog(kind=kind,case=case)
    form=app.active_analysis_form
    assert set(form.controls)=={x.key for x in BY_KIND[kind].inputs}
    # Form identity: changing nothing must not perturb SI or its hash.
    assert form.build()==case
    record=asyncio.run(form.run())
    assert record is not None,app.session.messages
    assert app.session.is_current(record)
    direct=AnalysisService(library).execute(project,case)
    compare_arrays(record.execution.result,direct.result)
    assert record.execution.analysis_hash==direct.analysis_hash
    assert app.plot_png.startswith(b'\x89PNG')
    assert not [m for m in app.session.messages if m[0] in ('ERRO','VISUALIZAÇÃO')]
    saved=tmp_path/(kind+'.json');app.session.save(saved)
    reopened=load_project(saved)
    assert reopened.model.model_hash()==project.model.model_hash()
    again=NativeJob(reopened,reopened.analyses[0],library).future.result(40)
    compare_arrays(again.execution.result,record.execution.result)
    # Round-trip exports retain every ndarray without allow_pickle.
    raw=npz_bytes(record)
    with np.load(io.BytesIO(raw),allow_pickle=False) as z:
        for key,value in arrays_of(record.execution.result).items():np.testing.assert_array_equal(z[key],value)
    assert len(csv_bytes(record))>10 and zipfile.is_zipfile(io.BytesIO(report_bytes(record,current=True)))
    app.document='model';app.session.replace_entity(EntityRef('nodes',1),replace(project.model.nodes[1],z_m=project.model.nodes[1].z_m+.001))
    assert not app.session.is_current(record)
    app.session.undo();assert app.session.is_current(record)


@pytest.mark.parametrize('kind',list(BY_KIND))
def test_every_result_tab_real_arrays_and_selector_presentation(kind,native_records):
    record=native_records[kind];r=record.execution.result
    if old_modal(r):return # Original desktop smoke covers all modal/Campbell panes.
    for view,label in tabs_for(r):
        for dark in (False,True):
            p=present(record,{'view':view,'output_dof':2,'input_dof':1,'point_index':1},dark=dark)
            assert p.figure is not None
            assert p.rows or p.note
            for ax in p.figure.axes:
                for line in ax.lines:assert np.isfinite(line.get_ydata()).all()
    if isinstance(r,AsymmetricFrequencyResponseResult):assert 'orbit' not in dict(tabs_for(r))


@pytest.mark.parametrize('kind',['general_frf','forced_response'])
@pytest.mark.parametrize('quantity',['displacement','velocity','acceleration'])
def test_complex_response_table_exact_dof_units_and_independent_frequency(kind,quantity,native_records):
    rec=native_records[kind];r=rec.execution.result
    got=present(rec,dict(output_dof=6,input_dof=3,response=quantity))
    data=getattr(r,{'displacement':'H_disp','velocity':'H_vel','acceleration':'H_acc'}[quantity])[6,3,:] if kind=='general_frf' else getattr(r,quantity)[6]
    np.testing.assert_allclose(np.asarray(got.rows)[:,0],r.frequency_rad_s/(2*np.pi),rtol=0,atol=0)
    np.testing.assert_allclose(np.asarray(got.rows)[:,1],data.real,rtol=0,atol=0)
    np.testing.assert_allclose(np.asarray(got.rows)[:,2],data.imag,rtol=0,atol=0)
    assert 'rad' in got.headers[1] and ('N·m' in got.headers[1] if kind=='general_frf' else True)


@pytest.mark.parametrize('kind',['modal','asymmetric_modal'])
def test_no_eigenvectors_is_supported_without_plotting_error(kind,app_factory,library):
    project,case=screen_case(kind);params={**case.parameters,'with_eigenvectors':False}
    if kind=='modal':params['with_kappa']=False
    case=replace(case,parameters=params);project.analyses=[case]
    app=app_factory(project);record=asyncio.run(app.run_case(case))
    assert record is not None and record.execution.result.eigenvectors is None
    assert app.plot_png.startswith(b'\x89PNG')
    assert not any(x[0]=='VISUALIZAÇÃO' for x in app.session.messages)


@pytest.mark.parametrize('kind',list(BY_KIND))
def test_form_invalid_and_snapshot_guard_are_transactional(kind,app_factory):
    project,case=screen_case(kind);app=app_factory(project);form=AnalysisForm(app,kind,case)
    before=app.session.project.project_hash();form.name.value=' '
    with pytest.raises(ValueError):form.build()
    assert before==app.session.project.project_hash()
    form.name.value=case.name
    app.session.replace_entity(EntityRef('nodes',1),replace(project.model.nodes[1],z_m=.28))
    with pytest.raises(ValueError,match='modelo mudou'):form.build()


@pytest.mark.parametrize('cls',ADVANCED_CLASSES,ids=lambda cls:cls.__name__)
def test_all_advanced_editor_fields_roundtrip_exact_and_tag_edit(cls,app_factory):
    entity=make_entity('advanced_bearings',simple_model(),cls.__name__)
    validate_advanced_bearing(entity)
    values=advanced_values(entity);back=advanced_from_values(entity,values)
    assert advanced_bearing_to_dict(back)==advanced_bearing_to_dict(entity)
    assert set(values)=={f.name for f in fields(entity) if f.init and f.name!='provenance'}
    project=RotorProject('advanced',replace(simple_model(),advanced_bearings=[entity]))
    app=app_factory(project);form=EntityForm(app,entity,'advanced_bearings',EntityRef('advanced_bearings',0))
    assert form.build()==entity
    if 'tag' in values:
        form.controls['tag'].value='SENTINELA_3579';candidate=form.build()
        assert candidate.tag=='SENTINELA_3579' and candidate.provenance==entity.provenance


CLASSIC=[('nodes',None)]+[('shafts',v) for v in ('ShaftElement','TaperedShaftElement','AsymmetricShaftElement')]+[('disks',str(i)) for i in range(1,7)]+[('bearings',str(i)) for i in (1,2,3,4,5,6,7,8,20)]+[('forces',str(i)) for i in range(1,8)]+[('bend',None),('rotors',None)]
@pytest.mark.parametrize('kind,variant',CLASSIC)
def test_every_classic_entity_editor_roundtrip(kind,variant,app_factory):
    model=simple_model();entity=make_entity(kind,model,variant);app=app_factory(RotorProject('ed',model))
    form=EntityForm(app,entity,kind)
    assert form.build()==entity
    assert set(form.controls)=={f.key for f in specs(entity)}


def test_tapered_asymmetric_rotational_bearing_and_coefficient_sentinels():
    m=simple_model()
    tapered=make_entity('shafts',m,'TaperedShaftElement');v=form_values(tapered)
    v['outer_diameter_2_m']='63,125';v['E_pa']='212345'
    t=from_form(tapered,v);assert t.outer_diameter_2_m==pytest.approx(.063125);assert t.E_pa==212345e6
    asym=make_entity('shafts',m,'AsymmetricShaftElement');v=form_values(asym);v['EIy_nm2']='81234.5'
    assert from_form(asym,v).EIy_nm2==81234.5
    b=make_entity('bearings',m,'6');v=form_values(b);v['property_2']='-1234.5';v['property_19']='-98.75'
    b2=from_form(b,v);assert b2.properties[2]==-1234.5 and b2.properties[19]==-98.75
    c=CoefficientBearing(1,kxx=((1e6,2e6),(3e6,4e6)),cxx=100.,speed_rad_s=(100.,200.),frequency_rad_s=(50.,150.))
    values=advanced_values(c);values['kxy']='-11; -12\n-21; -22'
    updated=advanced_from_values(c,values);assert updated.kxy==((-11.,-12.),(-21.,-22.))
    assert updated.speed_rad_s==c.speed_rad_s and updated.frequency_rad_s==c.frequency_rad_s
    with pytest.raises(ValueError):parse_data('false','cavitation',True)


def test_all_load_materialization_and_grid_fail_closed():
    m=simple_model();axis=np.array([0.,.1,.2]);entries=[dict(node=2,dof=2,real='1;2;3',imag='-1'),dict(node=2,dof=2,real='4',imag='2')]
    a=loads_matrix(entries,axis,m);np.testing.assert_array_equal(a[6],[5+1j,6+1j,7+1j]);assert np.count_nonzero(a)==3
    for raw in [{'mode':'explicit','values':'0;1;1'},{'mode':'uniform','start':2,'stop':1,'count':3}]:
        with pytest.raises(ValueError):materialize_grid(raw)
    with pytest.raises(ValueError):loads_matrix([dict(node=999,dof=0,real='1',imag='0')],axis,m)
    temporal=loads_matrix([dict(node=2,dof=0,shape='Samples',values='2;4;8')],axis,m,temporal=True)
    np.testing.assert_array_equal(temporal[4],[2,4,8])


def test_dfft_dc_nyquist_and_nonuniform_contract():
    t=np.arange(8)*.01
    f,a=time_spectrum(t,np.ones(8)*3);assert a[0]==3 and np.max(a[1:])==0
    f,a=time_spectrum(t,2*(-1.)**np.arange(8));assert a[-1]==2
    assert time_spectrum(np.array([0.,.01,.025]),np.ones(3)) is None


@pytest.fixture(scope='module')
def bearing_records(library,tmp_path_factory):
    root=tmp_path_factory.mktemp('physical_cache');d={}
    for scope in ('bearing_fields','operating_map'):
        p,c=bearing_case(scope,root);d[scope]=NativeJob(p,c,library).future.result(50)
    return d

@pytest.mark.parametrize('scope',['bearing_fields','operating_map'])
def test_native_bearing_screen_every_tab_and_complete_npz(scope,bearing_records,app_factory):
    record=bearing_records[scope];project,case=bearing_case(scope,record.execution.case.options.get('cache_root','unused'))
    app=app_factory(project);app.session.records.append(record);app.document=record.id;app.render()
    assert app.plot_png.startswith(b'\x89PNG')
    for tab in FIELD_TABS if scope=='bearing_fields' else MAP_TABS:
        app.result_set('view',tab[0]);assert app.plot_png.startswith(b'\x89PNG') and app.presented_result.rows
    with np.load(io.BytesIO(npz_bytes(record)),allow_pickle=False) as data:
        assert set(arrays_of(record.execution.result))<=set(data.files)
    assert not [x for x in app.session.messages if x[0] in ('ERRO','VISUALIZAÇÃO')]


def test_native_field_exact_matrices_and_grid_shape(bearing_records):
    rec=bearing_records['bearing_fields'];p,c=bearing_case('bearing_fields','unused')
    expected=AdvancedBearingBackend().evaluate_fields(p.model.advanced_bearings[0],100.,85.)
    compare_arrays(rec.execution.result.payload,expected)
    assert rec.execution.result.payload['pressure_field_pa'].shape==(2,9,5)


def test_native_map_cache_roundtrip_and_apply_undo(bearing_records,library,app_factory):
    rec=bearing_records['operating_map'];p,c=bearing_case('operating_map',rec.execution.result.cache_root)
    next_record=NativeJob(p,c,library).future.result(50)
    assert next_record.execution.result.cached.source=='L1'
    compare_arrays(rec.execution.result.cached.operating_map,next_record.execution.result.cached.operating_map)
    from drm_core.solver.bearing_maps import BearingMapCache
    other=BearingMapCache(rec.execution.result.cache_root)
    cached=other.get_or_generate(p.model.advanced_bearings[0],[80.,100.,120.],[50.,100.],interpolation='linear',backend=AdvancedBearingBackend())
    assert cached.source=='L2'
    app=app_factory(p);app.session.records.append(rec);app.document=rec.id;app.render()
    async def accept(*args):return True
    app.confirm=accept
    before=app.session.project.model.model_hash()
    asyncio.run(app.apply_operating_map())
    actual=app.session.project.model.advanced_bearings[0]
    assert isinstance(actual,CoefficientBearing) and app.session.project.model.model_hash()!=before
    assert 'source_bearing' in actual.provenance
    app.session.undo();assert app.session.project.model.model_hash()==before


def test_navigation_catalog_results_reports_diagnostics_all_render(app_factory,native_records):
    p,c=screen_case('general_frf');app=app_factory(p);app.session.records.extend(native_records.values())
    for screen in ('model','analyses','bearings','results','reports','diagnostics'):
        app.navigate(screen);assert app.root.content is not None
    app.navigate(native_records['general_frf'].id)
    for extension in ('png','svg','pdf','csv','npz','bundle','zip'):
        data=app.export_bytes(extension);assert len(data)>20
        if extension in ('bundle','zip'):assert zipfile.is_zipfile(io.BytesIO(data))


def test_flet_has_no_qt_imports_or_hidden_numeric_solver():
    for file in (ROOT/'python/src/drm_flet').glob('*.py'):
        tree=ast.parse(file.read_text(encoding='utf-8'))
        for x in ast.walk(tree):
            if isinstance(x,ast.ImportFrom):assert not str(x.module).startswith(('PySide','PyQt','drm_studio'))
            if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute):assert x.func.attr not in ('eig','eigh','eigvals','eigs','solve_ivp','odeint','inv')


def test_complete_qt_presentation_inventory_has_no_unmapped_class():
    from scripts.flet_screen_inventory import inventory
    result=inventory(ROOT)
    assert result['qt_presentation_classes']==42
    assert result['native_contracts']==21
    assert len({s['qt_class'] for s in result['screens']})==42
