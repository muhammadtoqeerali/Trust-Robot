"""Verify archived L17-L23 code, evidence and upstream provenance."""

import ast
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent

previous = (
    root.parent
    / "isaacsim_v16_l10_l16_target_recovery_v1"
)

def sha(path):
    assert path.is_file() and not path.is_symlink(), path
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text())

manifest = load(root / "checkpoint_manifest_v1.json")

assert manifest["schema"] == (
    "TRUST_ROBOT_KIOS_L17_L23_AMBIGUITY_ROBUSTNESS_CHECKPOINT_V1"
)

assert manifest["parent_commit"] == (
    "cd8ce09f169d1942eb44c28e460be4d78a3fcf77"
)

assert len(manifest["files_sha256"]) == 14
assert len(manifest["phases"]) == 7

for relative, digest in manifest["files_sha256"].items():
    path = Path(relative)

    assert not path.is_absolute()
    assert ".." not in path.parts
    assert sha(root / path) == digest

    if path.suffix == ".py":
        ast.parse((root / path).read_text())

reports = {}
sources = {}
report_hashes = {}

for phase in range(17, 24):
    entry = manifest["phases"][str(phase)]

    source = root / entry["source"]
    evidence = root / entry["report"]

    r = load(evidence)

    assert r["implementation_sha256"] == sha(source)
    assert r["pose_factors_authorized"] == 0

    reports[phase] = r
    sources[phase] = sha(source)
    report_hashes[phase] = sha(evidence)

assert sources[21] == (
    "fac8fd0945145efdc781484b5a6918725dc5b866ce414183a8b8b68a9e725391"
)

assert sources[22] == (
    "5cfe8e389ef3aba3cc1da06a77f8eaefad1964da90c9652029f83d02f1ce1feb"
)

l15path = (
    previous
    / "evidence/l15_restored_final_scan_registration_v1.json"
)

l16path = (
    previous
    / "evidence/l16_six_scan_trajectory_diagnostic_v1.json"
)

l15sha = sha(l15path)
l16sha = sha(l16path)

assert manifest["upstream_l15_sha256"] == l15sha
assert manifest["upstream_l16_sha256"] == l16sha

assert reports[17]["upstream_l15_sha256"] == l15sha
assert reports[17]["upstream_l16_sha256"] == l16sha

assert reports[18]["upstream_l15_sha256"] == l15sha
assert reports[18]["upstream_l16_sha256"] == l16sha
assert reports[18]["upstream_l17_sha256"] == report_hashes[17]

assert reports[19]["l15_report_sha256"] == l15sha
assert reports[19]["l16_report_sha256"] == l16sha
assert reports[19]["l18_report_sha256"] == report_hashes[18]

baseline = {
    "l15": l15sha,
    "l16": l16sha,
    **{
        f"l{phase}": digest
        for phase, digest in report_hashes.items()
    },
}

for name in ("l15", "l16", "l17", "l18", "l19"):
    assert reports[20]["upstream_sha256"][name] == baseline[name]

for phase in range(15, 21):
    name = f"l{phase}"
    assert reports[21]["upstream_report_sha256"][name] == baseline[name]

assert reports[21]["l20_rule_source_sha256"] == sources[20]

for phase in range(15, 22):
    name = f"l{phase}"
    assert reports[22]["upstream_report_sha256"][name] == baseline[name]

for phase in range(17, 21):
    assert reports[22]["reused_implementation_sha256"][f"l{phase}"] == (
        sources[phase]
    )

for phase in (15, 19, 20, 22):
    assert reports[23]["upstream_sha256"][f"l{phase}"] == (
        baseline[f"l{phase}"]
    )

for phase in (17, 18, 19, 20, 22):
    assert reports[23]["reused_source_sha256"][f"l{phase}"] == (
        sources[phase]
    )

assert len(reports[17]["pair_cases"]) == 10
assert len(reports[18]["pair_cases"]) == 10
assert len(reports[19]["pair_diagnostics"]) == 15
assert len(reports[20]["pair_screens"]) == 10

decisions = [
    x["screen"]["decision"]
    for x in reports[20]["pair_screens"]
]

assert decisions.count("STRUCTURAL_REVIEW") == 3
assert decisions.count("SENSITIVITY_REVIEW") == 3
assert decisions.count("NOT_FLAGGED_DIAGNOSTIC_ONLY") == 4

assert reports[21]["numeric_and_duplicate_boundary_probes"] == 23
assert reports[21]["observed_pair_adverse_metric_mutations"] == 80
assert reports[21]["in_memory_evidence_tampering_rejected"] == 6

assert reports[22]["total_trials"] == 60
assert reports[22]["fully_recomputed"] == 60
assert reports[22]["not_evaluable"] == 0

assert reports[23]["scenario_count"] == 11
assert reports[23]["total_pair_trials"] == 110
assert reports[23]["recomputed_pairs"] == 110
assert reports[23]["not_evaluable_pairs"] == 0
assert reports[23]["decision_changes"] == 5

assert reports[23][
    "point_permutation_control_decision_changes"
] == 0

assert reports[23][
    "stale_mapping_decision_changes"
] == 1

assert reports[23]["two_derivations_identical"] is True

assert reports[23]["original_recordings_modified"] is False
assert reports[23]["health_labels_generated"] == 0

assert manifest["raw_recordings_published"] is False
assert manifest["frozen_frontend_modified"] is False
assert manifest["independent_ground_truth_verified"] is False
assert manifest["sensor_exposure_sync_verified"] is False
assert manifest["screen_thresholds_calibrated"] is False
assert manifest["sensor_failure_detection_validated"] is False

assert manifest["health_labels_generated"] == 0
assert manifest["pose_factors_authorized"] == 0

print("L17_L23_CHECKPOINT_INTEGRITY=PASS")
print("L17_L23_FULL_PROVENANCE_CHAIN=PASS")
print("L23_STRESS_RESULTS=VERIFIED")
print("SCIENTIFIC_POSE_FACTORS=0")
