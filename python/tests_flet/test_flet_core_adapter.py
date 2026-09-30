"""Flet adapters are tested against the unchanged, real Fortran Core.

The PageStub tests cover Python control trees/handlers, not screen rendering.
The separate desktop_smoke.py captures the actual Flutter desktop client.
"""
from __future__ import annotations
import asyncio
import io
import json
import os
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import zipfile
import numpy as np
import pytest
import flet as ft
from drm_core import (AnalysisCase, AnalysisService, AnalysisCancelled, RotorProject,
    RotorModel, Node, Bearing, CoefficientBearing, Force, load_project)
from drm_core.solver.facade import SolverFacade
from drm_core.units import rpm_to_rad_s
from drm_flet.session import StudioSession, EntityRef, reference_project
from drm_flet.editing import (number, canonical, display, form_values, from_form,
    entity_json, from_json, coefficient_csv, validate_editable_model)
from drm_flet.jobs import NativeJob, BearingSweep, csv_bytes, npz_bytes, report_bytes, _POOL
from drm_flet.plotting import rotor_svg, positive_modes, modal_figure, png_bytes


@pytest.fixture(scope="module")
def library():
    path = Path(os.environ.get("DRMROTOR_LIB", "missing-library"))
    assert path.is_file(), "Build Fortran and set DRMROTOR_LIB; real-native tests are mandatory, not skipped."
    return str(path)


def modal_case(name="Modal_test"):
    return AnalysisCase("modal", {"speed_rad_s": rpm_to_rad_s(3600), "with_eigenvectors": True,
        "with_kappa": True, "coefficient_policy": "SYNCHRONOUS_COEFFICIENTS"}, name)


@pytest.fixture(scope="module")
def modal_record(library):
    return NativeJob(reference_project(), modal_case(), library).future.result(timeout=30)


@pytest.mark.parametrize("text,expected", [("140,25",140.25),("210.000,0",210000.),("1.2e-3",.0012),("-25",-25),(" 8 120 ",8120)])
def test_numeric_inputs(text,expected):
    assert number(text)==expected


@pytest.mark.parametrize("text", ["NaN","inf","-inf","1,234.5","1.25,4","abc",""])
def test_reject_invalid_numeric_inputs(text):
    with pytest.raises(ValueError):number(text)


def test_no_integer_truncation():
    with pytest.raises(ValueError):number("2.5",integer=True)
    assert number("3",integer=True)==3


@pytest.mark.parametrize("unit,stored,shown", [("mm",.14025,140.25),("MPa",211234e6,211234),
    ("rpm",rpm_to_rad_s(3579.75),3579.75),("N/m",1.234e7,1.234e7),("kg/m³",7812.3,7812.3)])
def test_unit_round_trip(unit,stored,shown):
    assert float(display(stored,unit))==pytest.approx(shown,rel=1e-10)
    assert canonical(shown,unit)==pytest.approx(stored,rel=1e-12)


def test_transactional_form_sentinels_undo_redo():
    s=StudioSession(); ref=EntityRef("shafts",5); base=s.project.model.model_hash()
    values=form_values(s.selected())
    values.update(outer_diameter_m="143,25",inner_diameter_m="12.5",E_pa="211234",
        G_pa="81234",rho_kg_m3="7812.3",axial_force_n="123.4",torque_nm="23.5")
    candidate=from_form(s.selected(),values);s.replace_entity(ref,candidate)
    assert candidate.outer_diameter_m==pytest.approx(.14325)
    assert candidate.inner_diameter_m==pytest.approx(.0125)
    assert candidate.E_pa==211234e6 and candidate.G_pa==81234e6
    assert candidate.rho_kg_m3==7812.3 and candidate.torque_nm==23.5
    assert s.project.model.model_hash()!=base
    edited=s.project.model.model_hash();s.undo();assert s.project.model.model_hash()==base
    s.redo();assert s.project.model.model_hash()==edited


