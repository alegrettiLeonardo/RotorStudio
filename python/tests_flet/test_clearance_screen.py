"""A8 Flet input units, native results and deliberate rejection of unsafe inputs."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
import flet as ft
from drm_core import AnalysisService
from drm_flet.analysis_catalog import default_values,build_case,values_from_case
from drm_flet.analysis_forms import AnalysisForm
from drm_flet.session import StudioSession
from drm_flet.ui import StudioApp
from drm_flet.jobs import NativeJob
from drm_flet.clearance_view import present_clearance
from scripts.flet_screen_cases import simple_model,screen_case
from test_flet_core_adapter import PageStub


def values():
    model=simple_model();v=default_values('clearance',model)
    v['speed_range_rad_s'].update(count=7,stop=10000)
    return model,v


def test_a8_sentinels_and_inserted_speeds():
    m,v=values();v.update(probe_angles_rad='31.25;-62.5',radial_clearance_m='87.125;206.5;112.75',
        minimum_allowable_speed_rad_s='7012.125',maximum_continuous_speed_rad_s='9031.25',
        explicit_unbalance=True,unbalance_nodes='2',unbalance_magnitude_kg_m='0.000037125',
        unbalance_phase_rad='21.125',scale_factor_cap='6.125')
    c=build_case('clearance',v,m,'A8 sentinela');p=c.parameters
    np.testing.assert_allclose(p['radial_clearance_m'],np.array([87.125,206.5,112.75])*1e-6,rtol=0,atol=0)
    np.testing.assert_allclose(p['probe_angles_rad'],np.deg2rad([31.25,-62.5]),rtol=0,atol=0)
    assert p['unbalance_magnitude_kg_m']==[.000037125]
    r=AnalysisService().execute(m,c).result
    assert p['minimum_allowable_speed_rad_s'] in r.speed_range_rad_s
    assert p['maximum_continuous_speed_rad_s'] in r.speed_range_rad_s
    assert r.scale_factor_cap==6.125
    np.testing.assert_allclose(r.diametral_clearance_m,2*np.array(p['radial_clearance_m']))
    shown=present_clearance(r,dict(view='summary',selected_clearance_index=1))
    assert [row[-1]=='PASS' for row in shown.rows]==r.passed.tolist()
    assert 'pico a pico' in present_clearance(r,dict(view='clearance')).figure.axes[0].get_ylabel()
    assert 'não escalada' in present_clearance(r,dict(view='probes')).headers[1]


@pytest.mark.parametrize('changes',[
    {'probe_nodes':'1.5;3'}, {'probe_nodes':'1;99'}, {'probe_angles_rad':'45'},
    {'radial_clearance_m':'0;10;20'}, {'radial_clearance_m':'10;-10;20'},
    {'clearance_tags':'A;;C'}, {'probe_tags':'only one'},
    {'minimum_allowable_speed_rad_s':10000,'maximum_continuous_speed_rad_s':9000},
    {'scale_factor_cap':0}, {'num_modes':11},
    {'explicit_unbalance':True,'unbalance_magnitude_kg_m':'-.0001'},
    {'explicit_unbalance':True,'unbalance_phase_rad':'1;2'},
])
def test_a8_invalid_form_fails_before_execution(changes):
    m,v=values();v.update(changes)
    with pytest.raises(ValueError):build_case('clearance',v,m,'reject')


def test_disabled_unbalance_is_not_parsed_and_native_a7_is_used():
    m,v=values();v.update(unbalance_nodes='',unbalance_phase_rad='invalid',unbalance_magnitude_kg_m='')
    c=build_case('clearance',v,m,'A7 default')
    assert not any(k.startswith('unbalance_') for k in c.parameters)
    assert c.parameters['scale_factor_cap'] is None
    assert AnalysisService().execute(m,c).result.mode==0


def test_a8_selection_and_renaming_preserve_parameters(monkeypatch):
    monkeypatch.setattr(ft.Control,'update',lambda self:None)
    project,c=screen_case('clearance');app=StudioApp(PageStub(),StudioSession(project))
    app.analysis_dialog(kind='clearance',case=c);form=app.active_analysis_form
    form.name.value='Renamed';renamed=form.build()
    assert renamed.parameters==c.parameters
    assert form.controls['unbalance_nodes'].disabled
    form.controls['explicit_unbalance'].value=True;form.apply_visibility()
    assert not form.controls['unbalance_nodes'].disabled
    r=asyncio.run(form.run());assert r
    app.result_set('selected_clearance_index',2);app.result_set('probe_index',1)
    assert r.view_selection['selected_clearance_index']==2
    assert r.view_selection['probe_index']==1


def test_deleted_case_is_not_current_and_undo_restores():
    project,c=screen_case('modal');session=StudioSession(project)
    r=NativeJob(project,c).future.result(30)
    assert session.is_current(r)
    session.transact('delete',lambda p:p.analyses.clear(),validate=False)
    assert not session.is_current(r)
    session.undo();assert session.is_current(r)


def test_campbell_respects_requested_excitation_order():
    from drm_flet.plotting import campbell_figure
    project,c=screen_case('modal_sweep');points=AnalysisService().execute(project,c).result
    fig=campbell_figure(points,nx=3.5)
    labels=[line.get_label() for line in fig.axes[0].lines]
    assert '3×' in labels and '4×' not in labels
