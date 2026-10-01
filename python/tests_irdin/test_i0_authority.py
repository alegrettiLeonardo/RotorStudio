from __future__ import annotations

import json

from drm_core import load_irdin_project, load_project, save_project
from validation.irdin.i0_authority import (
    AUTHORITY_DIR,
    CASE_PATH,
    EXPECTED_SOURCE_SHA256,
    generated_documents,
    normalized_raw_document,
    parse_source,
    verify_authority,
)


def test_i0_frozen_st41_authority_is_complete_and_regenerates_exactly():
    summary = verify_authority()
    assert summary["status"] == "PASS"
    assert summary["source_sha256"] == EXPECTED_SOURCE_SHA256
    assert summary["records"] == 171
    assert summary["assignments"] == 161
    assert summary["field_inventory"] == 161

    inventory = json.loads((AUTHORITY_DIR / "field_inventory.json").read_text(encoding="utf-8"))
    lines = [item["line"] for item in inventory["fields"]]
    assert len(lines) == len(set(lines)) == 161
    assert set(inventory["status_counts"]) <= {"MAPPED", "PRESERVED_ONLY", "UNKNOWN"}


def test_i0_import_preserves_every_raw_assignment_without_unlocking_physics():
    raw = CASE_PATH.read_bytes()
    parsed = parse_source(raw)
    expected_raw = normalized_raw_document(parsed)

    project = load_irdin_project(CASE_PATH)
    assert project.metadata["source_sha256"] == EXPECTED_SOURCE_SHA256
    assert project.metadata["source_size_bytes"] == len(raw)
    assert project.metadata["legacy_irdin_raw"] == expected_raw
    assert sum(len(values) for values in project.metadata["legacy_irdin_raw"].values()) == 161

    readiness = project.metadata["numerical_readiness"]
    assert readiness["status"] == "LEGACY_NUMERIC_READY"
    assert readiness["blockers"] == []
    assert readiness["components"]["mass_native_materialization"] == "PASS_I7_DISK_MATERIALIZATION"
    assert readiness["components"]["support_native_assembly"] == "PASS_I8_GLOBAL_MATRICES"
    assert readiness["components"]["expanded_solver"] == "PASS_I9_NATIVE_MODAL_RESPONSE"
    assert readiness["components"]["automatic_cases"] == "PASS_I10_LEGACY_CASES"
    assert [case.kind for case in project.analyses] == [
        "irdin_modal_sweep",
        "irdin_synchronous_response",
    ]


def test_i0_import_raw_metadata_survives_project_save_reopen(tmp_path):
    project = load_irdin_project(CASE_PATH)
    target = tmp_path / "st41-i0.rds"
    save_project(project, target)
    reopened = load_project(target)

    for key in ("source_sha256", "source_size_bytes", "legacy_irdin_raw"):
        assert reopened.metadata[key] == project.metadata[key]
    assert reopened.metadata["numerical_readiness"] == project.metadata["numerical_readiness"]


def test_i0_committed_authority_documents_match_source_bytes():
    expected = generated_documents(CASE_PATH.read_bytes())
    for filename, payload in expected.items():
        committed = json.loads((AUTHORITY_DIR / filename).read_text(encoding="utf-8"))
        assert committed == payload
