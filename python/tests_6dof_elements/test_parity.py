from __future__ import annotations
import itertools
import pytest

@pytest.mark.parametrize('index',range(113))
def test_each_primary_matrix(native_reports,index):
    rows=native_reports[0]['PRIMARY_PARITY.json']['results']
    assert len(rows)==113
    assert rows[index]['status']=='PASS', rows[index]

@pytest.mark.parametrize('index',range(63))
def test_each_frozen_lateral_selection(native_reports,index):
    rows=native_reports[0]['LATERAL_PARITY.json']['results']
    assert len(rows)==63
    assert rows[index]['status']=='PASS', rows[index]

@pytest.mark.parametrize('index',range(63))
def test_each_legacy_common_domain_comparison(native_reports,index):
    rows=native_reports[0]['LEGACY_CROSSCHECK.json']['results']
    assert len(rows)==63
    assert rows[index]['status']=='PASS', rows[index]

@pytest.mark.parametrize('index',range(4))
def test_signed_load_additions_use_frozen_entrywise_floor(native_reports,index):
    row=native_reports[0]['LOAD_ADDITIONS.json']['results'][index]
    assert row['status']=='PASS', row

@pytest.mark.parametrize('prefix',['S17','S18','S19','S24'])
def test_explicit_conical_cases_remain_full_tapered_matrices(native_reports,prefix):
    rows=[r for r in native_reports[0]['PRIMARY_PARITY.json']['results'] if r['case'].startswith(prefix+'_')]
    assert len(rows)==4 and {r['matrix'] for r in rows}=={'M','K','G','Kst'}
    assert all(r['status']=='PASS' for r in rows),rows


def test_independent_native_invariants(native_reports):
    report=native_reports[0]['INVARIANTS.json']
    assert report['count']>200
    failed=[r for r in report['results'] if r['status']!='PASS']
    assert not failed,failed


def test_all_eight_flags_are_really_defined():
    from validation.b1.native_validation import inputs
    cases=inputs()
    flags={tuple(p[k] for k in ('shear_effects','rotary_inertia','gyroscopic'))
           for cid,(kind,p) in cases.items() if cid[:3] in {f'S{i:02d}' for i in range(2,10)}}
    assert flags==set(itertools.product((False,True),repeat=3))


def test_summary_cannot_hide_an_unexecuted_gate(native_reports):
    reports,summary=native_reports
    assert summary['primary_matrices']==113
    assert summary['lateral_selections']==63
    assert summary['legacy_comparisons']==63
    assert summary['authority_unchanged'] is True
    assert all(r['status']=='PASS' and r['count']>0 for r in reports.values())
    assert set(summary['maxima_by_matrix_type'])=={'shaft_M','shaft_K','shaft_G','shaft_Kst','disk_M','disk_G','disk_Kdt'}
    assert summary['status']=='PASS',summary
