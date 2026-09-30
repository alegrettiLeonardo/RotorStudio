"""A5 regression: original-bearing authority follows ROSS's stable node order.

No historical goldens or tolerances are changed. Tests named native require
real Fortran; the binding-only checks are not a qualification substitute.
"""
from dataclasses import replace

import numpy as np
import pytest

from drm_core.domain.bearings import CoefficientBearing
from drm_core.domain.model import Bearing, Disk, Node, RotorModel, ShaftElement
from drm_core.solver import ucs_backend

FAMILIES = ("legacy3", "legacy5", "frequency", "map2d")
SPEED = (40.0, 120.0, 260.0, 480.0, 820.0)
FREQUENCY = (30.0, 100.0, 230.0, 470.0, 830.0)
FX = (4.6e6, 7.8e6, 1.33e7, 2.11e7, 3.28e7)
FY = (5.9e6, 9.1e6, 1.51e7, 2.39e7, 3.55e7)
GX = (
    (3.6e6, 4.2e6, 5.1e6, 6.3e6, 7.8e6),
    (5.1e6, 5.9e6, 7.0e6, 8.5e6, 1.03e7),
    (7.4e6, 8.4e6, 9.8e6, 1.17e7, 1.39e7),
    (1.04e7, 1.17e7, 1.35e7, 1.58e7, 1.86e7),
    (1.47e7, 1.63e7, 1.86e7, 2.15e7, 2.50e7),
)
GY = tuple(tuple(1.18 * x + 2e5 for x in row) for row in GX)


def bearing_pair(family):
    if family == "legacy3":
        return (Bearing(3, 1, (1.25e7, 1.25e7, 230.0, 230.0)),
                Bearing(3, 4, (2.1e7, 3.6e7, 310.0, 410.0)))
    if family == "legacy5":
        return (Bearing(5, 1, (1.25e7, 0.0, 0.0, 1.25e7, 230.0, 0.0, 0.0, 230.0)),
                Bearing(5, 4, (2.1e7, 0.0, 0.0, 3.6e7, 310.0, 0.0, 0.0, 410.0)))
    if family == "frequency":
        lower = CoefficientBearing(1, FX, 0.0, FY, 0.0,
                                   frequency_rad_s=FREQUENCY, tag="low-frequency")
    elif family == "map2d":
        lower = CoefficientBearing(1, GX, 0.0, GY, 0.0,
                                   speed_rad_s=SPEED, frequency_rad_s=FREQUENCY,
                                   interpolation="pchip", tag="low-map")
    else:
        raise ValueError(f"unknown test family: {family}")
    high_axis = (50.0, 150.0, 300.0, 550.0, 900.0)
    high_k = (2.1e7, 2.4e7, 2.8e7, 3.2e7, 3.6e7)
    higher = CoefficientBearing(4, high_k, 0.0, high_k, 0.0,
                                speed_rad_s=high_axis, tag="high-speed")
    return lower, higher


def make_model(family, supports):
    nodes = [Node(i + 1, z) for i, z in enumerate((0.0, 0.21, 0.48, 0.67))]
    shafts = [ShaftElement(2, i, i + 1, od, 0.014, 7810.0,
                          211e9, 81.2e9, 2.5e-3, 0.0, 0.0)
              for i, od in enumerate((0.054, 0.061, 0.049), 1)]
    disks = [Disk.inertial(3, 19.0, 0.083, 0.151)]
    if family.startswith("legacy"):
        return RotorModel(nodes, shafts, disks, list(supports))
    return RotorModel(nodes, shafts, disks, [], advanced_bearings=list(supports))


def validated(model, synchronous=False):
    values = ucs_backend._validate_model(None, model, (6.0, 10.0),
                                         7, 16, None, synchronous)
    return values[5], values[6], values[8]


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("synchronous", (False, True))
def test_first_original_bearing_follows_ross_node_order(family, synchronous):
    low, high = bearing_pair(family)
    model = make_model(family, [high, low])
    persisted = model.bearings if family.startswith("legacy") else model.advanced_bearings
    snapshot = model.model_hash()
    supports, _, seals = validated(model, synchronous)
    assert supports == sorted([high, low], key=lambda b: b.node)
    assert supports[0] is low
    assert supports is not persisted
    assert persisted[0] is high and persisted[1] is low
    assert model.model_hash() == snapshot
    assert seals == []