@pytest.mark.parametrize("mutation", [lambda s:replace(s,outer_diameter_m=-1),
    lambda s:replace(s,inner_diameter_m=99),lambda s:replace(s,node2=999),
    lambda s:replace(s,E_pa=float('nan')),lambda s:replace(s,node1=1.2)])
def test_invalid_edit_rollback(mutation):
    s=StudioSession();base=s.project.project_hash()
    with pytest.raises(ValueError):s.replace_entity(s.selection,mutation(s.selected()))
    assert s.project.project_hash()==base and not s.can_undo


def test_no_orphan_node_removal_or_force_reference():
    s=StudioSession()
    with pytest.raises(ValueError):s.remove_entity(EntityRef("nodes",0))
    m=RotorModel(nodes=[Node(1,0)],forces=[Force(1,(1,.001,0))])
    s=StudioSession(RotorProject("one",m));base=s.project.project_hash()
    with pytest.raises(ValueError):s.remove_entity(EntityRef("nodes",0))
    assert s.project.project_hash()==base
    with pytest.raises(ValueError):s.replace_entity(EntityRef("nodes",0),Node(2,0))


def test_build_empty_model_incrementally():
    s=StudioSession(RotorProject("New",RotorModel()))
    s.add_entity("nodes",Node(7,0));s.add_entity("nodes",Node(9,.2))
    s.remove_entity(EntityRef("nodes",1));s.remove_entity(EntityRef("nodes",0))
    assert not s.project.model.nodes
    s.undo();assert s.project.model.nodes==[Node(7,0)]


def test_core_persistence_and_dirty(tmp_path):
    s=StudioSession();s.set_case(modal_case());path=tmp_path/"sentinels.json"
    assert s.dirty;s.save(path);assert not s.dirty
    expected=s.project.project_hash();assert load_project(path).project_hash()==expected
    s.replace_entity(s.selection,replace(s.selected(),outer_diameter_m=.15));assert s.dirty
    s.undo();assert not s.dirty
    t=StudioSession();t.open(path);assert t.project.project_hash()==expected and not t.dirty
    assert t.project.analyses[0].name=="Modal_test"
    t.open_bytes(s.as_bytes());assert t.path is None and t.project.project_hash()==expected


def test_json_preserves_unknown_type_specific_fields():
    b=CoefficientBearing(1,(1e7,2e7),(20.,30.),kxy=(-500.,-700.),kyx=(300.,400.),
                         speed_rad_s=(0.,100.),mxx=(2.,3.),myy=(4.,5.),tag="sentinel")
    restored=from_json(b,entity_json(b))
    assert restored==b
    with pytest.raises(ValueError):from_json(b,entity_json(b).replace('100.0','NaN'))


def test_csv_retains_signs_and_mass():
    b=CoefficientBearing(1,(1e7,2e7),(20.,30.),speed_rad_s=tuple(rpm_to_rad_s([0,6000])),
                         mxx=(2.,3.),myy=(4.,5.),tag="M")
    data="rpm;kxx;kxy;kyx;kyy;cxx;cxy;cyx;cyy\n0;123;-234;345;456;21;-22;23;24\n6000;223;-334;445;556;31;-32;33;34"
    typed=coefficient_csv(b,data,"linear")
    assert typed.kxy==(-234.,-334.) and typed.kyx==(345.,445.)
    assert typed.mxx==b.mxx and typed.myy==b.myy and typed.tag==b.tag
    np.testing.assert_allclose(typed.speed_rad_s,rpm_to_rad_s([0,6000]),rtol=1e-14)
    with pytest.raises(ValueError):coefficient_csv(b,data.replace('6000;','7000;'),"linear")
    # myy-only speed dependence also forbids silently relabelling its axis.
    b2=replace(b,mxx=0.,myy=(4.,5.))
    with pytest.raises(ValueError):coefficient_csv(b2,data.replace('6000;','7000;'),"linear")


