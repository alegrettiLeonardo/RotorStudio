"""Post-publication immutable-reference guards, separate from native B1.

Pin the entire first-freeze inventory and its Git commit. Candidate files may
have different serialization bytes within policy; frozen files may not change.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from validation.b1.authority_common import (
    BASE_MAIN, FROZEN_PATH, INPUT_PATH, REPO_ROOT, START_HEAD,
    file_hash, git, read_json, require, write_json,
)
from validation.ross_parity.verify_6dof_elements_candidate import (
    snapshot, verify, verify_frozen_integrity,
)

FREEZE_COMMIT = "a9a9b529f09958a2795b628535549a78d575dbd9"
INVENTORY_SHA256 = "86e80775aab32b904ba48a7d7ba64954a3cfabad79cf835e808bf49077ffe847"


def locked_integrity(root: Path):
    require(file_hash(root / "SHA256SUMS.json") == INVENTORY_SHA256,
            "First-freeze inventory identity changed, including a self-consistent rewrite")
    return verify_frozen_integrity(root)


@pytest.fixture
def frozen():
    root = REPO_ROOT / FROZEN_PATH
    assert root.is_dir(), "The final authority gate requires committed goldens; do not skip this test"
    return root


def test_first_freeze_inventory_and_complete_integrity(frozen):
    result = locked_integrity(frozen)
    assert result["status"] == "PASS"
    assert result["frozen_file_count"] == 194
    assert result["sha256sums_sha256"] == INVENTORY_SHA256


def test_every_frozen_file_matches_first_publication_commit(frozen):
    assert not git(REPO_ROOT, "diff", FREEZE_COMMIT, "HEAD", "--", FROZEN_PATH).strip()
    assert not git(REPO_ROOT, "diff", "HEAD", "--", FROZEN_PATH).strip()


def test_physical_inputs_and_production_paths_remain_unchanged(frozen):
    assert (REPO_ROOT / INPUT_PATH).read_bytes() == git(REPO_ROOT, "show", f"{START_HEAD}:{INPUT_PATH}")
    from validation.b1.native_preservation import verify
    verify(REPO_ROOT)


@pytest.mark.parametrize("mutation", ["matrix", "missing", "tolerance", "extra", "provenance"])
def test_corrupt_frozen_copy_is_rejected(frozen, tmp_path, mutation):
    target = tmp_path / "frozen-copy"
    shutil.copytree(frozen, target)
    if mutation == "matrix":
        path = target / "arrays/S02_Kst.npy"
        data = bytearray(path.read_bytes()); data[-1] ^= 1; path.write_bytes(data)
    elif mutation == "missing": (target / "arrays/D01_G.npy").unlink()
    elif mutation == "tolerance": (target / "tolerances.json").write_text("{}", encoding="utf-8")
    elif mutation == "extra": (target / "unreviewed.txt").write_text("unexpected", encoding="utf-8")
    elif mutation == "provenance": (target / "authority.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError): locked_integrity(target)


def test_recomputed_checksum_inventory_cannot_rewrite_initial_evidence(frozen, tmp_path):
    target = tmp_path / "frozen-copy"
    shutil.copytree(frozen, target)
    path = target / "initial_reproduction/initial-cross-platform.json"
    data = read_json(path); data["reference_platform"] = "unreviewed replacement"
    write_json(path, data)
    sums = read_json(target / "SHA256SUMS.json")
    sums["files"]["initial_reproduction/initial-cross-platform.json"] = file_hash(path)
    write_json(target / "SHA256SUMS.json", sums)
    with pytest.raises(ValueError, match="First-freeze inventory identity changed"):
        locked_integrity(target)


def test_fresh_candidate_reproduces_committed_authority_without_writing(frozen, tmp_path):
    value = os.environ.get("B1_CANDIDATE")
    assert value, "Actually executed B1_CANDIDATE is required"
    candidate = Path(value).resolve()
    before_reference, before_candidate = snapshot(frozen), snapshot(candidate)
    result = verify(frozen, candidate, tmp_path / "read-only-reproduction.json")
    assert result["status"] == "PASS"
    assert result["mode"] == "IMMUTABLE_AUTHORITY_REPRODUCTION"
    assert result["primary_matrices_compared"] == 113
    assert result["lateral_selections_compared"] == 63
    assert result["reference_unchanged"]
    assert snapshot(frozen) == before_reference and snapshot(candidate) == before_candidate


def test_one_time_freezer_cannot_overwrite_published_authority(frozen, tmp_path, monkeypatch):
    from validation.b1.freeze_reviewed_authority import freeze
    monkeypatch.delenv("GH_TOKEN", raising=False)
    before = snapshot(frozen)
    destination = tmp_path / "must-not-be-created"
    with pytest.raises(ValueError, match="Immutable authority already exists"):
        freeze(destination)
    assert not destination.exists() and snapshot(frozen) == before


def test_generator_cannot_target_immutable_reference(frozen, tmp_path):
    from validation.ross_parity.generate_6dof_elements_reference import generate
    before = snapshot(frozen)
    with pytest.raises(ValueError, match="Generator cannot target immutable authority"):
        generate(tmp_path / "unused-ross-root", frozen, REPO_ROOT / INPUT_PATH)
    assert snapshot(frozen) == before


def test_initial_publication_workflow_has_been_retired(frozen):
    assert not (REPO_ROOT / ".github/workflows/b1-6dof-initial-freeze.yml").exists()
    text = (REPO_ROOT / ".github/workflows/b1-6dof-authority.yml").read_text(encoding="utf-8")
    assert "contents: write" not in text
    assert "git push" not in text and "git commit" not in text
