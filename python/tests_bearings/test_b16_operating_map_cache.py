from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import time

import numpy as np
import pytest

from drm_core import (
    BearingMapCache,
    BearingMapCacheCorruption,
    BearingMapCancelled,
    CoefficientBearing,
    Node,
    PlainJournalPhysicsBearing,
    RotorModel,
    ShaftElement,
    TiltingPadPhysicsBearing,
    generate_operating_map,
)
from drm_core.solver.bearings_backend import AdvancedBearingBackend


def _plain(**changes):
    base = PlainJournalPhysicsBearing(
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
        total_e_x_film=8,
        total_e_z_film=4,
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
        relax_temperature=0.35,
        outer_iterations=20,
    )
    return replace(base, **changes)


def _tilting():
    return TiltingPadPhysicsBearing(
        node=1,
        weight_n=112814.90696191376,
        journal_diameter_m=0.3999992,
        radial_clearance_m=0.000194564,
        oil_viscosity_pa_s=0.01901574061455835,
        pad_thickness_m=0.149614636,
        pad_density_kg_m3=7835.631544657211,
        pivot_angle_rad=(
            0.9424777960769379,
            2.199114857512855,
            3.4557519189487724,
            4.71238898038469,
            5.969026041820607,
        ),
        pad_arc_rad=(1.0471975511965976,) * 5,
        pad_axial_length_m=(0.263144,) * 5,
        preload=(0.3,) * 5,
        offset=(0.5,) * 5,
        k_rotate_nm_rad=(0.0,) * 5,
        total_e_x_film=8,
        total_e_z_film=4,
        total_e_y_pad=4,
        total_e_y_film=4,
        xj_ratio_initial=0.15,
        yj_ratio_initial=-0.2,
        force_tolerance=5e-3,
        outer_iterations=12,
    )


def _synthetic():
    speed = (80.0, 120.0)
    frequency = (30.0, 70.0)
    def surface(a, b, c=0.0):
        return tuple(tuple(a*s + b*w + c for w in frequency) for s in speed)
    return CoefficientBearing(
        node=1,
        speed_rad_s=speed,
        frequency_rad_s=frequency,
        interpolation="linear",
        kxx=surface(10.0, 2.0, 1e6),
        kxy=surface(1.0, -0.5, 2e4),
        kyx=surface(-2.0, 0.25, -3e4),
        kyy=surface(8.0, 3.0, 1.2e6),
        cxx=surface(0.1, 0.02, 100.0),
        cxy=surface(0.01, -0.005, 5.0),
        cyx=surface(-0.02, 0.004, -7.0),
        cyy=surface(0.08, 0.03, 120.0),
    )


def test_b16_2d_synthetic_map_exact_at_table_and_interpolated_points():
    source = _synthetic()
    backend = AdvancedBearingBackend()
    operating_map = generate_operating_map(
        source,
        speed_rad_s=(80.0, 120.0),
        frequency_rad_s=(30.0, 70.0),
        interpolation="linear",
        backend=backend,
    )
    mapped = operating_map.to_coefficient_bearing()
    for omega in (80.0, 100.0, 120.0):
        for whirl in (30.0, 50.0, 70.0):
            direct = backend.evaluate(source, omega, whirl)
            cached = backend.evaluate(mapped, omega, whirl)
            np.testing.assert_allclose(cached.K, direct.K, rtol=2e-14, atol=2e-8)
            np.testing.assert_allclose(cached.C, direct.C, rtol=2e-14, atol=2e-12)


def test_b16_plain_synchronous_tabulated_points_match_direct_physics():
    bearing = _plain()
    backend = AdvancedBearingBackend()
    speeds = (90.0, 100.0, 110.0)
    operating_map = generate_operating_map(
        bearing, speeds, interpolation="linear", backend=backend
    )
    mapped = operating_map.to_coefficient_bearing()
    for speed in speeds:
        direct = backend.evaluate(bearing, speed, speed)
        cached = backend.evaluate(mapped, speed, speed)
        np.testing.assert_allclose(cached.K, direct.K, rtol=3e-13, atol=1e-5)
        np.testing.assert_allclose(cached.C, direct.C, rtol=3e-13, atol=1e-6)


def test_b16_tilting_2d_interpolation_matches_nearby_direct_asynchronous_solve():
    bearing = _tilting()
    backend = AdvancedBearingBackend()
    operating_map = generate_operating_map(
        bearing,
        speed_rad_s=(94.0, 96.0),
        frequency_rad_s=(46.0, 48.0),
        interpolation="linear",
        backend=backend,
    )
    mapped = operating_map.to_coefficient_bearing()
    direct = backend.evaluate(bearing, 95.0, 47.0)
    cached = backend.evaluate(mapped, 95.0, 47.0)
    # The cell is intentionally narrow (2 rad/s in each axis); this is an
    # interpolation-discretization gate, not a relaxation of B12 solver parity.
    np.testing.assert_allclose(cached.K, direct.K, rtol=2e-2, atol=50.0)
    np.testing.assert_allclose(cached.C, direct.C, rtol=2e-2, atol=1.0)
    assert 95.0 != 47.0


