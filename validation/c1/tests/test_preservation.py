from __future__ import annotations
from pathlib import Path
import subprocess
import yaml
from validation.c1.preservation import verify

ROOT=Path(__file__).resolve().parents[3]

def test_c1_b3_preservation_gate():
    assert verify()["status"]=="PASS"

def test_c1_authority_workflow_is_post_freeze_read_only():
    path=ROOT/".github/workflows/c1-misalignment-authority.yml"
    text=path.read_text(encoding="utf-8")
    data=yaml.safe_load(text)
    permissions=data.get("permissions",{})
    assert permissions.get("contents")=="read"
    assert "contents: write" not in text
    assert "git push" not in text
    assert "git commit" not in text
    assert "freeze_authority.py" not in text
    assert "persist-credentials: false" in text
    assert "b45bbaa5ec91ca004643142e83f75d0c13f7a8ea" in text

def test_c1_frozen_authority_is_byte_immutable():
    subprocess.run([
        "git","diff","--exit-code","b45bbaa5ec91ca004643142e83f75d0c13f7a8ea","HEAD",
        "--","validation/ross_parity/misalignment"
    ],cwd=ROOT,check=True)