def test_svg_same_geometry_for_draw_and_hit_test():
    p=reference_project();ref=EntityRef("shafts",5)
    svg,hits=rotor_svg(p.model,ref,width=960,height=330)
    assert b"1800 mm" in svg and b"200 mm" in svg
    hit=next(h for h in hits if h.kind=="shafts" and h.index==5)
    assert hit.contains((hit.x0+hit.x1)/2,(hit.y0+hit.y1)/2)
    moved,_=rotor_svg(p.model,ref,width=960,height=330,zoom=2,pan=30)
    assert svg!=moved


def test_native_modal_exact_core_parity(library,modal_record):
    direct=AnalysisService(library).execute(reference_project(),modal_case()).result
    actual=modal_record.execution.result
    np.testing.assert_allclose(actual.eigenvalues,direct.eigenvalues,rtol=1e-12,atol=1e-9)
    np.testing.assert_allclose(actual.eigenvectors,direct.eigenvectors,rtol=1e-12,atol=1e-10)
    assert actual.eigenvectors.shape[0]==4*len(modal_record.model.nodes)


def test_result_staleness_undo_and_case_change(modal_record):
    s=StudioSession();s.set_case(modal_case());assert s.is_current(modal_record)
    s.replace_entity(s.selection,replace(s.selected(),outer_diameter_m=.151))
    assert not s.is_current(modal_record)
    assert modal_record.model.shafts[5].outer_diameter_m==.14
    s.undo();assert s.is_current(modal_record)
    s.set_case(replace(modal_case(),parameters={**modal_case().parameters,"speed_rad_s":100.}))
    assert not s.is_current(modal_record)


def test_native_bearing_diagonal_and_cross_coefficients(library):
    p=reference_project()
    p.model.advanced_bearings[0]=replace(p.model.advanced_bearings[0],kxy=-1234.5,kyx=4567.8,cxy=-12.3,cyx=45.6,mxx=1.23)
    case=AnalysisCase("bearing_matrices",{"speed_rad_s":0},"Bearing",{"flet_scope":"bearing_sweep",
        "bearing_kind":"advanced_bearings","bearing_index":0,"speeds_rad_s":rpm_to_rad_s([0,3000,6000]).tolist()})
    r=NativeJob(p,case,library).future.result(timeout=30).execution.result
    direct=SolverFacade(library).advanced_bearing(p.model.advanced_bearings[0],rpm_to_rad_s(3000),rpm_to_rad_s(3000))
    np.testing.assert_allclose(r.K[1],direct.K[:2,:2]);np.testing.assert_allclose(r.C[1],direct.C[:2,:2])
    np.testing.assert_allclose(r.M[1],direct.M[:2,:2]);assert r.K[1,0,1]==-1234.5


def test_native_legacy_bearing_returns_M_C_K_in_correct_order(library):
    p=reference_project();p.model.advanced_bearings=[];p.model.bearings=[Bearing(3,3,(1.234e7,2.345e7,123.,456.))]
    case=AnalysisCase("bearing_matrices",{"speed_rad_s":0},"Legacy",{"flet_scope":"bearing_sweep",
        "bearing_kind":"bearings","bearing_index":0,"speeds_rad_s":[0.,100.]})
    r=NativeJob(p,case,library).future.result(timeout=30).execution.result
    assert r.K[0,0,0]==1.234e7 and r.C[0,1,1]==456. and r.M[0,0,0]==0.


def test_blocked_import_cannot_use_bearing_shortcut(library):
    p=reference_project();p.metadata['numerical_readiness']={'status':'BLOCKED_FOR_NUMERICAL_ANALYSIS'}
    with pytest.raises(ValueError):NativeJob(p,modal_case(),library).future.result(timeout=10)
    case=AnalysisCase("bearing_matrices",{},"blocked",{"flet_scope":"bearing_sweep",
        "bearing_kind":"advanced_bearings","bearing_index":0,"speeds_rad_s":[100.]})
    with pytest.raises(ValueError):NativeJob(p,case,library).future.result(timeout=10)


def test_cancel_queued_job_does_not_fabricate_result(library):
    event=Event();hold=_POOL.submit(lambda:event.wait(10))
    try:
        job=NativeJob(reference_project(),modal_case(),library);job.cancel();event.set()
        with pytest.raises(AnalysisCancelled):job.future.result(timeout=10)
        assert job.state=="CANCELLED"
    finally:event.set();hold.result(timeout=15)


