from __future__ import annotations

import math

import pytest

from drm_core import Node, RotorModel, RotorProject
from drm_core.domain.bearings import (
    CoefficientBearing,
    PlainJournalPhysicsBearing,
    TiltingPadPhysicsBearing,
    advanced_bearing_from_dict,
    advanced_bearing_to_dict,
    validate_advanced_bearing,
)
from drm_core.stage1 import load_project, save_project


def _plain(node=1, **changes):
    kwargs = dict(
        node=node,
        weight_n=1234.5,
        journal_diameter_m=0.1016,
        radial_clearance_m=74.9e-6,
        oil_viscosity_pa_s=0.019,
        pivot_angle_rad=(math.radians(90), math.radians(270)),
        pad_arc_rad=(math.radians(176), math.radians(176)),
        pad_axial_length_m=(0.0501, 0.0502),
        preload=(0.0, 0.0),
        offset=(0.49, 0.51),
        tag="PJ sentinel",
    )
    kwargs.update(changes)
    return PlainJournalPhysicsBearing(**kwargs)


def _tilting(node=1, **changes):
    kwargs = dict(
        node=node,
        weight_n=2345.6,
        journal_diameter_m=0.1016,
        radial_clearance_m=74.9e-6,
        oil_viscosity_pa_s=0.0213,
        pad_thickness_m=0.0127,
        pad_density_kg_m3=7835.6,
        pivot_angle_rad=tuple(math.radians(x) for x in (18, 90, 162, 234, 306)),
        pad_arc_rad=tuple(math.radians(x) for x in (58, 59, 60, 61, 62)),
        pad_axial_length_m=tuple(x * 1e-3 for x in (50.1, 50.2, 50.3, 50.4, 50.5)),
        preload=(0.41, 0.42, 0.43, 0.44, 0.45),
        offset=(0.46, 0.47, 0.48, 0.49, 0.50),
        k_rotate_nm_rad=(101001, 102002, 103003, 104004, 105005),
        tag="TP sentinel",
    )
    kwargs.update(changes)
    return TiltingPadPhysicsBearing(**kwargs)


@pytest.mark.parametrize(
    "bearing",
    [
        CoefficientBearing(node=1, kxx=1.01e6, cxx=101.0),
        CoefficientBearing(
            node=1,
            speed_rad_s=(101.0, 202.0, 303.0),
            kxx=(1.01e6, 1.02e6, 1.03e6),
            cxx=(101.0, 102.0, 103.0),
            interpolation="pchip",
        ),
        CoefficientBearing(
            node=1,
            frequency_rad_s=(111.0, 222.0),
            kxx=(2.01e6, 2.02e6),
            cxx=(201.0, 202.0),
            interpolation="linear",
        ),
        CoefficientBearing(
            node=1,
            speed_rad_s=(101.0, 202.0),
            frequency_rad_s=(303.0, 404.0, 505.0),
            kxx=((11.0, 12.0, 13.0), (21.0, 22.0, 23.0)),
            cxx=((1.1, 1.2, 1.3), (2.1, 2.2, 2.3)),
            mxx=((0.11, 0.12, 0.13), (0.21, 0.22, 0.23)),
            interpolation="pchip",
        ),
    ],
)
def test_b13_coefficient_contracts_and_roundtrip(bearing):
    validate_advanced_bearing(bearing)
    restored = advanced_bearing_from_dict(advanced_bearing_to_dict(bearing))
    assert restored == bearing


def test_b13_coefficient_rejects_invalid_axes_and_shapes():
    with pytest.raises(ValueError, match="strictly increasing"):
        validate_advanced_bearing(
            CoefficientBearing(
                node=1,
                speed_rad_s=(100.0, 100.0),
                kxx=(1.0, 2.0),
                cxx=(1.0, 2.0),
            )
        )
    with pytest.raises(ValueError, match="received shape"):
        validate_advanced_bearing(
            CoefficientBearing(
                node=1,
                speed_rad_s=(100.0, 200.0),
                frequency_rad_s=(10.0, 20.0),
                kxx=(1.0, 2.0),
                cxx=1.0,
            )
        )


