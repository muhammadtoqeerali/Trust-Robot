"""Standalone strict integrity verifier for archived KIOS L24-L30 evidence."""

import ast
import hashlib
import json
import pathlib
import re

root = pathlib.Path(__file__).resolve().parent
repo = root.parent.parent
manifest_path = root / "checkpoint_manifest_v1.json"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def safe_file(path):
    assert path.is_file() and not path.is_symlink(), path
    assert path.stat().st_nlink == 1, path
    assert path.resolve().is_relative_to(repo.resolve()), path
    assert path.stat().st_size <= 3_000_000, path

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

safe_file(manifest_path)
m = load(manifest_path)

assert m["schema"] == "TRUST_ROBOT_KIOS_L24_L30_CHECKPOINT_V1"
assert m["parent_commit"] == "45b54a9625ea4c834f4009f441973cf93ce0d6b3"
assert m["branch"] == "kios-isaacsim-v15-integration"

files = m["files_sha256"]
assert isinstance(files, dict) and len(files) >= 20

expected_archive = set(files) | {
    "checkpoint_manifest_v1.json",
    "verify_checkpoint.py",
}

actual_archive = {
    p.relative_to(root).as_posix()
    for p in root.rglob("*")
    if p.is_file()
}

assert actual_archive == expected_archive, (
    "Archive file set mismatch",
    sorted(actual_archive ^ expected_archive),
)

for relative, expected in files.items():
    p = pathlib.PurePosixPath(relative)
    assert not p.is_absolute()
    assert ".." not in p.parts
    assert p.parts[0] in ("code", "evidence", "README.md")
    f = root / relative
    safe_file(f)
    assert digest(f) == expected, relative
    if f.suffix == ".py":
        ast.parse(f.read_text(encoding="utf-8"))
    if f.suffix == ".json":
        load(f)
    if f.suffix == ".jsonl":
        rows = [json.loads(line) for line in f.read_text().splitlines()]
        assert all(isinstance(row, dict) for row in rows)

assert set(m["phases"]) == {str(x) for x in range(24, 31)}

for phase in range(24, 30):
    entry = m["phases"][str(phase)]
    source = root / entry["source"]
    report = root / entry["report"]
    assert digest(source) == entry["source_sha256"]
    assert digest(report) == entry["report_sha256"]

assert m["phases"]["30"]["report_sha256"] == (
    "d358563fa3e08523c2aa86fb42e8d39b51bd33ffc5fa1cf87ad348075a1adc67"
)

expected_events = {
    "l28_events": "957e13ec10411631cbeaaeb8759907363bfa0e3200f9f9b46caf49adaf2bc082",
    "l29_dryrun_events": "0683126c2494d1400d94fe63b43ec489847d9d9a6150a5ab314458b0ede2e8cd",
    "l30_events": "b28c333347ebb9c7262b636c355324b9abfa0b03beeb7c1af5a8b473a7144444",
}
for key, sha in expected_events.items():
    relative = m["envelopes"][key]
    f = root / relative
    assert digest(f) == sha
    rows = [json.loads(s) for s in f.read_text().splitlines()]
    assert len(rows) == 272
    assert all(isinstance(x, dict) for x in rows)

assert m["l30_capture_counts"] == {
    "camera": 6,
    "lidar": 6,
    "imu": 130,
    "scripted_usd_pose": 130,
    "total_events": 272,
    "lidar_points": 96,
}

assert m["l30_selected_steps"] == [51, 61, 71, 81, 91, 101]
assert m["l30_negative_controls_passed"] == 6
assert m["l30_runtime_exit_code"] == 0

assert m["upstream_report_sha256"]["l15"] == (
    "da5a45d217d6c27d565acabef8c6c454d7d3f691d5d7dd375c780c0b37f6b1c9"
)
assert m["upstream_report_sha256"]["l16"] == (
    "2a1ebca297ca4d58ab2d2ff0a9aa3104673e12aef9dd6e1f43ce5167617cfdaf"
)

old = repo / "experiments/isaacsim_v16_l17_l23_ambiguity_robustness_v1"
previous = repo / "experiments/isaacsim_v16_l10_l16_target_recovery_v1"

for phase in (19, 20, 23):
    relative = {
        19: "evidence/l19_beam_association_stability_report_v1.json",
        20: "evidence/l20_ambiguity_screen_report_v1.json",
        23: "evidence/l23_structured_stress_diagnostic_v1.json",
    }[phase]
    f = old / relative
    safe_file(f)
    assert digest(f) == m["upstream_report_sha256"][f"l{phase}"]

for phase, filename in (
    (15, "l15_restored_final_scan_registration_v1.json"),
    (16, "l16_six_scan_trajectory_diagnostic_v1.json"),
):
    f = previous / "evidence" / filename
    safe_file(f)
    assert digest(f) == m["upstream_report_sha256"][f"l{phase}"]

for relative, expected in m["documentation_sha256"].items():
    assert relative in (
        "AGENTS.md",
        "docs/TRUST_ROBOT_PROJECT_STATE.md",
        "docs/audits/trust_robot/TRUST_ROBOT_KIOS_L24_L30_MULTIMODAL_EVIDENCE_V1.md",
    )
    f = repo / relative
    safe_file(f)
    assert digest(f) == expected

for flag in (
    "independent_ground_truth_verified",
    "cross_sensor_exposure_sync_verified",
    "physical_sensor_equivalence_verified",
    "calibrated_health_probabilities",
    "factor_uncertainty_qualified",
    "sensor_failure_detection_validated",
    "raw_recordings_published",
    "frozen_frontend_modified",
):
    assert m[flag] is False, flag

assert m["pose_factors_authorized"] == 0
assert m["health_labels_generated"] == 0

for p in root.rglob("*"):
    assert not p.is_symlink()
    if p.is_file():
        safe_file(p)
        assert p.suffix.lower() not in (
            ".npy", ".npz", ".usd", ".usda", ".usdc",
            ".log", ".bin", ".so", ".pt", ".pth",
        )

print("L24_L30_CHECKPOINT_INTEGRITY=PASS")
print("L24_L30_HASH_PINNED_PROVENANCE=PASS")
print("L30_272_EVENT_ARCHIVE=VERIFIED")
print("L30_SCIENTIFIC_RESTRICTIONS=ENFORCED")
print("SCIENTIFIC_POSE_FACTORS=0")
