"""One-time copy of a reviewed CI candidate, never a reference regenerator.

The caller must supply an Actions read token for artifact retrieval. This script
does not push commits. It refuses an existing frozen authority. The temporary
bootstrap workflow may commit only the new authority directory, once.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from validation.b1.authority_common import (
    REPO_ROOT, BASE_MAIN, GENERATOR_PATH, FROZEN_PATH, INPUT_PATH, file_hash,
    check_candidate, git, head, read_json, require, sha256, write_json,
)
from validation.b1.inspect_candidate import inspect_candidate
from validation.ross_parity.verify_6dof_elements_candidate import (
    POLICY_PATH, REVIEW_PATH, INSPECTOR_PATH, snapshot, validate_inspection,
    validate_provenance, verify, verify_frozen_integrity,
)

REPOSITORY = "alegrettiLeonardo/RotorStudio"
BRANCH = "feature/ross-analysis-b1-6dof-element-matrices"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(resource: str, token: str):
    request = urllib.request.Request(f"https://api.github.com/repos/{REPOSITORY}/{resource}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "RotorStudio-B1-authority-freeze"})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=60) as response:
        return json.load(response)


def download_artifact(artifact: dict, review: dict, token: str, target: Path) -> dict:
    require(not target.exists(), "Refuse to overwrite downloaded evidence")
    meta = api(f"actions/artifacts/{artifact['id']}", token)
    require(meta["name"] == artifact["name"] and not meta["expired"], "Wrong/expired reviewed artifact")
    require(meta["digest"] == "sha256:" + artifact["sha256"], "Actions metadata digest mismatch")
    require(meta["workflow_run"]["id"] == review["run_id"] and meta["workflow_run"]["head_sha"] == review["reviewed_head"], "Wrong reviewed artifact run/HEAD")
    url = f"https://api.github.com/repos/{REPOSITORY}/actions/artifacts/{artifact['id']}/zip"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "User-Agent": "RotorStudio-B1-authority-freeze"})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=60) as response:
            data = response.read(20_000_001)
    except urllib.error.HTTPError as error:
        require(error.code == 302, f"Artifact download failed: HTTP {error.code}")
        location = error.headers["Location"]
        require(location.startswith("https://"), "Artifact redirect must use HTTPS")
        # Do not forward the GitHub API credential to blob storage.
        with urllib.request.urlopen(location, timeout=60) as response:
            data = response.read(20_000_001)
    require(len(data) <= 20_000_000, "Unexpectedly large reviewed artifact")
    require(sha256(data) == artifact["sha256"], "Actual reviewed ZIP bytes do not match approved digest")
    archive = zipfile.ZipFile(io.BytesIO(data))
    members = archive.infolist()
    require(len({m.filename for m in members}) == len(members), "Duplicate ZIP entries")
    require(sum(m.file_size for m in members) <= 20_000_000, "Unexpected inflated artifact size")
    target.mkdir(parents=True, exist_ok=False)
    for member in members:
        relative = PurePosixPath(member.filename)
        require(not relative.is_absolute() and ".." not in relative.parts and "\\" not in member.filename, "Unsafe artifact member path")
        require(not stat.S_ISLNK(member.external_attr >> 16), "Artifact symlinks are not accepted")
        path = target.joinpath(*relative.parts)
        require(path.resolve().is_relative_to(target.resolve()), "ZIP entry escaped evidence directory")
        if member.is_dir():
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(member))
    return {"id": artifact["id"], "sha256": sha256(data), "bytes": len(data),
            "run_id": meta["workflow_run"]["id"], "head_sha": meta["workflow_run"]["head_sha"]}


def freeze(download_root: Path) -> None:
    target = REPO_ROOT / FROZEN_PATH
    require(not target.exists(), "Immutable authority already exists; reproduction only, never overwrite")
    review = read_json(REVIEW_PATH)
    require(file_hash(REPO_ROOT / GENERATOR_PATH) == review["source_generator_sha256"], "Reviewed generator changed")
    require(file_hash(INSPECTOR_PATH) == review["source_inspector_sha256"], "Reviewed inspector changed")
    require(file_hash(REPO_ROOT / INPUT_PATH) == review["input_specification_sha256"], "Reviewed inputs changed")
    require(not git(REPO_ROOT, "diff", BASE_MAIN, "HEAD", "--", "fortran", "python", "reference").strip(), "Native/production historical paths changed")
    live_main = git(REPO_ROOT, "ls-remote", "origin", "refs/heads/main").decode().split()[0]
    require(live_main == BASE_MAIN, "Main advanced; revalidate before first freeze")
    live_branch = git(REPO_ROOT, "ls-remote", "origin", f"refs/heads/{BRANCH}").decode().split()[0]
    require(live_branch == head(REPO_ROOT), "Parallel B1 work detected; stop rather than overwrite")
    token = os.environ.get("GH_TOKEN")
    require(bool(token), "GH_TOKEN with Actions read permission is required to retrieve reviewed artifacts")
    run = api(f"actions/runs/{review['run_id']}", token)
    require(run["head_sha"] == review["reviewed_head"] and run["event"] == "push" and run["conclusion"] == "success", "Reviewed run is not successful at expected HEAD")
    jobs = api(f"actions/runs/{review['run_id']}/jobs?filter=latest&per_page=100", token)["jobs"]
    observed_jobs = {j["id"]: j for j in jobs}
    for job_id in review["job_ids"].values():
        require(observed_jobs[job_id]["status"] == "completed" and observed_jobs[job_id]["conclusion"] == "success", "Reviewed job failed")
    artifacts = {}
    for platform in ("linux", "windows"):
        artifacts[platform] = download_artifact(review["artifacts"][platform], review, token, download_root / platform)
        root = download_root / platform / "candidate"
        authority, _, _ = check_candidate(root)
        require(file_hash(root / "authority.json") == review[f"{platform}_authority_sha256"], "Not the reviewed first candidate")
        require(authority["generator_head"] == review["reviewed_head"] and authority["data_bundle_sha256"] == review["reviewed_data_bundle_sha256"], "Reviewed candidate changed")
        validate_provenance(root, authority)
        validate_inspection(root, authority)
    linux, windows = download_root / "linux/candidate", download_root / "windows/candidate"
    report_root = download_root.parent
    cross = verify(linux, windows, report_root / "initial-cross-platform.json", review_only=True)
    require(cross["status"] == "PASS", "Reviewed Linux/Windows numerical comparison failed")
    repeats = {}
    for platform in ("linux", "windows"):
        repeat = download_root / platform / "repeat"
        report = inspect_candidate(repeat)
        require(report["status"] == "PASS", "Second-generation candidate inspection failed")
        repeats[platform] = verify(linux, repeat, report_root / f"initial-{platform}-repeat.json", review_only=True)
        require(repeats[platform]["status"] == "PASS", "Second-generation reproduction failed")
    environment = os.environ.copy(); environment["B1_CANDIDATE"] = str(linux.resolve())
    subprocess.run([sys.executable, "-m", "pytest", "validation/b1/tests", "-q", f"--junitxml={report_root / 'pre-freeze-tests.xml'}"],
                   cwd=REPO_ROOT, env=environment, check=True, timeout=180)
    # Only now materialize the first immutable authority. Every original
    # candidate file, including authority.json, retains its original bytes.
    shutil.copytree(linux, target)
    shutil.copyfile(POLICY_PATH, target / "tolerances.json")
    shutil.copyfile(REVIEW_PATH, target / "FREEZE_REVIEW.json")
    (target / ".gitattributes").write_bytes(b"*.npy -text\n*.json text eol=lf\n*.txt -text\n")
    evidence_dir = target / "initial_reproduction"
    evidence_dir.mkdir()
    for path in report_root.glob("initial-*.json"):
        shutil.copyfile(path, evidence_dir / path.name)
    # Preserve Windows provenance/environment without duplicating its equal arrays.
    for filename in ("authority.json", "requirements-freeze.txt", "pip-check.txt", "inspection.json"):
        shutil.copyfile(windows / filename, evidence_dir / f"windows-{filename}")
    freeze_record = {
        "schema_version": 1, "freeze_utc": datetime.now(timezone.utc).isoformat(),
        "freeze_parent_head": head(REPO_ROOT), "reviewed_generator_head": review["reviewed_head"],
        "review_sha256": file_hash(REVIEW_PATH), "tolerances_sha256": file_hash(POLICY_PATH),
        "source_candidate_authority_sha256": file_hash(linux / "authority.json"),
        "artifacts": artifacts, "candidate_review": "PASS", "cross_platform_numeric_comparison": cross["status"],
        "copy_policy": "Reviewed Linux first candidate copied byte-for-byte; no generator output was substituted during freeze",
        "native_implementation": "NOT_STARTED", "ABI": "NOT_STARTED",
        "freeze_workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
    }
    write_json(target / "FREEZE_RECORD.json", freeze_record)
    write_json(target / "SHA256SUMS.json", {"schema_version": 1, "files": snapshot(target)})
    integrity = verify_frozen_integrity(target)
    final = verify(target, windows, report_root / "frozen-windows-verification.json")
    require(final["status"] == "PASS", "Frozen authority reproduction failed after copy")
    print("B1_FIRST_FREEZE " + json.dumps({"status": "PASS", "freeze_parent_head": head(REPO_ROOT),
          "path": FROZEN_PATH, **integrity, "primary_matrices": 113, "lateral_selections": 63,
          "native_implementation": "NOT_STARTED", "ABI": "NOT_STARTED"}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-root", type=Path, required=True)
    args = parser.parse_args()
    freeze(args.download_root.resolve())


if __name__ == "__main__":
    main()
