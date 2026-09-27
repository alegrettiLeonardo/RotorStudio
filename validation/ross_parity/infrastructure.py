"""Authority/integrity checks and deterministic data IO, with no rotor physics."""
from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path

PIN = json.loads(Path(__file__).with_name("authority.json").read_text(encoding="utf-8"))


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def verify_checkout(root: Path) -> dict:
    root = root.resolve(strict=True)
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise ValueError("ROSS root must be the repository root")
    actual = git(root, "rev-parse", "HEAD")
    if actual != PIN["commit"]:
        raise ValueError(f"ROSS commit: received {actual}; expected {PIN['commit']}")
    if git(root, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("ROSS authority checkout is dirty; use a clean pinned checkout")
    return {
        "repository": PIN["repository"],
        "commit": actual,
        "tree": git(root, "rev-parse", "HEAD^{tree}"),
        "source_sha256": {
            p: hashlib.sha256((root / p).read_bytes()).hexdigest()
            for p in PIN["source_files"]
        },
    }


def verify_import(root: Path, module) -> None:
    expected = root.resolve() / "ross" / "__init__.py"
    received = Path(module.__file__).resolve()
    if received != expected:
        raise ValueError(f"ROSS import: received {received}; expected {expected}")


def json_bytes(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def write_new_json(path: Path, value) -> str:
    data = json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
    return hashlib.sha256(data).hexdigest()


def compare(reference, actual, *, rtol: float, atol: float, path="root") -> float:
    """Strict shape/schema/finite checks; never broadcasts or accepts NaN equality."""
    if not math.isfinite(rtol) or not math.isfinite(atol) or min(rtol, atol) < 0:
        raise ValueError("tolerances must be finite and nonnegative")
    if isinstance(reference, dict):
        if not isinstance(actual, dict) or reference.keys() != actual.keys():
            raise AssertionError(f"{path}: dictionary schema mismatch")
        return max((compare(v, actual[k], rtol=rtol, atol=atol, path=f"{path}.{k}")
                    for k, v in reference.items()), default=0.0)
    if isinstance(reference, list):
        if not isinstance(actual, list) or len(reference) != len(actual):
            raise AssertionError(f"{path}: array shape mismatch")
        return max((compare(a, b, rtol=rtol, atol=atol, path=f"{path}[{i}]")
                    for i, (a, b) in enumerate(zip(reference, actual))), default=0.0)
    if isinstance(reference, (float, int)) and not isinstance(reference, bool):
        if not isinstance(actual, (float, int)) or isinstance(actual, bool):
            raise AssertionError(f"{path}: numeric type mismatch")
        if not math.isfinite(reference) or not math.isfinite(actual):
            raise AssertionError(f"{path}: nonfinite value")
        error = abs(reference - actual)
        limit = atol + rtol * abs(reference)
        if error > limit:
            raise AssertionError(f"{path}: error {error} exceeds {limit}")
        return error
    if type(reference) is not type(actual) or reference != actual:
        raise AssertionError(f"{path}: metadata mismatch")
    return 0.0


def verified_bundle(root: Path) -> dict:
    manifest = json.loads((root / "authority.json").read_text(encoding="utf-8"))
    if manifest["commit"] != PIN["commit"] or manifest["repository"] != PIN["repository"]:
        raise ValueError("Reference bundle authority mismatch")
    if manifest.get("producer") != "ROSS_ONLY" or not manifest.get("cases"):
        raise ValueError("Missing ROSS reference provenance or cases")
    result = {}
    for name, digest in manifest["cases"].items():
        path = root / name
        if path.resolve().parent != root.resolve() or path.suffix != ".json":
            raise ValueError("Reference path must be a direct JSON child")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Reference checksum mismatch: {name}")
        result[name] = json.loads(data)
    return result