def test_missing_solver_is_failure_not_demo_fallback(tmp_path):
    job=NativeJob(reference_project(),modal_case(),str(tmp_path/"missing.so"))
    with pytest.raises(Exception):job.future.result(timeout=10)
    assert job.state=="FAILED"


def test_complex_exports_and_stale_report(modal_record):
    data=np.load(io.BytesIO(npz_bytes(modal_record)),allow_pickle=False)
    np.testing.assert_allclose(data['result.eigenvectors'],modal_record.execution.result.eigenvectors)
    assert b'imaginary' in csv_bytes(modal_record)
    with zipfile.ZipFile(io.BytesIO(report_bytes(modal_record,current=False))) as z:
        assert json.loads(z.read('result_context.json'))['status']=='OUTDATED'
        assert {'analysis.json','analysis.md','data.csv','data.npz'}<=set(z.namelist())


def test_real_mode_plot_phase_dark_light(modal_record):
    r=modal_record.execution.result;k=positive_modes(r)[0]
    images=[]
    for dark,phase in [(False,0),(True,0),(True,90)]:
        fig=modal_figure(modal_record.model,r,k,dark=dark,phase=phase)
        data=png_bytes(fig);assert data[:8]==b'\x89PNG\r\n\x1a\n';images.append(data)
    assert len(set(images))==3


class PageStub:
    """Control-tree-only fixture. Does not replace the desktop rendering smoke."""
    def __init__(self):self.window=SimpleNamespace();self.web=False;self.dialogs=[]
    def add(self,_):pass
    def update(self):pass
    def show_dialog(self,dialog):self.dialogs.append(dialog)
    def pop_dialog(self):return self.dialogs.pop()
    def run_task(self,fn,*args):return asyncio.create_task(fn(*args))


def test_flet_controls_handlers_to_real_solver_and_reopen(library,tmp_path,monkeypatch):
    from drm_flet.ui import StudioApp
    monkeypatch.setattr(ft.Control,'update',lambda self:None)
    app=StudioApp(PageStub(),library_path=library)
    app.form_fields['outer_diameter_m'].value='141,375'
    assert app.apply_properties()
    assert app.session.selected().outer_diameter_m==pytest.approx(.141375)
    app.analysis_dialog(kind='modal')
    dialog=app.page.dialogs[-1]
    asyncio.run(dialog.actions[-1].on_click(None))
    assert app.session.records and app.plot_png is not None
    assert not [x for x in app.session.messages if x[0] in ('ERRO','VISUALIZAÇÃO')]
    r=app.session.records[-1]
    direct=AnalysisService(library).execute(app.session.project,r.execution.case).result
    np.testing.assert_allclose(r.execution.result.eigenvalues,direct.eigenvalues,atol=1e-9)
    path=tmp_path/'gui_project.json';app.session.save(path)
    reopened=StudioSession();reopened.open(path)
    repeat=NativeJob(reopened.project,reopened.project.analyses[-1],library).future.result(timeout=30)
    np.testing.assert_allclose(repeat.execution.result.eigenvalues,r.execution.result.eigenvalues,atol=1e-9)
    app.document='model';app.render();app.form_fields['outer_diameter_m'].value='NaN'
    before=app.session.project.project_hash();assert not app.apply_properties()
    assert app.session.project.project_hash()==before


@pytest.mark.parametrize('kind,params',[("modal_sweep",{"speeds_rad_s":rpm_to_rad_s([0,1500,3000,6000]).tolist(),"with_eigenvectors":True,"with_kappa":True,"coefficient_policy":"SYNCHRONOUS_COEFFICIENTS"}),
 ("critical_speeds",{"NX":1.,"damped":True,"ncrit":4,"method":3,"max_iterations":40,"tol":1e-6}),
 ("frequency_response",{"speeds_rad_s":rpm_to_rad_s([300,1500,3000,6000]).tolist()}),
 ("static",{}),("general_frf",{"frequency_rad_s":[10.,50.,100.],"speed":100.})])
