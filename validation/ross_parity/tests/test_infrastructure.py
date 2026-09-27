"""Infrastructure tests; synthetic IO data is never promoted as a ROSS golden."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from infrastructure import (PIN, compare, json_bytes, verify_checkout, verify_import,
                            verified_bundle, write_new_json)


class ComparisonTests(unittest.TestCase):
    def test_relative_and_absolute_tolerance(self):
        self.assertLess(compare([1.0, 0.0], [1.000001, 1e-12], rtol=2e-6, atol=1e-12), 2e-6)

    def test_shape_mismatch_no_broadcast(self):
        with self.assertRaises(AssertionError):
            compare([[1, 2]], [1, 2], rtol=0, atol=0)

    def test_missing_key(self):
        with self.assertRaises(AssertionError):
            compare({"x": 1}, {"y": 1}, rtol=0, atol=0)

    def test_nonfinite_never_passes(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(AssertionError):
                compare(value, value, rtol=1, atol=1)

    def test_wrong_sign_fails(self):
        with self.assertRaises(AssertionError):
            compare(7, -7, rtol=1e-8, atol=1e-12)

    def test_bool_is_not_number(self):
        with self.assertRaises(AssertionError):
            compare(1, True, rtol=0, atol=0)

    def test_invalid_tolerances(self):
        for tolerance in (-1, float("inf"), float("nan")):
            with self.subTest(tolerance=tolerance), self.assertRaises(ValueError):
                compare(1, 1, rtol=tolerance, atol=0)

    def test_canonical_json(self):
        self.assertEqual(json_bytes({"b": 2, "a": 1}), json_bytes({"a": 1, "b": 2}))
        with self.assertRaises(ValueError):
            json_bytes({"x": float("nan")})

    def test_write_never_replaces_golden(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "case.json"
            digest = write_new_json(path, {"a": 1})
            with self.assertRaises(FileExistsError):
                write_new_json(path, {"a": 2})
            self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_import_must_come_from_authority(self):
        root = Path("_ross_ref").resolve()
        verify_import(root, SimpleNamespace(__file__=str(root / "ross/__init__.py")))
        with self.assertRaises(ValueError):
            verify_import(root, SimpleNamespace(__file__="/unrelated/ross/__init__.py"))

    def test_checksum_tampering_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            digest = write_new_json(root / "case.json", {"number": 7})
            write_new_json(root / "authority.json", {
                "commit": PIN["commit"], "repository": PIN["repository"],
                "producer": "ROSS_ONLY", "cases": {"case.json": digest}})
            self.assertEqual(verified_bundle(root)["case.json"]["number"], 7)
            (root / "case.json").write_text('{"number":8}')
            with self.assertRaises(ValueError):
                verified_bundle(root)

    def test_reference_path_escape_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write_new_json(root / "authority.json", {
                "commit": PIN["commit"], "repository": PIN["repository"],
                "producer": "ROSS_ONLY", "cases": {"../case.json": "untrusted"}})
            with self.assertRaises(ValueError):
                verified_bundle(root)


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run_git("init", "-q")
        (self.root / "source.txt").write_text("sentinel\n")
        self.run_git("add", "source.txt")
        self.run_git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture")
        self.sha = self.run_git("rev-parse", "HEAD")

    def run_git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True).strip()

    def test_wrong_commit_fails(self):
        with self.assertRaisesRegex(ValueError, "received"):
            verify_checkout(self.root)

    def test_clean_source_hash_and_dirty_rejection(self):
        with patch.dict(PIN, {"commit": self.sha, "source_files": ["source.txt"]}):
            self.assertEqual(verify_checkout(self.root)["source_sha256"]["source.txt"],
                             hashlib.sha256(b"sentinel\n").hexdigest())
            (self.root / "source.txt").write_text("modified\n")
            with self.assertRaisesRegex(ValueError, "dirty"):
                verify_checkout(self.root)

    def test_untracked_source_rejected(self):
        with patch.dict(PIN, {"commit": self.sha, "source_files": ["source.txt"]}):
            (self.root / "injected.py").write_text("pass")
            with self.assertRaisesRegex(ValueError, "dirty"):
                verify_checkout(self.root)

    def test_subdirectory_rejected(self):
        (self.root / "sub").mkdir()
        with self.assertRaisesRegex(ValueError, "repository root"):
            verify_checkout(self.root / "sub")


if __name__ == "__main__":
    unittest.main()
