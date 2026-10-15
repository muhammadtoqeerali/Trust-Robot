"""Verify archived source bytes, evidence chain and scientific restrictions."""

import ast
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent

def sha(path):
    assert path.is_file() and not path.is_symlink(), path
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(relative):
    return json.loads((root / relative).read_text())

m = load("checkpoint_manifest_v1.json")

assert m["schema"] == (
    "TRUST_ROBOT_KIOS_V16_L10_L16_TARGET_RECOVERY_CHECKPOINT_V1"
)

assert m["parent_commit"] == (
    "c8d13cc7f6fe5a5faaa4c828cb4c5c2bc68cad9c"
)

assert len(m["files_sha256"]) == 17

for name, digest in m["files_sha256"].items():
    relative = Path(name)

    assert not relative.is_absolute()
    assert ".." not in relative.parts

    assert sha(root / relative) == digest, name

    if name.endswith(".py"):
        ast.parse((root / relative).read_text())

assert m["pose_factors_authorized"] == 0
assert m["raw_recordings_published"] is False
assert m["independent_ground_truth_verified"] is False
assert m["cross_sensor_synchronization_verified"] is False

l10 = load("evidence/l10_sparse_endpoint_diagnostic_v1.json")
l11 = load("evidence/l11_existing_gmo_sweep_triage_v1.json")
l12 = load("evidence/l12_azimuth_mapping_and_return_timeline_v1.json")
l13 = load("evidence/l13_target_distance_preparation_receipt_v1.json")
l14 = load("evidence/l14_target_distance_comparison_v1.json")
l15 = load("evidence/l15_restored_final_scan_registration_v1.json")
l16 = load("evidence/l16_six_scan_trajectory_diagnostic_v1.json")

assert l10["implementation_sha256"] == sha(
    root / "code/l10_sparse_endpoint.py"
)

assert l11["implementation_sha256"] == sha(
    root / "code/l11_gmo_sweep_triage.py"
)

assert l12["implementation_sha256"] == sha(
    root / "code/l12_angle_mapping.py"
)

assert l11["upstream_l10_sha256"] == sha(
    root / "evidence/l10_sparse_endpoint_diagnostic_v1.json"
)

assert l12["l11_sha256"] == sha(
    root / "evidence/l11_existing_gmo_sweep_triage_v1.json"
)

assert l13["upstream_l12_sha256"] == sha(
    root / "evidence/l12_azimuth_mapping_and_return_timeline_v1.json"
)

assert l13["candidate_scene_sha256"] == sha(
    root / "scene/l13_distance_intervention.usda"
)

assert l13["candidate_source_sha256"] == sha(
    root / "code/l13_target_distance_acquisition.py"
)

assert l13["candidate_launcher_sha256"] == sha(
    root / "code/l13_isolated_launcher.sh"
)

assert l13["candidate_verifier_sha256"] == sha(
    root / "code/l13_verify_recording.py"
)

assert l13["candidate_metadata_sha256"] == sha(
    root / "evidence/l13_candidate_metadata_v1.json"
)

assert l14["l13_receipt_sha256"] == sha(
    root / "evidence/l13_target_distance_preparation_receipt_v1.json"
)

assert l14["l12_report_sha256"] == sha(
    root / "evidence/l12_azimuth_mapping_and_return_timeline_v1.json"
)

assert l14["scene_sha256"] == sha(
    root / "scene/l13_distance_intervention.usda"
)

assert l14["acquisition_source_sha256"] == sha(
    root / "code/l13_target_distance_acquisition.py"
)

assert l15["implementation_sha256"] == sha(
    root / "code/l15_restored_registration.py"
)

assert l15["upstream_l14_sha256"] == sha(
    root / "evidence/l14_target_distance_comparison_v1.json"
)

assert l16["implementation_sha256"] == sha(
    root / "code/l16_six_scan_trajectory.py"
)

assert l16["l15_report_sha256"] == sha(
    root / "evidence/l15_restored_final_scan_registration_v1.json"
)

assert l16["l14_report_sha256"] == sha(
    root / "evidence/l14_target_distance_comparison_v1.json"
)

assert l14["shifted_selected_valid_counts"] == [16] * 6
assert l15["deterministic_two_derivations_identical"] is True
assert l16["repeated_derivation_identical"] is True
assert l16["all_pair_attempts_per_derivation"] == 15
assert len(l16["all_pairs"]) == 15

assert sum(
    r["status"] == "DIAGNOSTIC_AVAILABLE"
    for r in l16["all_pairs"]
) == 15

for report in (l10, l11, l12, l13, l14, l15, l16):
    assert report["pose_factors_authorized"] == 0

assert l16["scientific_localization_ate_rpe_computed"] is False
assert l16["kinematic_usd_is_independent_ground_truth"] is False

print("L10_L16_CHECKPOINT_INTEGRITY=PASS")
print("FULL_EVIDENCE_CHAIN=PASS")
print("SCIENTIFIC_POSE_FACTORS=0")
