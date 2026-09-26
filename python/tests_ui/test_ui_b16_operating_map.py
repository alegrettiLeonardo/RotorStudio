from __future__ import annotations

import numpy as np

from drm_core import CoefficientBearing, PlainJournalPhysicsBearing
from drm_studio.jobs import OperatingMapJobManager, JobState


def _coefficient():
    return CoefficientBearing(
        node=1,
        speed_rad_s=(80.0, 120.0),
        frequency_rad_s=(30.0, 70.0),
        interpolation="linear",
        kxx=((1.0e6, 1.1e6), (1.2e6, 1.3e6)),
        kyy=((1.4e6, 1.5e6), (1.6e6, 1.7e6)),
        cxx=((100.0, 110.0), (120.0, 130.0)),
        cyy=((140.0, 150.0), (160.0, 170.0)),
    )


def _physical():
    return PlainJournalPhysicsBearing(
        node=1,
        weight_n=112814.90696191376,
        journal_diameter_m=0.3999992,
        radial_clearance_m=0.000194564,
        oil_viscosity_pa_s=0.01901574061455835,
        pivot_angle_rad=(np.pi / 2.0, 3.0 * np.pi / 2.0),
        pad_arc_rad=(3.07177948351002,) * 2,
        pad_axial_length_m=(0.263144,) * 2,
        preload=(0.0, 0.0),
        offset=(0.5, 0.5),
        total_e_x_film=20,
        total_e_z_film=10,
        total_e_y_pad=4,
        total_e_y_film=4,
        xj_ratio_initial=0.15,
        yj_ratio_initial=-0.2,
        force_tolerance=5e-3,
        thermal_type="adiabatic",
        oil_supply_temperature_k=323.0,
        lubricant_density_kg_m3=854.9516,
        lubricant_cp_j_kgk=1951.5015,
        lubricant_conductivity_w_mk=0.15,
        viscosity2_pa_s=0.0077152334111,
        temperature1_k=322.9833333333,
        temperature2_k=352.9833333333,
        outer_iterations=50,
    )


def test_b16_map_job_generates_then_reuses_cache(qtbot, tmp_path):
    manager = OperatingMapJobManager()
    states = []
    progress = []
    manager.stateChanged.connect(lambda state, request: states.append(state))
    manager.progress.connect(lambda request, item: progress.append(item))
    with qtbot.waitSignal(manager.completed, timeout=10000) as signal:
        manager.submit(
            _coefficient(),
            (80.0, 120.0),
            (30.0, 70.0),
            interpolation="linear",
            cache_root=tmp_path,
            selection_key="bearing-A",
        )
    first = signal.args[0]
    assert first.result.source == "GENERATED"
    assert JobState.RUNNING.value in states
    assert progress and progress[-1].percent == 100.0

    with qtbot.waitSignal(manager.completed, timeout=5000) as signal:
        manager.submit(
            _coefficient(),
            (80.0, 120.0),
            (30.0, 70.0),
            interpolation="linear",
            cache_root=tmp_path,
            selection_key="bearing-A",
        )
    assert signal.args[0].result.source in {"L1", "L2"}


def test_b16_map_job_cancel_does_not_publish_or_promote_partial_map(qtbot, tmp_path):
    manager = OperatingMapJobManager()
    completed = []
    manager.completed.connect(completed.append)
    job = manager.submit(
        _physical(),
        (90.0, 100.0, 110.0),
        interpolation="linear",
        cache_root=tmp_path,
        selection_key="bearing-A",
    )
    with qtbot.waitSignal(manager.progress, timeout=30000):
        pass
    with qtbot.waitSignal(manager.cancelled, timeout=30000):
        assert manager.cancel(job)
    assert completed == []
    assert job.state == JobState.CANCELLED.value
    assert not [path for path in tmp_path.iterdir() if path.is_dir()]
