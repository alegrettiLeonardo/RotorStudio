from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from drm_core import (
    BearingTableImportError,
    CoefficientBearing,
    ImportedBearingTable,
    load_irdin_project,
    load_project,
    parse_coefficient_table,
    parse_irdin_coefficient_table,
    save_project,
)
from drm_core.solver.bearings_backend import AdvancedBearingBackend
from drm_core.units import rpm_to_rad_s
from drm_core.importers.bearing_table import (
    IRDIN_SPEED_UNIT,
    IRDIN_STIFFNESS_UNIT,
    IRDIN_DAMPING_UNIT,
    IRDIN_COORDINATE_CONVENTION,
    IRDIN_CROSS_COUPLING_CONVENTION,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "examples" / "legacy" / "EST-12735185-CRYOSTAR_V2.txt"


def _contract(**overrides):
    values = {
        "speed_unit": IRDIN_SPEED_UNIT,
        "stiffness_unit": IRDIN_STIFFNESS_UNIT,
        "damping_unit": IRDIN_DAMPING_UNIT,
        "coordinate_convention": IRDIN_COORDINATE_CONVENTION,
        "cross_coupling_convention": IRDIN_CROSS_COUPLING_CONVENTION,
    }
    values.update(overrides)
    return values


def _synthetic_raw():
    return (
        "TABLE§1000|1000000|10000|-20000|1200000|100|10|-20|120"
        "§2000|2000000|20000|-40000|2400000|200|20|-40|240"
    )


def test_b15_real_cryostar_tables_become_typed_coefficient_bearings_without_sign_flip():
    project = load_irdin_project(FIXTURE)
    assert len(project.model.advanced_bearings) == 2
    for bearing, sketch in zip(project.model.advanced_bearings, project.metadata["sketch"]["bearings"]):
        assert isinstance(bearing, CoefficientBearing)
        assert sketch["table_mapped"] is True
        assert bearing.node == sketch["node"]
        assert project.model.nodes[bearing.node - 1].z_m == pytest.approx(
            sketch["position_mm"] / 1000.0, abs=1e-12
        )
        np.testing.assert_allclose(
            bearing.speed_rad_s,
            [rpm_to_rad_s(row["rpm"]) for row in sketch["table"]],
            rtol=0.0,
            atol=2e-13,
        )
        # No hidden sign convention: the negative source cross-couplings stay negative.
        assert bearing.kxy[0] == sketch["table"][0]["kxy"] < 0.0
        assert bearing.kyx[0] == sketch["table"][0]["kyx"] < 0.0
        assert bearing.cxy[0] == sketch["table"][0]["cxy"] < 0.0
        assert bearing.cyx[0] == sketch["table"][0]["cyx"] < 0.0
        assert bearing.provenance["sign_transform"] == "NONE"


def test_b15_table_points_match_source_at_near_machine_precision():
    project = load_irdin_project(FIXTURE)
    backend = AdvancedBearingBackend()
    for bearing, sketch in zip(project.model.advanced_bearings, project.metadata["sketch"]["bearings"]):
        for row in sketch["table"]:
            evaluation = backend.evaluate(
                bearing,
                speed_rad_s=float(rpm_to_rad_s(row["rpm"])),
            )
            actual = np.array([
                evaluation.K[0, 0], evaluation.K[0, 1],
                evaluation.K[1, 0], evaluation.K[1, 1],
                evaluation.C[0, 0], evaluation.C[0, 1],
                evaluation.C[1, 0], evaluation.C[1, 1],
            ])
            expected = np.array([
                row["kxx"], row["kxy"], row["kyx"], row["kyy"],
                row["cxx"], row["cxy"], row["cyx"], row["cyy"],
            ])
            np.testing.assert_allclose(actual, expected, rtol=3e-15, atol=2e-7)


@pytest.mark.parametrize("interpolation", ["linear", "pchip"])
def test_b15_linear_and_pchip_midpoints_and_roundtrip(interpolation, tmp_path):
    imported = parse_irdin_coefficient_table(_synthetic_raw(), node=2)
    bearing = imported.to_coefficient_bearing(interpolation=interpolation, tag="B15 sentinel")
    backend = AdvancedBearingBackend()
    midpoint = float(rpm_to_rad_s(1500.0))
    result = backend.evaluate(bearing, midpoint)
    np.testing.assert_allclose(
        [result.K[0, 0], result.K[0, 1], result.K[1, 0], result.K[1, 1]],
        [1.5e6, 1.5e4, -3.0e4, 1.8e6],
        rtol=2e-14,
        atol=2e-8,
    )
    from drm_core import Node, RotorModel, RotorProject, ShaftElement
    project = RotorProject(
        "b15",
        RotorModel(
            nodes=[Node(1, 0.0), Node(2, 1.0)],
            shafts=[ShaftElement(2, 1, 2, 0.05, 0.0, 7800.0, 210e9, 80e9)],
            advanced_bearings=[bearing],
        ),
    )
    path = tmp_path / "b15.rds"
    save_project(project, path)
    reopened = load_project(path)
    assert reopened.model.advanced_bearings == [bearing]


@pytest.mark.parametrize(
    ("raw", "kwargs", "match"),
    [
        ("TABLE", {}, "empty"),
        (
            "TABLE§1000|1|2|3|4|5|6|7|NaN",
            {},
            "non-finite",
        ),
        (
            "TABLE§1000|1|2|3|4|5|6|7|8§1000|2|3|4|5|6|7|8|9",
            {},
            "strictly increasing",
        ),
        (
            "TABLE§rpm|Kxx|Kxy|Kyx|Kyy|Cxx|Cxy|Cyx|WRONG§1000|1|2|3|4|5|6|7|8",
            {},
            "invalid coefficient columns",
        ),
        (
            _synthetic_raw(),
            {"speed_unit": "rad/s"},
            "unknown/ambiguous",
        ),
        (
            _synthetic_raw(),
            {"coordinate_convention": "Y/X"},
            "unknown/ambiguous",
        ),
        (
            _synthetic_raw(),
            {"cross_coupling_convention": "ambiguous"},
            "unknown/ambiguous",
        ),
    ],
)
def test_b15_fail_closed_table_contract(raw, kwargs, match):
    contract = _contract(**kwargs)
    with pytest.raises(BearingTableImportError, match=match):
        parse_coefficient_table(raw, node=1, **contract)


def test_b15_invalid_node_fails_closed():
    with pytest.raises(BearingTableImportError, match="node=0"):
        parse_irdin_coefficient_table(_synthetic_raw(), node=0)


def test_b15_real_cryostar_only_removes_bearing_table_blocker():
    project = load_irdin_project(FIXTURE)
    readiness = project.metadata["numerical_readiness"]
    assert readiness["status"] == "BLOCKED_FOR_NUMERICAL_ANALYSIS"
    codes = {item["code"] for item in readiness["blockers"]}
    assert readiness["mapped_inline_bearing_tables"] == 2
    assert "IRDIN_BEARING_COEFFICIENT_TABLE_UNMAPPED" not in codes
    assert "IRDIN_DISTRIBUTED_MASS_UNMAPPED" in codes


def test_b15_flexible_support_blocker_remains_granular(tmp_path):
    source = tmp_path / "support.txt"
    source.write_text(
        """[Dados]
S_MELAST=207000000000
S_MASESP=7850
S_POISSON=0.3
COMP=B15-SUPPORT
[Secoes]
1,0=1000
1,1=100
[Mancais]
1,0=500
1,10=B1
1,11=TABLE§1000|1e6|0|0|1e6|100|0|0|100§2000|2e6|0|0|2e6|200|0|0|200
[Suporte]
1,0=1
1,1=100000
1,2=100000
1,3=0
1,4=0
1,5=100
1,6=100
1,7=0
1,8=0
1,9=10
1,10=SUPPORT
""",
        encoding="utf-8",
    )
    project = load_irdin_project(source)
    codes = {item["code"] for item in project.metadata["numerical_readiness"]["blockers"]}
    assert "IRDIN_FLEXIBLE_SUPPORT_UNMAPPED" in codes
    assert "IRDIN_BEARING_COEFFICIENT_TABLE_UNMAPPED" not in codes
    assert len(project.model.advanced_bearings) == 1
