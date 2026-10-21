#!/usr/bin/env python3
"""R56 checkpoint preparation: exact local receipts, no network or raw data."""

import hashlib
import json
import os
import pathlib
import re
import shutil
import stat
import sys

E = pathlib.Path(sys.argv[1])
A = pathlib.Path(sys.argv[2])
R = pathlib.Path(sys.argv[3])

PHASES = {
    "r51": (
        "trust_robot_r51_clock_evidence_dev_v1",
        "trust_robot_r51_clock_evidence_result_v1",
    ),
    "r52": (
        "trust_robot_r52_clock_sensitivity_dev_v1",
        "trust_robot_r52_clock_sensitivity_result_v1",
    ),
    "r53": (
        "trust_robot_r53_timing_receipt_boundary_dev_v1",
        "trust_robot_r53_timing_receipt_boundary_result_v1",
    ),
    "r54": (
        "trust_robot_r54_author_request_packet_dev_v1",
        "trust_robot_r54_author_request_packet_result_v1",
    ),
    "r55": (
        "trust_robot_r55_gt_source_acquisition_dev_v1",
        "trust_robot_r55_gt_source_acquisition_result_v1",
    ),
    "r55f": (
        "trust_robot_r55f_official_gt_manual_fallback_dev_v1",
        "trust_robot_r55f_official_gt_manual_fallback_result_v1",
    ),
}

EXPECTED = {
    "r51": "852613e76d272ae1fb312e9dee27ee08bf7cf41e81889aed7495763d3b565602",
    "r52": "093b1722e23d8e9db92c2ae6dfb173978fbb56041144d64d53388183dcea5210",
    "r53": "9e2a8b5cf30bad5d67a1776c7bfabafb6f3b7dd1b79a93429e8f34aca8096309",
    "r54": "ac924e0ff77fbe161bc299255802d47fc602da78e9d83bbe0da89d8dd24801d0",
    "r55": "899ed3a8582d6fed4d8d211b99729dc2d0a4b7db75cb5a0855b9600192efb65e",
    "r55f": "22a0ed923ab1057c1bbee38314f4886918dd543e3f43d0bfd0c2c7e27b36bdd8",
}

ALLOWED_SUFFIXES = {".py", ".json", ".md"}

MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 12 * 1024 * 1024

SECRET = re.compile(
    rb"(?i)(authorization\s*:\s*bearer\s+\S+"
    rb"|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    rb"|(?:access_token|refresh_token|client_secret)"
    rb"\s*[=:]\s*['\"]?[A-Za-z0-9._-]{12,})"
)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def safe_directory(path):
    st = path.lstat()
    if not stat.S_ISDIR(st.st_mode):
        raise RuntimeError("Unsafe directory: " + str(path))

def safe_file(path):
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        raise RuntimeError("Unsafe source file: " + str(path))
    if st.st_size > MAX_FILE:
        raise RuntimeError("Artifact exceeds safe cap: " + str(path))
    return st

manifest = {
    "schema": "trust_robot_r51_r55f_checkpoint_manifest_v1",
    "base_commit": "58e23861811e51c5d00f00f5d22e5cb561c4b43a",
    "branch": "kios-isaacsim-v15-integration",
    "frozen_split": "22_train_7_validation_calibration_7_confirmation_test",
    "ground_truth_status": "NOT_ACQUIRED",
    "scientific_gates": "ALL_11_CLOSED",
    "real_pose_factors": "DENIED",
    "health_training": "DENIED",
    "ate_rpe": "DENIED",
    "confirmation_test_accessed": False,
    "raw_bag_opened": False,
    "files": {},
    "phase_file_counts": {},
    "independent_report_sha256": EXPECTED,
}

total = 0
skipped = []

for phase, directories in PHASES.items():
    copied = 0

    for dirname in directories:
        src_dir = E / dirname
        safe_directory(src_dir)

        target_dir = A / "evidence" / dirname
        target_dir.mkdir(parents=True, exist_ok=False)

        for source in sorted(src_dir.iterdir()):
            if source.is_dir() and not source.is_symlink():
                raise RuntimeError(
                    "Unexpected nested source directory: " + str(source)
                )

            safe_file(source)

            if source.suffix.lower() not in ALLOWED_SUFFIXES:
                skipped.append(dirname + "/" + source.name)
                continue

            before = source.stat()
            data = source.read_bytes()
            after = source.stat()

            identity = lambda s: (
                s.st_dev, s.st_ino, s.st_size,
                s.st_mtime_ns, s.st_ctime_ns
            )

            if identity(before) != identity(after):
                raise RuntimeError(
                    "Source changed while reading: " + str(source)
                )

            if len(data) != before.st_size:
                raise RuntimeError("Short source read")

            if len(data) > MAX_FILE:
                raise RuntimeError("File cap exceeded")

            total += len(data)
            if total > MAX_TOTAL:
                raise RuntimeError("Archive byte budget exceeded")

            if b"\x00" in data:
                raise RuntimeError("Binary content refused: " + str(source))

            try:
                data.decode("utf-8")
            except UnicodeDecodeError:
                raise RuntimeError("Non-UTF8 content refused: " + str(source))

            if SECRET.search(data):
                raise RuntimeError(
                    "Possible authentication material: " + str(source)
                )

            target = target_dir / source.name

            with target.open("xb") as f:
                f.write(data)

            if target.read_bytes() != data:
                raise RuntimeError("Archive copy mismatch")

            relative = target.relative_to(A).as_posix()
            manifest["files"][relative] = {
                "sha256": digest(data),
                "bytes": len(data),
                "source": str(source),
            }

            copied += 1

    if copied < 3:
        raise RuntimeError("Insufficient archived evidence: " + phase)

    manifest["phase_file_counts"][phase] = copied

for phase, expected in EXPECTED.items():
    names = [
        name for name in manifest["files"]
        if name.startswith("evidence/")
        and name.split("/")[1].startswith(
            PHASES[phase][1]
        )
        and name.endswith("_independent_validation_v1.json")
    ]

    if len(names) != 1:
        raise RuntimeError(
            "Independent report missing or ambiguous: " + phase
        )

    if manifest["files"][names[0]]["sha256"] != expected:
        raise RuntimeError(
            "Independent report SHA mismatch: " + phase
        )

    report = json.loads((A / names[0]).read_text(encoding="utf-8"))

    if not isinstance(report, dict):
        raise RuntimeError("Invalid report: " + phase)

manifest["skipped_nonwhitelisted_names"] = sorted(skipped)
manifest["archive_source_bytes"] = total

out = A / "manifest.json"

with out.open("x", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, sort_keys=True)
    f.write("\n")

print("R56_ARCHIVED_PHASES=" + str(len(PHASES)))
print("R56_ARCHIVED_FILES=" + str(len(manifest["files"])))
print("R56_ARCHIVED_BYTES=" + str(total))
print("R56_SKIPPED_NONWHITELISTED=" + str(len(skipped)))

for phase, n in sorted(manifest["phase_file_counts"].items()):
    print("R56_PHASE_FILES_" + phase.upper() + "=" + str(n))