@pytest.mark.parametrize("family", FAMILIES)
def test_equal_node_order_is_stable_and_does_not_mutate_model(family):
    low, high = bearing_pair(family)
    second_low = replace(high, node=1)
    model = make_model(family, [high, low, second_low])
    before = model.model_hash()
    supports, _, _ = validated(model)
    assert supports[0] is low and supports[1] is second_low
    assert supports[2] is high
    assert model.model_hash() == before


def test_seals_are_excluded_without_becoming_the_first_original_bearing():
    low, high = bearing_pair("legacy3")
    seal = Bearing(8, 1, ())
    model = make_model("legacy3", [seal, high, low])
    before = model.model_hash()
    supports, _, seals = validated(model)
    assert supports[0] is low and supports[1] is high
    assert seals == [seal]
    assert model.bearings == [seal, high, low]
    assert model.model_hash() == before


@pytest.mark.parametrize("family", FAMILIES)
def test_original_bearing_owns_the_raw_kxx_kyy_family_decision(family):
    low, high = bearing_pair(family)
    supports, native_family, _ = validated(make_model(family, [high, low]))
    expected_equal = family.startswith("legacy")
    assert bool(ucs_backend._raw_equal(low, native_family)) == expected_equal
    assert bool(ucs_backend._raw_equal(high, native_family)) != expected_equal
    assert bool(ucs_backend._raw_equal(supports[0], native_family)) == expected_equal


@pytest.mark.parametrize("family", ("frequency", "map2d"))
def test_original_bearing_owns_speed_frequency_and_2d_axis_policy(family):
    low, high = bearing_pair(family)
    supports, native_family, _ = validated(make_model(family, [high, low]))
    expected_axis = FREQUENCY if family == "frequency" else SPEED
    np.testing.assert_array_equal(ucs_backend._axis(supports[0], native_family), expected_axis)


@pytest.mark.parametrize("family", ("legacy3", "legacy5"))
def test_constant_curve_uses_lowest_node_sentinel_not_first_inserted(family):
    low, high = bearing_pair(family)
    supports, native_family, _ = validated(make_model(family, [high, low]))
    kxx, kyy, _ = ucs_backend._curve(None, supports[0], native_family,
                                    np.array([40.0, 120.0, 260.0]))
    np.testing.assert_array_equal(kxx, np.full(3, 1.25e7))
    np.testing.assert_array_equal(kyy, np.full(3, 1.25e7))


def test_mixed_support_families_remain_fail_closed():
    low, high = bearing_pair("legacy3")
    model = make_model("legacy3", [high, low])
    model.advanced_bearings = [CoefficientBearing(2, 1e7, 0.0)]
    with pytest.raises(ValueError, match="first-bearing ordering"):
        validated(model)


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("synchronous", (False, True))
def test_native_permuted_supports_preserve_complete_numeric_ucs(family, synchronous):
    from drm_core import run_ucs
    from test_ucs import assert_result
    low, high = bearing_pair(family)
    ordered = make_model(family, [low, high])
    permuted = make_model(family, [high, low])
    before = permuted.model_hash()
    kwargs = dict(stiffness_range_exponents=(6, 10), num=7,
                  num_modes=16, synchronous=synchronous)
    if family.startswith("legacy"):
        ref_name = "synchronous_true" if synchronous else "isotropic_constant"
    elif not synchronous:
        ref_name = "frequency_axis" if family == "frequency" else "map_2d"
    else:
        ref_name = None
    actual = (assert_result(ref_name, permuted, **kwargs) if ref_name is not None
              else run_ucs(permuted, **kwargs))
    reference = run_ucs(ordered, **kwargs)
    numeric_fields = (
        "stiffness_log_n_m", "natural_frequency_rad_s", "bearing_speed_rad_s",
        "bearing_kxx_n_m", "bearing_kyy_n_m", "intersection_stiffness_n_m",
        "intersection_speed_rad_s", "intersection_mode_index", "intersection_coefficient",
        "critical_eigenvalue_real", "critical_eigenvalue_imag", "critical_wn_rad_s",
        "critical_wd_rad_s", "critical_damping_ratio", "critical_log_dec",
    )
    for name in numeric_fields:
        np.testing.assert_array_equal(getattr(actual, name), getattr(reference, name), err_msg=name)
    assert actual.bearing_speed_policy == reference.bearing_speed_policy
    assert actual.coefficient_families == reference.coefficient_families
    assert permuted.model_hash() == before
    assert permuted.bearings == ([high, low] if family.startswith("legacy") else [])
    assert permuted.advanced_bearings == ([] if family.startswith("legacy") else [high, low])
