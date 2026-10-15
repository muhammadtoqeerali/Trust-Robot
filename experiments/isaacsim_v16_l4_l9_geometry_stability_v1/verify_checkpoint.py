"""Offline integrity verifier for TRUST-ROBOT L4-L9 checkpoint."""

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent

manifest = json.loads(
    (root / "checkpoint_manifest_v1.json").read_text()
)

assert manifest["schema"] == (
    "TRUST_ROBOT_KIOS_V16_L4_L9_GEOMETRY_STABILITY_CHECKPOINT_V1"
)
assert manifest["qualified_pose_factors"] == 0
assert manifest["independent_ground_truth_verified"] is False
assert manifest["cross_sensor_synchronization_verified"] is False
assert manifest["raw_recordings_published"] is False
assert manifest["simulator_executed_by_publisher"] is False

files = manifest["files_sha256"]
assert len(files) == 15

for name, expected in files.items():
    path = root / name

    assert path.is_file() and not path.is_symlink()

    actual = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

    assert actual == expected, name

expected_inventory = "".join(
    f"{value}  {name}\n"
    for name, value in sorted(files.items())
)

assert (
    root / "SHA256SUMS.txt"
).read_text() == expected_inventory

def load(filename):
    return json.loads(
        (root / "evidence" / filename).read_text()
    )

l5 = load("l5_candidate_preparation_receipt_v1.json")
l6 = load("l6_sparse_aware_geometry_comparison_v1.json")
l7 = load("l7_registration_comparison_v1.json")
l8 = load("l8_multipattern_registration_report_v1.json")
l9 = load("l9_bidirectional_skip_pair_report_v1.json")

assert l5["candidate_scene_sha256"] == (
    files["scene/l5_permuted_beam_scene.usda"]
)
assert l5["candidate_script_sha256"] == (
    files["code/l5_permuted_beam_acquisition.py"]
)
assert l5["candidate_runner_sha256"] == (
    files["code/l5_prepared_isolated_launcher.sh"]
)

assert l6["actual_lidar_point_counts"] == [
    16,16,16,16,16,2
]

assert l6["l5_preparation_receipt_sha256"] == (
    files["evidence/l5_candidate_preparation_receipt_v1.json"]
)
assert l7["l6_evidence_sha256"] == (
    files["evidence/l6_sparse_aware_geometry_comparison_v1.json"]
)
assert l8["source_l7_sha256"] == (
    files["evidence/l7_registration_comparison_v1.json"]
)
assert l9["l8_sha256"] == (
    files["evidence/l8_multipattern_registration_report_v1.json"]
)

assert l8[
    "total_perturbation_registrations_per_derivation"
] == 192

assert l9["bidirectional_pair_attempts"] == 8
assert l9["two_step_direct_attempts"] == 6

assert all(
    count == 0
    for count in (
        l6["pose_factors_authorized"],
        l7["scientifically_qualified_pose_factors"],
        l8["pose_factors_authorized"],
        l9["pose_factors_authorized"],
    )
)

assert l9["independent_reference_verified"] is False
assert l9["scientific_accuracy_scored"] is False

print("COMPACT_CHECKPOINT_INTEGRITY=PASS")
print("L4_L9_EVIDENCE_CHAIN=PASS")
print("POSE_FACTORS_AUTHORIZED=0")
