from __future__ import annotations

from pathlib import Path
import json

import numpy as np
from PySide6.QtCore import QEventLoop, QTimer

from drm_core import PlainJournalPhysicsBearing
from drm_studio.jobs import JobState


def _bearing():
    return PlainJournalPhysicsBearing(
        node=1,
        weight_n=112814.90696191376,
        journal_diameter_m=0.3999992,
        radial_clearance_m=0.000194564,
        oil_viscosity_pa_s=0.01901574061455835,
        pivot_angle_rad=(np.pi / 2.0, 3.0 * np.pi / 2.0),
        pad_arc_rad=(3.07177948351002, 3.07177948351002),
        pad_axial_length_m=(0.263144, 0.263144),
        preload=(0.0, 0.0),
        offset=(0.5, 0.5),
        total_e_x_film=20,
        total_e_z_film=10,
        total_e_y_pad=4,
        total_e_y_film=4,
        xj_ratio_initial=0.15,
        yj_ratio_initial=-0.2,
        force_tolerance=5e-3,
    )


def run_b14_frozen_field_smoke(window, output_dir):
    """Use the packaged Qt worker and packaged native library, not source mocks."""
    page = window.bearing_page
    bearing = _bearing()
    loop = QEventLoop()
    result = {}
    progress_seen = []
    failure = []

    runnable = page.jobs.submit(
        bearing,
        94.24777960769379,
        94.24777960769379,
        "B14_FROZEN_SMOKE",
    )

    def on_progress(request, progress):
        if request.request_id == runnable.request.request_id:
            progress_seen.append(progress)

    def on_completed(outcome):
        if outcome.request.request_id == runnable.request.request_id:
            result["payload"] = outcome.payload
            loop.quit()

    def on_cancelled(request, reason):
        if request.request_id == runnable.request.request_id:
            failure.append(f"unexpected cancellation: {reason}")
            loop.quit()

    def on_failed(item):
        if item.request.request_id == runnable.request.request_id:
            failure.append(f"{item.exception_type}: {item.message}")
            loop.quit()

    page.jobs.progress.connect(on_progress)
    page.jobs.completed.connect(on_completed)
    page.jobs.cancelled.connect(on_cancelled)
    page.jobs.failed.connect(on_failed)
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(lambda: (failure.append("timeout"), page.jobs.cancel(runnable), loop.quit()))
    timeout.start(45000)
    loop.exec()
    timeout.stop()

    if failure:
        raise RuntimeError("B14 frozen field smoke failed: " + "; ".join(failure))
    payload = result.get("payload")
    if payload is None:
        raise RuntimeError("B14 frozen field smoke published no payload")
    if not progress_seen:
        raise RuntimeError("B14 frozen field smoke observed no native progress")

    expected = {
        "pressure_field_pa": (2, 21, 11),
        "temperature_field_k": (2, 21, 11),
        "film_thickness_field_m": (2, 21, 11),
        "deformation_field_m": (2, 21),
        "theta_rad": (2, 21),
        "axial_position_m": (2, 11),
        "pad_load_n": (2,),
    }
    shapes = {}
    for key, shape in expected.items():
        value = np.asarray(payload[key])
        if value.shape != shape or not np.isfinite(value).all():
            raise RuntimeError(f"B14 frozen field {key} invalid: shape={value.shape}")
        shapes[key] = list(value.shape)
    if np.min(payload["film_thickness_field_m"]) <= 0.0:
        raise RuntimeError("B14 frozen native film thickness is non-positive")

    page._render_payload(payload, runnable.request.speed_rad_s, runnable.request.frequency_rad_s)
    for index in range(2, 8):
        if not page.lower_tabs.isTabEnabled(index):
            raise RuntimeError(f"B14 frozen visualization tab {index} not enabled")
    shot = Path(output_dir) / "B14_BEARING_PERFORMANCE.png"
    page.grab().save(str(shot))
    if not shot.exists() or shot.stat().st_size == 0:
        raise RuntimeError("B14 frozen Bearing Performance screenshot was not produced")

    evidence = {
        "status": "PASS",
        "request_id": runnable.request.request_id,
        "states": [JobState.QUEUED.value, JobState.RUNNING.value, JobState.COMPLETED.value],
        "progress_samples": len(progress_seen),
        "last_progress": {
            "stage": progress_seen[-1].stage,
            "percent": progress_seen[-1].percent,
        },
        "field_shapes": shapes,
        "visualization_tabs": [
            "Summary", "Dynamic Coefficients", "Pressure", "Temperature",
            "Film Thickness", "Deformation", "Pads", "Convergence",
        ],
        "screenshot": str(shot),
    }
    path = Path(output_dir) / "B14_FROZEN_FIELDS.json"
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True))
    return evidence