def test_b16_cache_key_invalidation_covers_physical_inputs_mesh_thermal_and_axes(tmp_path):
    backend = AdvancedBearingBackend()
    cache = BearingMapCache(tmp_path)
    base = _plain()
    axes = (90.0, 100.0)
    key = cache.cache_key_for(base, axes, backend=backend)
    assert key == cache.cache_key_for(base, axes, backend=backend)
    assert key != cache.cache_key_for(
        replace(base, radial_clearance_m=base.radial_clearance_m * 1.01),
        axes,
        backend=backend,
    )
    assert key != cache.cache_key_for(
        replace(base, total_e_x_film=10),
        axes,
        backend=backend,
    )
    assert key != cache.cache_key_for(
        replace(base, thermal_type=None),
        axes,
        backend=backend,
    )
    assert key != cache.cache_key_for(base, (90.0, 101.0), backend=backend)


def test_b16_l1_l2_atomic_cache_corruption_rejected_and_recomputed(tmp_path):
    backend = AdvancedBearingBackend()
    source = _synthetic()
    cache = BearingMapCache(tmp_path)
    first = cache.get_or_generate(
        source, (80.0, 120.0), (30.0, 70.0),
        interpolation="linear", backend=backend,
    )
    assert first.source == "GENERATED"
    assert (tmp_path / first.cache_key / "manifest.json").is_file()
    assert (tmp_path / first.cache_key / "coefficients.npz").is_file()
    warm = cache.get_or_generate(
        source, (80.0, 120.0), (30.0, 70.0),
        interpolation="linear", backend=backend,
    )
    assert warm.source == "L1"

    # Force L2, then corrupt the data. A direct L2 read rejects it; the normal
    # get_or_generate path invalidates and regenerates instead of trusting it.
    cache2 = BearingMapCache(tmp_path)
    l2 = cache2.get(first.cache_key)
    assert l2 is not None and l2.source == "L2"
    (tmp_path / first.cache_key / "coefficients.npz").write_bytes(b"corrupt")
    cache3 = BearingMapCache(tmp_path)
    with pytest.raises(BearingMapCacheCorruption):
        cache3.get(first.cache_key)
    regenerated = cache3.get_or_generate(
        source, (80.0, 120.0), (30.0, 70.0),
        interpolation="linear", backend=backend,
    )
    assert regenerated.source == "GENERATED"
    assert regenerated.cache_key == first.cache_key


def test_b16_cancelled_generation_never_promotes_partial_cache(tmp_path):
    backend = AdvancedBearingBackend()
    cache = BearingMapCache(tmp_path)
    bearing = _plain()
    speeds = (90.0, 100.0, 110.0)
    cancel = {"value": False}

    def progress(completed, total, point):
        if completed >= 1:
            cancel["value"] = True

    key = cache.cache_key_for(bearing, speeds, backend=backend)
    with pytest.raises(BearingMapCancelled):
        cache.get_or_generate(
            bearing,
            speeds,
            backend=backend,
            progress_callback=progress,
            cancel_check=lambda: cancel["value"],
        )
    assert not (tmp_path / key).exists()
    assert not any(path.name.startswith(f".{key}.tmp-") for path in tmp_path.glob("*"))


def test_b16_warm_cache_is_materially_cheaper_than_repeated_physical_evaluation(tmp_path, capsys):
    backend = AdvancedBearingBackend()
    bearing = _plain()
    speeds = (92.0, 98.0, 104.0)
    start = time.perf_counter()
    for speed in speeds:
        backend.evaluate(bearing, speed, speed)
    direct = time.perf_counter() - start

    cache = BearingMapCache(tmp_path)
    start = time.perf_counter()
    cold = cache.get_or_generate(bearing, speeds, backend=backend)
    cold_elapsed = time.perf_counter() - start
    assert cold.source == "GENERATED"

    start = time.perf_counter()
    warm = cache.get_or_generate(bearing, speeds, backend=backend)
    warm_elapsed = time.perf_counter() - start
    assert warm.source == "L1"
    print(
        f"B16_PERFORMANCE direct_physical={direct:.6f}s "
        f"cold_map={cold_elapsed:.6f}s warm_cache={warm_elapsed:.6f}s"
    )
    assert warm_elapsed < direct
    assert warm_elapsed < cold_elapsed


def test_b16_cache_does_not_mutate_physical_model_hash(tmp_path):
    backend = AdvancedBearingBackend()
    bearing = _plain()
    model = RotorModel(
        nodes=[Node(1, 0.0), Node(2, 1.0)],
        shafts=[ShaftElement(2, 1, 2, 0.05, 0.0, 7800.0, 210e9, 80e9)],
        advanced_bearings=[bearing],
    )
    before = model.model_hash()
    BearingMapCache(tmp_path).get_or_generate(
        bearing, (90.0, 100.0), backend=backend
    )
    assert model.model_hash() == before