def test_b13_plain_thermal_deformation_paths_and_roundtrip():
    base = _plain()
    validate_advanced_bearing(base)
    thermal = _plain(
        thermal_type="full",
        deform_type="pad_mechanical_thermal",
        pad_thickness_m=0.0127,
        oil_supply_temperature_k=313.15,
        lubricant_density_kg_m3=861.2,
        lubricant_cp_j_kgk=1932.1,
        lubricant_conductivity_w_mk=0.131,
        viscosity2_pa_s=0.0107,
        temperature1_k=313.15,
        temperature2_k=353.15,
        pad_conductivity_w_mk=46.3,
        pad_young_pa=207.321e9,
        pad_poisson=0.291,
        pad_expansion_1_k=11.7e-6,
    )
    validate_advanced_bearing(thermal)
    assert advanced_bearing_from_dict(advanced_bearing_to_dict(thermal)) == thermal

    with pytest.raises(ValueError, match="equal lengths"):
        validate_advanced_bearing(_plain(preload=(0.1,)))
    with pytest.raises(ValueError, match="preload"):
        validate_advanced_bearing(_plain(preload=(0.1, 1.05)))
    with pytest.raises(ValueError, match="Reynolds element counts"):
        validate_advanced_bearing(_plain(total_e_x_film=21))


def test_b13_tilting_pad_variants_and_roundtrip():
    bearing = _tilting()
    validate_advanced_bearing(bearing)
    assert advanced_bearing_from_dict(advanced_bearing_to_dict(bearing)) == bearing
    with pytest.raises(ValueError, match="equal lengths"):
        validate_advanced_bearing(_tilting(k_rotate_nm_rad=(1.0,)))
    with pytest.raises(ValueError, match="preload"):
        validate_advanced_bearing(_tilting(preload=(0.1, 0.2, 0.3, 0.4, 1.05)))
    with pytest.raises(ValueError, match="offset"):
        validate_advanced_bearing(_tilting(offset=(0.1, 0.2, 0.3, 0.4, 1.0)))
    with pytest.raises(ValueError, match="even"):
        validate_advanced_bearing(_tilting(total_e_z_film=9))


def test_b13_typed_project_roundtrip_and_hash_contract(tmp_path):
    legacy = RotorModel(nodes=[Node(1, 0.0)])
    legacy_hash = legacy.model_hash()
    # Empty advanced_bearings remains absent from canonical payload, preserving
    # historical legacy hashing behavior.
    assert "advanced_bearings" not in legacy.canonical_dict()
    assert legacy.model_hash() == legacy_hash

    coeff = CoefficientBearing(
        node=1,
        speed_rad_s=(101.0, 202.0),
        frequency_rad_s=(303.0, 404.0),
        kxx=((11.0, 12.0), (21.0, 22.0)),
        cxx=((1.1, 1.2), (2.1, 2.2)),
        mxx=((0.11, 0.12), (0.21, 0.22)),
        interpolation="linear",
        tag="coeff sentinel",
        provenance={"provider": "B12 fixture", "user_note": "safe"},
    )
    model = RotorModel(nodes=[Node(1, 0.0)], advanced_bearings=[coeff, _plain(), _tilting()])
    path = tmp_path / "b13.rds"
    save_project(RotorProject("B13 roundtrip", model), path)
    reopened = load_project(path)
    assert reopened.model.advanced_bearings == model.advanced_bearings
    before = reopened.model.model_hash()
    reopened.model.advanced_bearings[0] = CoefficientBearing(
        **{
            **{k: v for k, v in advanced_bearing_to_dict(coeff).items() if k not in {"__type__", "model_family"}},
            "kxx": ((11.0, 12.0), (21.0, 22.12345)),
        }
    )
    assert reopened.model.model_hash() != before
