"""Real Flet desktop render + handler/Core smoke. Run under Xvfb on Linux.

This is not a frozen-executable test or an OS FilePicker interaction test.
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path("validation/reports/flet_desktop"))
    args = parser.parse_args()
    out = args.outdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "desktop_smoke.json"
    run_id = uuid.uuid4().hex
    report = {"run_id": run_id, "status": "RUNNING", "checks": [],
              "platform": platform.platform(), "python": platform.python_version(),
              "flet": importlib.metadata.version("flet"),
              "desktop_rendering": True, "frozen_executable_test": False,
              "os_filepicker_interaction_test": False,
              "model": "Explicit synthetic reference input; real Core/Fortran results"}
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
        try:
            library = os.environ["DRMROTOR_LIB"]
            check("native_library_exists", Path(library).is_file())
            report["native_library_sha256"] = sha256(Path(library).read_bytes()).hexdigest()
            app = StudioApp(page, library_path=library)

            async def screenshot(name: str) -> None:
                await asyncio.sleep(1.0)
                data = await page.take_screenshot()
                check(name + "_is_png", data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) > 10000)
                (out / (name + ".png")).write_bytes(data)
                check(name + "_no_plot_error", not any(level == "VISUALIZAÇÃO" for level, _ in app.session.messages))

            await screenshot("01_modelo_rotor")
            initial = app.session.project.model.model_hash()
            app.form_fields["outer_diameter_m"].value = "141,375"
            app.apply_clicked()
            check("form_mm_to_m", abs(app.session.selected().outer_diameter_m - .141375) < 1e-14)
            changed = app.session.project.model.model_hash()
            app.form_fields["inner_diameter_m"].value = "999"
            check("invalid_edit_rejected", not app.apply_properties())
            check("invalid_edit_rollback", app.session.project.model.model_hash() == changed)
            page.pop_dialog()
            app.render()
            app.undo()
            check("undo_restores_model", app.session.project.model.model_hash() == initial)
            app.redo()
            check("redo_restores_sentinel", app.session.project.model.model_hash() == changed)
            app.undo()

            case = AnalysisCase("modal_sweep", {
                "speeds_rad_s": rpm_to_rad_s(np.linspace(0, 6000, 31)).tolist(),
                "with_eigenvectors": True, "with_kappa": True,
                "coefficient_policy": "SYNCHRONOUS_COEFFICIENTS",
            }, "Campbell_01")
            campbell = await app.run_case(case)
            check("campbell_completed", campbell is not None and len(campbell.execution.result) == 31)
            check("campbell_current", app.session.is_current(campbell))
            direct = await asyncio.to_thread(AnalysisService(library).execute, app.session.project, case)
            for actual, expected in zip(campbell.execution.result, direct.result):
                np.testing.assert_allclose(actual.eigenvalues, expected.eigenvalues, rtol=1e-12, atol=1e-9)
                np.testing.assert_allclose(actual.eigenvectors, expected.eigenvectors, rtol=1e-12, atol=1e-10)
            check("campbell_direct_core_parity_31_points", True)
            app.speed_selected(SimpleNamespace(control=SimpleNamespace(value="18")))
            await screenshot("02_campbell")

            app.navigate("model")
            app.form_fields["outer_diameter_m"].value = "141,375"
            app.apply_clicked()
            check("edit_marks_result_stale", not app.session.is_current(campbell))
            app.undo()
            check("undo_restores_result_freshness", app.session.is_current(campbell))

            app.navigate("bearings")
            await app.bearing_analysis()
            bearing = app.bearing_record
            check("bearing_native_sweep_25_points", bearing is not None and len(bearing.execution.result.K) == 25)
            app.bearing_point(12)
            await screenshot("03_mancais")
            app.bearing_metric(True)
            check("bearing_C_plot", app.plot_png is not None)
            app.bearing_metric(False)

            app.navigate(campbell.id)
            app.mode_selected(0)
            app.speed_selected(SimpleNamespace(control=SimpleNamespace(value="18")))
            app.toggle_theme()
            frame_before = app.plot_png
            app.phase_slider.value = 45
            app.phase_changed(SimpleNamespace(control=app.phase_slider))
            check("modal_phase_changes_actual_plot", frame_before != app.plot_png)
            await screenshot("04_modos_3d_escuro")
            check("modal_display_does_not_change_model", app.session.project.model.model_hash() == initial)

            saved = out / "reference_project.json"
            app.session.save(saved)
            reopened = StudioSession()
            reopened.open(saved)
            check("save_reopen_project_hash", reopened.project.project_hash() == app.session.project.project_hash())
            reopened_case = next(c for c in reopened.project.analyses if c.name == case.name)
            again = await asyncio.wrap_future(NativeJob(reopened.project, reopened_case, library).future)
            for actual, expected in zip(again.execution.result, campbell.execution.result):
                np.testing.assert_allclose(actual.eigenvalues, expected.eigenvalues, rtol=1e-12, atol=1e-9)
            check("reopen_recompute_parity", True)
            (out / "campbell.csv").write_bytes(csv_bytes(campbell))
            (out / "campbell.npz").write_bytes(npz_bytes(campbell))
            (out / "campbell_report.zip").write_bytes(report_bytes(campbell, current=True, png=app.plot_png))
            check("real_numeric_exports_written", all((out / p).is_file() for p in ("campbell.csv", "campbell.npz", "campbell_report.zip")))
            report["analysis_hash"] = campbell.execution.analysis_hash
            report["model_hash"] = initial
            if failed:
                raise AssertionError("A prior session failed; automatic retries do not qualify")
            report["status"] = "PASS"
        except BaseException as exc:
            failed = True
            report["status"] = "FAIL"
            report["error"] = f"{type(exc).__name__}: {exc}"
            report["traceback"] = traceback.format_exc()
            traceback.print_exc()
        finally:
            report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            if app is not None:
                app.alive = False
                app.animating = False
            with suppress(asyncio.CancelledError, RuntimeError, TimeoutError):
                await asyncio.wait_for(page.window.destroy(), timeout=3)

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

    ft.run(start, view=ft.AppView.FLET_APP)
    actual = json.loads(report_path.read_text(encoding="utf-8"))
    if (actual.get("run_id") != run_id or actual.get("status") != "PASS" or failed
        or sessions_started != 1 or len(actual["checks"]) != 26 or len(set(actual["checks"])) != 26):
        raise SystemExit("Desktop smoke failed or client exited before completing: " + str(report_path))
    print(f"DESKTOP SMOKE PASS: {len(actual['checks'])} checks", flush=True)


if __name__ == "__main__":
    main()
