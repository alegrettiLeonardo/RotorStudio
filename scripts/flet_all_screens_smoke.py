"""Real Flet desktop render + handler/Core smoke. Run under Xvfb on Linux.

Source and frozen execution use the same scenario; the report records the actual mode.
OS/browser file dialogs are exercised only with --file-dialogs and the external driver.
A fresh run ID and explicit PASS file prevent a crashed Flutter client from
being counted as a passing test merely because ft.run() returned normally.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import suppress
from hashlib import sha256
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import platform
import sys
import traceback
from types import SimpleNamespace
import uuid

import flet as ft
import numpy as np

from drm_core import AnalysisCase, AnalysisService
from drm_core.units import rpm_to_rad_s
from drm_flet.jobs import NativeJob, csv_bytes, npz_bytes, report_bytes
from drm_flet.session import StudioSession
from drm_flet.ui import StudioApp
from drm_flet.analysis_catalog import CATALOG
from drm_flet.analysis_forms import AnalysisForm
from drm_flet.entity_forms import EntityForm, ADVANCED_CLASSES, make_entity
from drm_flet.result_presenter import tabs_for, present
from drm_flet.ui_results import old_modal
from drm_flet.ui_bearings import FIELD_TABS, MAP_TABS
from drm_flet.session import EntityRef
from scripts.flet_screen_cases import screen_case, bearing_case, simple_model
from drm_core import RotorProject
from drm_flet.plotting import positive_modes
from PIL import Image
import io


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path("validation/reports/flet_all_screens"))
    parser.add_argument("--web", action="store_true")
    parser.add_argument("--port", type=int, default=8550)
    parser.add_argument("--file-dialogs", action="store_true")
    args = parser.parse_args(argv)
    out = args.outdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "all_screens_smoke.json"
    run_id = uuid.uuid4().hex
    report = {"run_id": run_id, "status": "RUNNING", "checks": [],
              "platform": platform.platform(), "python": platform.python_version(),
              "flet": importlib.metadata.version("flet"),
              "desktop_rendering": not args.web, "web_rendering": args.web,
              "frozen_executable_test": bool(getattr(sys, "frozen", False)),
              "executable": sys.executable, "os_filepicker_interaction_test": False,
              "file_dialogs_requested": args.file_dialogs,
              "model": "Explicit small engineering fixtures; native Core/Fortran results"}
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logging.basicConfig(filename=out / "flet_protocol.log", filemode="w", level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    logging.getLogger("flet").setLevel(logging.DEBUG)
    sessions_started = 0
    scenario_started = False
    failed = False

    def check(name: str, condition: bool) -> None:
        if not condition:
            raise AssertionError(name)
        report["checks"].append(name)
        print("PASS:", name, flush=True)

    async def scenario(page: ft.Page) -> None:
        nonlocal failed
        page.enable_screenshots = True
        app = None
        screenshots={}
        try:
            library=os.environ['DRMROTOR_LIB']
            check('native_library_exists',Path(library).is_file())
            report['native_library_path']=str(Path(library).resolve())
            report['native_library_sha256']=sha256(Path(library).read_bytes()).hexdigest()
            app=StudioApp(page,library_path=library)

            async def capture(name):
                page.update()
                await asyncio.sleep(.45)
                data=await page.take_screenshot()
                if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data)<10000:raise AssertionError('Invalid screenshot '+name)
                image=Image.open(io.BytesIO(data)).convert('RGB')
                if np.asarray(image).std()<4:raise AssertionError('Blank screenshot '+name)
                (out/(name+'.png')).write_bytes(data)
                screenshots[name]={'sha256':sha256(data).hexdigest(),'bytes':len(data),'size':list(image.size)}
                if any(level=='VISUALIZAÇÃO' for level,_ in app.session.messages):raise AssertionError(app.session.messages)

            def use_project(project):
                app.session.reset(project);app.document='model';app.bearing_ref=app.first_bearing()
                app.bearing_record=None;app.speed_index=0;app.mode_ordinal=0;app.dark=False;app.render()

            for spec in CATALOG:
                project,case=screen_case(spec.kind);use_project(project)
                app.analysis_dialog(kind=spec.kind,case=case)
                await capture('setup_'+spec.kind)
                form=app.active_analysis_form
                before=project.model.model_hash()
                record=await form.run()
                check('native_pipeline_'+spec.kind,record is not None and app.session.is_current(record))
                await capture('result_'+spec.kind)
                direct=await asyncio.to_thread(AnalysisService(library).execute,project,case)
                from drm_flet.jobs import arrays_of
                for key,a in arrays_of(record.execution.result).items():
                    b=arrays_of(direct.result)[key]
                    if a.dtype.kind in 'US':np.testing.assert_array_equal(a,b)
                    else:np.testing.assert_allclose(a,b,rtol=1e-11,atol=1e-12,equal_nan=True)
                check('core_parity_'+spec.kind,True)
                r=record.execution.result
                if old_modal(r):
                    points=r if isinstance(r,list) else [r]
                    for view in ('roots','modes','orbits'):
                        app.set_subview(view);await capture('view_'+spec.kind+'_'+view)
                else:
                    for view,label in tabs_for(r):
                        app.result_set('view',view);await capture('view_'+spec.kind+'_'+view)
                if spec.kind in ('general_frf','general_time_response','asymmetric_modal'):
                    app.toggle_theme();await capture('dark_'+spec.kind);app.toggle_theme()
                check('display_model_unchanged_'+spec.kind,app.session.project.model.model_hash()==before)
                path=out/('project_'+spec.kind+'.json');app.session.save(path)
                reopened=StudioSession();reopened.open(path)
                again=await asyncio.wrap_future(NativeJob(reopened.project,reopened.project.analyses[0],library).future)
                check('reopen_analysis_hash_'+spec.kind,again.execution.analysis_hash==record.execution.analysis_hash)
                (out/('data_'+spec.kind+'.npz')).write_bytes(npz_bytes(record))

            for scope in ('bearing_fields','operating_map'):
                project,case=bearing_case(scope,out/'cache');use_project(project)
                app.bearing_job_dialog(case=case)
                await capture('setup_'+scope)
                record=await app.active_bearing_controls['run'](None)
                # Run callback returns its record; state is also checked independently.
                if record is None and app.session.records:record=app.session.records[-1]
                check('native_pipeline_'+scope,record is not None and app.session.is_current(record))
                for tab in FIELD_TABS if scope=='bearing_fields' else MAP_TABS:
                    app.result_set('view',tab[0]);await capture('view_'+scope+'_'+tab[0])
                (out/('data_'+scope+'.npz')).write_bytes(npz_bytes(record))

            use_project(RotorProject('Editores de engenharia',simple_model()))
            entities=[('nodes',None)]+[('shafts',x) for x in ('ShaftElement','TaperedShaftElement','AsymmetricShaftElement')]
            entities += [('disks',str(i)) for i in range(1,7)]+[('bearings',str(i)) for i in (1,2,3,4,5,6,7,8,20)]
            entities += [('forces',str(i)) for i in range(1,8)]+[('bend',None),('rotors',None)]
            entities += [('advanced_bearings',c.__name__) for c in ADVANCED_CLASSES]
            for kind,variant in entities:
                entity=make_entity(kind,app.session.project.model,variant)
                form=EntityForm(app,entity,kind);page.show_dialog(form.dialog)
                await capture('editor_'+kind+'_'+str(variant or 'default'))
                check('editor_identity_'+kind+'_'+str(variant or 'default'),form.build()==entity)
                if kind=='advanced_bearings' and variant in ('PlainJournalPhysicsBearing','TiltingPadPhysicsBearing'):
                    await form.body.scroll_to(offset=-1,duration=0)
                    await capture('editor_'+variant+'_bottom')
                page.pop_dialog()
            for kind in ('rotors','bend'):
                app.entity_collection_dialog(kind);await capture('table_'+kind);page.pop_dialog()
            for destination in ('analyses','results','reports','diagnostics','model','bearings'):
                app.navigate(destination);await capture('workspace_'+destination)
            # Fill reporting workspace with a real new record rather than an empty placeholder.
            project,case=screen_case('general_frf');use_project(project)
            record=await app.run_case(case)
            for destination in ('results','reports'):
                app.navigate(destination);await capture('workspace_'+destination+'_populated')
            app.navigate(record.id)
            app.export_formats_dialog();await capture('export_formats');page.pop_dialog()
            app.project_properties();await capture('project_properties');page.pop_dialog()
            app.about();await capture('about');page.pop_dialog()
            if args.file_dialogs:
                from drm_core import load_project
                expected = app.session.project.model.model_hash()
                upload = out / "upload_project.json"
                app.session.save(upload)
                def request_dialog(action, destination):
                    (out / "file_dialog.json").write_text(json.dumps({
                        "run_id": run_id, "action": action, "destination": str(destination),
                        "expected_hash": expected}), encoding="utf-8")
                request_dialog("save_project", out / "dialog_saved_project.json")
                await app.save_as()
                if not page.web:
                    check("os_save_project_roundtrip", load_project(out / "dialog_saved_project.json").model.model_hash() == expected)
                request_dialog("open_project", upload)
                app.session.reset(RotorProject("File-dialog empty fixture", simple_model()))
                await app.open_project()
                check("filepicker_upload_roundtrip", app.session.project.model.model_hash() == expected)
                request_dialog("export", out / "dialog_export.csv")
                await app.write_bytes(b"node;value\n1;123.456\n", "dialog_export.csv")
                if not page.web:
                    check("os_export_bytes", (out / "dialog_export.csv").read_bytes() == b"node;value\n1;123.456\n")
                    report["os_filepicker_interaction_test"] = True
                report["file_dialog_checks_finished"] = True
            check('all_current_cases_completed',len([c for c in report['checks'] if c.startswith('native_pipeline_')])==len(CATALOG)+2)
            check('all_screens_no_session_errors',not any(x[0] in ('ERRO','VISUALIZAÇÃO') for x in app.session.messages))
            if failed:raise AssertionError('A prior client session failed.')
            report['screenshots']=screenshots
            report['status']='PASS'
        except BaseException as exc:
            failed=True;report['status']='FAIL';report['error']=f'{type(exc).__name__}: {exc}'
            report['traceback']=traceback.format_exc();report['screenshots']=screenshots
            traceback.print_exc()
        finally:
            report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
            if app is not None:app.alive=False;app.animating=False
            if not page.web:
                with suppress(asyncio.CancelledError,RuntimeError,TimeoutError):
                    await asyncio.wait_for(page.window.destroy(),timeout=3)

    def start(page: ft.Page) -> None:
        nonlocal sessions_started, scenario_started, failed
        sessions_started += 1
        report["sessions_started"] = sessions_started
        if scenario_started:
            failed = True
            report["status"] = "FAIL"
            report.setdefault("error", "Unexpected client reconnection; no automatic retry allowed")
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            page.run_task(page.window.destroy)
            return
        scenario_started = True
        # Return from session initialization before waiting for client events.
        page.run_task(scenario, page)

    ft.run(start, view=ft.AppView.WEB_BROWSER if args.web else ft.AppView.FLET_APP,
           host="127.0.0.1", port=args.port if args.web else 0, no_cdn=True)
    actual = json.loads(report_path.read_text(encoding="utf-8"))
    if (actual.get("run_id") != run_id or actual.get("status") != "PASS" or failed
        or sessions_started != 1 or len(actual["checks"]) < 100 or len(set(actual["checks"])) != len(actual["checks"])):
        raise SystemExit("Desktop smoke failed or client exited before completing: " + str(report_path))
    print(f"CLIENT SMOKE PASS: {len(actual['checks'])} checks", flush=True)


if __name__ == "__main__":
    main()
