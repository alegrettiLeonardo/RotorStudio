"""Packaging guard tests; these are not Windows, browser or frozen GUI evidence."""
from __future__ import annotations
import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile
import pytest
from drm_flet import app
from scripts import package_flet as pack
from scripts.flet_distribution_driver import clean_environment, drive
from scripts import flet_extract_package as extract
from scripts.flet_distribution_gate import verify


def frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(app.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(app.sys, '_MEIPASS', str(tmp_path/'bundle'), raising=False)
    monkeypatch.delenv('DRMROTOR_LIB', raising=False)
    return tmp_path/'bundle/native'


def test_frozen_resolves_only_bundled_solver(monkeypatch, tmp_path):
    native=frozen(monkeypatch,tmp_path);native.mkdir(parents=True)
    library=native/'libdrmrotor.so';library.write_bytes(b'test fixture')
    other=tmp_path/'build-flet';other.mkdir();(other/'libdrmrotor.so').write_bytes(b'wrong fixture')
    monkeypatch.chdir(tmp_path)
    assert app.resolve_library()==library


def test_missing_frozen_solver_does_not_fall_back_to_developer_build(monkeypatch,tmp_path):
    frozen(monkeypatch,tmp_path)
    other=tmp_path/'build-flet';other.mkdir();(other/'libdrmrotor.so').write_bytes(b'wrong fixture')
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError,match='Solver ausente'):app.resolve_library()


def test_broken_explicit_path_remains_an_error_when_frozen(monkeypatch,tmp_path):
    native=frozen(monkeypatch,tmp_path);native.mkdir(parents=True);(native/'libdrmrotor.so').touch()
    with pytest.raises(FileNotFoundError,match='informada'):app.resolve_library(tmp_path/'absent.so')


@pytest.mark.parametrize('name',['PYTHONPATH','DRMROTOR_LIB','DRMBEARINGS_LIB','UCRT64_BIN','FLET_VIEW_PATH','LD_LIBRARY_PATH'])
def test_clean_environment_drops_developer_overrides(monkeypatch,tmp_path,name):
    monkeypatch.setenv(name,'UNRELATED_DEVELOPER_LOCATION')
    env=clean_environment(tmp_path/'home')
    assert name not in env
    assert 'UNRELATED_DEVELOPER_LOCATION' not in env['PATH']


def test_driver_rejects_old_client_report(tmp_path):
    (tmp_path/'all_screens_smoke.json').write_text('{}')
    with pytest.raises(RuntimeError,match='not fresh'):
        asyncio.run(drive(SimpleNamespace(out=tmp_path)))


def test_driver_requires_real_executable(tmp_path):
    with pytest.raises(ValueError,match='executable command'):
        asyncio.run(drive(SimpleNamespace(out=tmp_path,command=[])))


def test_native_package_missing_runtime_is_rejected(monkeypatch,tmp_path):
    monkeypatch.setattr(pack.os,'name','posix')
    monkeypatch.setattr(pack.subprocess,'check_output',lambda *a,**kw:'libgfortran.so => not found\n')
    with pytest.raises(RuntimeError,match='not found'):pack.native_dependencies([tmp_path/'solver'])


def test_native_package_empty_dependency_scan_is_rejected(monkeypatch,tmp_path):
    monkeypatch.setattr(pack.os,'name','posix')
    monkeypatch.setattr(pack.subprocess,'check_output',lambda *a,**kw:'')
    with pytest.raises(RuntimeError,match='not identified'):pack.native_dependencies([tmp_path/'solver'])


def zip_fixture(tmp_path, member='RotorStudioFlet/app', tamper=False):
    dist=tmp_path/'dist';dist.mkdir();archive=dist/'bundle.zip';content=b'inert fixture, not executable'
    manifest={'source_head':'test-head','files':{'app':hashlib.sha256(content).hexdigest()}}
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr(member,content)
        z.writestr('RotorStudioFlet/PACKAGE_MANIFEST.json',json.dumps(manifest))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (dist/'PACKAGE.json').write_text(json.dumps({'archive':'bundle.zip','sha256':'bad' if tamper else digest,'source_head':'test-head'}))
    return dist


def test_package_extraction_hashes(monkeypatch,tmp_path,capsys):
    dist=zip_fixture(tmp_path);out=tmp_path/'clean'
    monkeypatch.setattr('sys.argv',['extract','--dist',str(dist),'--out',str(out)])
    extract.main()
    assert json.loads(capsys.readouterr().out)['status']=='EXTRACTION_HASHES_PASS'
    assert (out/'RotorStudioFlet/app').is_file()


def test_package_archive_hash_mismatch(monkeypatch,tmp_path):
    dist=zip_fixture(tmp_path,tamper=True)
    monkeypatch.setattr('sys.argv',['extract','--dist',str(dist),'--out',str(tmp_path/'clean')])
    with pytest.raises(ValueError,match='Archive hash'):extract.main()


def test_package_member_escape_is_rejected(monkeypatch,tmp_path):
    dist=zip_fixture(tmp_path,member='../outside')
    monkeypatch.setattr('sys.argv',['extract','--dist',str(dist),'--out',str(tmp_path/'clean')])
    with pytest.raises(ValueError,match='escapes'):extract.main()
    assert not (tmp_path/'outside').exists()


def test_platform_gate_rejects_mismatched_head(tmp_path):
    (tmp_path/'source_head.txt').write_text('old-head')
    with pytest.raises(ValueError,match='expected HEAD'):verify(tmp_path,'new-head','linux')


@pytest.mark.parametrize('entry',['','<testcase><failure/></testcase>','<testcase><skipped/></testcase>'])
def test_platform_gate_rejects_missing_or_failed_test_collections(tmp_path,entry):
    (tmp_path/'source_head.txt').write_text('head')
    (tmp_path/'pytest.xml').write_text('<testsuite>'+entry+'</testsuite>')
    with pytest.raises(ValueError,match='Empty, failed'):verify(tmp_path,'head','linux')


def test_platform_gate_rejects_no_file_dialog_evidence(tmp_path):
    (tmp_path/'source_head.txt').write_text('head')
    for filename in ('pytest.xml','ctest.xml'):
        (tmp_path/filename).write_text('<testsuite><testcase/></testsuite>')
    out=tmp_path/'source_desktop';out.mkdir()
    (out/'DISTRIBUTION_RESULT.json').write_text(json.dumps({'status':'PASS','source_head':'head','file_dialogs':False}))
    with pytest.raises(ValueError,match='exact-head qualification'):verify(tmp_path,'head','linux')
