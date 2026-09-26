from pathlib import Path

import pytest

from drm_core import AnalysisCase, AnalysisService, load_irdin_project, load_project, save_project


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "examples" / "legacy" / "EST-12735185-CRYOSTAR_V2.txt"


def test_real_cryostar_irdin_import_preserves_exact_shaft_geometry_and_sketch_entities():
    project = load_irdin_project(FIXTURE)

    assert project.name == "12735185-CRYOSTAR_V2"
    assert project.metadata["source_format"] == "iRdin/VB6 INI"

    model = project.model
    # B15 inserts exact FE stations at the two imported bearing locations.
    # The 16 historical shaft sections remain preserved in sketch metadata.
    assert len(model.nodes) == 19
    assert len(model.shafts) == 18
    assert model.nodes[-1].z_m == pytest.approx(2.58555)
    assert model.shafts[0].outer_diameter_m == pytest.approx(0.06985)
    outside = [
        getattr(shaft, "outer_diameter_m", getattr(shaft, "outer_diameter_1_m", None))
        for shaft in model.shafts
    ]
    assert any(value == pytest.approx(0.175) for value in outside)
    assert any(value == pytest.approx(0.170) for value in outside)
    assert model.shafts[-1].outer_diameter_m == pytest.approx(0.065)
    assert [model.nodes[b.node - 1].z_m for b in model.advanced_bearings] == pytest.approx(
        [0.36105, 2.2811]
    )

    legacy = project.metadata["legacy_irdin"]
    assert legacy["reference"] == "EST"
    assert legacy["line"] == "HGF"
    assert legacy["frame"] == "400"
    assert legacy["poles"] == 2
    assert legacy["frequency_hz"] == pytest.approx(60.0)
    assert legacy["nominal_rpm"] == pytest.approx(3600.0)
    assert legacy["young_pa"] == pytest.approx(207e9)
    assert legacy["density_kg_m3"] == pytest.approx(7850.0)

    sketch = project.metadata["sketch"]
    assert sketch["shaft_length_mm"] == pytest.approx(2585.55)
    assert len(sketch["sections"]) == 16
    assert len(sketch["masses"]) == 3
    assert sketch["masses"][0]["xi_mm"] == pytest.approx(882.05)
    assert sketch["masses"][0]["length_mm"] == pytest.approx(900.0)
    assert sketch["masses"][0]["mass_kg"] == pytest.approx(647.699)
    assert sketch["masses"][0]["outer_diameter_mm"] == pytest.approx(450.0)
    assert sketch["masses"][0]["package"] is True
    assert sketch["masses"][0]["ump"] is True

    assert len(sketch["bearings"]) == 2
    assert [b["position_mm"] for b in sketch["bearings"]] == pytest.approx([361.05, 2281.1])
    assert all(len(b["table"]) == 8 for b in sketch["bearings"])
    assert sketch["bearings"][0]["table"][0]["rpm"] == pytest.approx(1000.0)
    assert sketch["bearings"][0]["table"][-1]["rpm"] == pytest.approx(4500.0)

    assert len(sketch["unbalance"]) == 2
    assert [u["position_mm"] for u in sketch["unbalance"]] == pytest.approx([882.05, 1782.05])
    assert len(sketch["probes"]) == 4
    assert [p["position_mm"] for p in sketch["probes"]] == pytest.approx(
        [253.4, 253.4, 2389.5, 2389.5]
    )
    assert [p["coordinate"] for p in sketch["probes"]] == [1, 2, 1, 2]
    assert all(p["orientation_deg"] == pytest.approx(45.0) for p in sketch["probes"])


def test_real_cryostar_import_maps_bearing_tables_but_preserves_other_blockers():
    project = load_irdin_project(FIXTURE)
    readiness = project.metadata["numerical_readiness"]
    assert readiness["status"] == "BLOCKED_FOR_NUMERICAL_ANALYSIS"
    assert readiness["exact_shaft_geometry"] is True
    assert readiness["mapped_inline_bearing_tables"] == 2
    codes = {item["code"] for item in readiness["blockers"]}
    assert "IRDIN_BEARING_COEFFICIENT_TABLE_UNMAPPED" not in codes
    assert "IRDIN_DISTRIBUTED_MASS_UNMAPPED" in codes
    assert any("mass/package" in reason for reason in readiness["reasons"])
    assert len(project.model.advanced_bearings) == 2

    case = AnalysisCase("modal", {"speed_rad_s": 0.0}, "Must Not Run")
    with pytest.raises(ValueError, match="BLOCKED_FOR_NUMERICAL_ANALYSIS"):
        AnalysisService().execute(project, case)


def test_real_cryostar_import_can_be_saved_as_rds_and_reopened_without_losing_sketch(tmp_path):
    project = load_irdin_project(FIXTURE)
    target = tmp_path / "cryostar_imported.rds"
    save_project(project, target)
    reopened = load_project(target)

    assert reopened.name == project.name
    assert reopened.model.model_hash() == project.model.model_hash()
    assert reopened.metadata["source_format"] == "iRdin/VB6 INI"
    assert reopened.metadata["numerical_readiness"]["status"] == "BLOCKED_FOR_NUMERICAL_ANALYSIS"
    assert len(reopened.metadata["sketch"]["sections"]) == 16
    assert len(reopened.metadata["sketch"]["masses"]) == 3
    assert len(reopened.metadata["sketch"]["bearings"]) == 2
    assert len(reopened.model.advanced_bearings) == 2
    assert reopened.model.advanced_bearings == project.model.advanced_bearings