def test_exposed_analysis_parameters_really_execute(library,kind,params):
    project=reference_project()
    if kind=="static":
        project.model.advanced_bearings=[]
        project.model.bearings=[Bearing(3,3,(1e7,1e7,1500.,1500.)),Bearing(3,11,(1e7,1e7,1500.,1500.))]
    job=NativeJob(project,AnalysisCase(kind,params,kind),library)
    r=job.future.result(timeout=30)
    assert job.state=='COMPLETED' and r.execution.result is not None


def test_nonconsecutive_node_ids_blocked_before_native_abi(library):
    p=RotorProject("numbering",RotorModel(nodes=[Node(7,0),Node(9,.2)]))
    job=NativeJob(p,modal_case(),library)
    with pytest.raises(ValueError,match="consecutivos"):job.future.result(timeout=10)
    assert job.state=="FAILED"


def test_library_discovery_preserves_explicit_errors(tmp_path, monkeypatch):
    from drm_flet.app import resolve_library
    monkeypatch.delenv("DRMROTOR_LIB", raising=False)
    library = tmp_path / "build-release" / "libdrmrotor.so"
    library.parent.mkdir(); library.write_bytes(b"discovery-only fixture")
    assert resolve_library(roots=[tmp_path]) == library.resolve()
    with pytest.raises(FileNotFoundError):
        resolve_library(tmp_path / "missing.so", roots=[tmp_path])
    monkeypatch.setenv("DRMROTOR_LIB", str(tmp_path / "missing.so"))
    with pytest.raises(FileNotFoundError):
        resolve_library(roots=[tmp_path])


def test_native_configuration_preserves_explicit_bearing_library(tmp_path, monkeypatch):
    from drm_flet.app import configure_native
    rotor=tmp_path/"libdrmrotor.so"; rotor.touch()
    bearing=tmp_path/"libdrmbearings.so"; bearing.touch()
    monkeypatch.delenv("DRMBEARINGS_LIB", raising=False)
    monkeypatch.setenv("DRMROTOR_LIB", "")
    configure_native(rotor)
    assert os.environ['DRMROTOR_LIB'] == str(rotor)
    assert os.environ['DRMBEARINGS_LIB'] == str(bearing)
    monkeypatch.setenv("DRMBEARINGS_LIB", "explicit.so")
    configure_native(rotor)
    assert os.environ['DRMBEARINGS_LIB'] == "explicit.so"


def test_table_pagination_reveals_selection_without_detached_scroll_rpc(monkeypatch):
    from drm_flet.ui import StudioApp
    monkeypatch.setattr(ft.Control, "update", lambda self: None)
    page = PageStub()
    def unexpected_task(*args):
        raise AssertionError("Rendering a disposable table must not schedule scroll RPCs")
    page.run_task = unexpected_task
    app = StudioApp(page)
    table = app.table(["Index"], [[str(i)] for i in range(10)], selected=5, height=160)
    header, body, footer = table.content.controls
    def shown():
        return [row.content.controls[0].content.value for row in body.controls]
    assert shown() == ["3", "4", "5"]
    footer.content.controls[-1].on_click(None)
    assert shown() == ["6", "7", "8"]
    footer.content.controls[-1].on_click(None)
    assert shown() == ["9"]
    assert footer.content.controls[-1].disabled
    footer.content.controls[-2].on_click(None)
    assert shown() == ["6", "7", "8"]


def test_disconnected_app_does_not_launch_jobs_or_update_destroyed_page(monkeypatch):
    from drm_flet.ui import StudioApp
    app = StudioApp(PageStub())
    app.disconnect()
    def destroyed_update():
        raise AssertionError("A disconnected session must not update its destroyed page")
    app.page.update = destroyed_update
    app.render()
    app.error("Disconnected", "Diagnostic retained without opening a dialog")
    assert asyncio.run(app.run_case(modal_case())) is None
    assert app.job is None
