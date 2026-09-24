from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from drm_core import AnalysisCase, RotorProject, AnalysisExecution
from drm_core.units import rpm_to_rad_s
from drm_studio.application.session import ProjectSession
from drm_studio.commands import SetShaftPropertyCommand
from drm_studio.main_window import MainWindow
from drm_studio.result_views.io import (
    export_record_csv, export_record_native, export_record_report,
    export_view_plot_bundle,
)

ROOT = Path(__file__).resolve().parents[2]


def _load_example():
    path = ROOT / "examples" / "chapter05" / "example_05_08_01.py"
    spec = importlib.util.spec_from_file_location("stage2_export_example", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(not os.environ.get("DRMROTOR_LIB"), reason="real Fortran library required")
def test_real_modal_exports_and_report(qtbot, tmp_path):
    model = _load_example().build(6)
    case = AnalysisCase(
        "modal",
        {
            "speed_rad_s": float(rpm_to_rad_s(3210.0)),
            "with_eigenvectors": True,
            "with_kappa": True,
        },
        "Modal Export Sentinel",
    )
    project = RotorProject("Export Sentinel Project", model, [case])
    window = MainWindow(session=ProjectSession(project))
    qtbot.addWidget(window)
    window.show()

    with qtbot.waitSignal(window.session.resultAdded, timeout=60000) as signal:
        assert window.run_analysis(case)
    record = signal.args[0]

    csv_path = export_record_csv(record, tmp_path / "modal.csv")
    assert csv_path.exists() and csv_path.stat().st_size > 0
    data = np.genfromtxt(csv_path, delimiter=",", names=True)
    assert data.size > 0
    reconstructed = data["eigenvalue_real_rad_s"] + 1j * data["eigenvalue_imag_rad_s"]
    assert np.allclose(reconstructed, record.execution.result.eigenvalues)
    assert np.isfinite(data["natural_frequency_hz"]).all()

    native = export_record_native(record, tmp_path / "modal.npz")
    loaded = np.load(native)
    assert loaded["data"].shape[0] == record.execution.result.eigenvalues.size
    assert loaded["analysis_hash"][0] == record.execution.analysis_hash

    view = window._result_tabs[record.key]
    written = export_view_plot_bundle(view, tmp_path / "modal_plot")
    assert written["png"].read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    ET.parse(written["svg"])
    assert written["pdf"].read_bytes()[:5] == b"%PDF-"

    reports = export_record_report(record, tmp_path / "report")
    payload = json.loads(reports["json"].read_text())
    assert payload["status"] == "COMPLETED"
    assert payload["build_metadata"]["project_name"] == "Export Sentinel Project"
    assert payload["build_metadata"]["backend"] == "Fortran2018/ctypes"
    assert payload["result"]["natural_frequency_hz"]["preview"]
    assert "Canonical SI" in payload["unit_convention"]
    markdown = reports["markdown"].read_text()
    assert "Result summary" in markdown
    assert "Traceback" not in markdown


def test_stale_then_undo_returns_result_to_current():
    model = _load_example().build(6)
    session = ProjectSession(RotorProject("Stale restoration", model))
    case = AnalysisCase("modal", {"speed_rad_s": 0.0}, "Modal Baseline")
    fake = AnalysisExecution(
        case=case,
        result=object(),
        analysis_hash="unit-only",
        build_metadata={"model_hash": session.current_model_hash},
    )
    record = session.add_result(fake)
    original = session.project.model.shafts[0].outer_diameter_m

    session.undo_stack.push(
        SetShaftPropertyCommand(session, 0, "outer_diameter_m", original * 1.01)
    )
    assert record.stale is True
    session.undo_stack.undo()
    assert record.stale is False
