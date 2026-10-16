"""Independent L41 report verifier; compares to versioned evidence."""

import argparse
import hashlib
import json
from pathlib import Path

BASE = "8d5a1701df3e9d755ac0a4b5adda2845873f52eb"
EXPECTED_STATUS = {
    "archived_checkpoint_integrity": "PASS_ARCHIVED",
    "offline_preflight_contract": "PROTOTYPE_ONLY",
    "pre_simulator_hook_position": "PROTOTYPE_ONLY",
    "post_export_seal_hook_position": "PROTOTYPE_ONLY",
    "single_host_nonce_consumption": "PROTOTYPE_ONLY",
    "transactional_receipt_outbox": "PROTOTYPE_ONLY",
    "incomplete_session_quarantine": "PROTOTYPE_ONLY",
    "guarded_live_gpu_launch_authorization": "BLOCKED",
    "candidate_scene_and_metadata_staging": "BLOCKED",
    "capture_hook_to_persistent_outbox": "BLOCKED",
    "per_sensor_acquisition_session_binding": "BLOCKED",
    "independent_immutable_witness_storage": "BLOCKED",
    "independent_sensor_source_authenticity": "NOT_QUALIFIED",
    "hardware_backed_attestation": "NOT_QUALIFIED",
    "power_loss_durability": "NOT_QUALIFIED",
    "multi_host_replay_protection": "NOT_QUALIFIED",
    "physical_exposure_clock_synchronization": "NOT_QUALIFIED",
    "sensor_intrinsic_extrinsic_calibration": "NOT_QUALIFIED",
    "independent_six_dof_reference": "NOT_QUALIFIED",
    "heldout_scientific_pose_health_evaluation": "NOT_QUALIFIED",
}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def sha(path):
    p = Path(path)
    need(p.is_file() and not p.is_symlink(), "Missing/symlink " + str(p))
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(args):
    archive = Path(args.archive)
    report_path = Path(args.report)
    output = Path(args.validation)
    need(not output.exists(), "Validation output exists")
    r = json.loads(report_path.read_text())
    manifest = json.loads((archive / "checkpoint_manifest_v1.json").read_text())
    need(r["schema"] == "TRUST_ROBOT_L41_ACQUISITION_WITNESS_READINESS_V1", "Schema")
    need(r["parent_commit"] == BASE, "Commit")
    need(r["assessment_source_sha256"] == sha(args.assessor), "Source hash")
    need(r["checkpoint_manifest_sha256"] == sha(archive / "checkpoint_manifest_v1.json"), "Archive manifest")
    need(r["l33_contract_sha256"] == sha(args.l33_contract), "L33 contract")
    need(r["l33_contract_sha256"] == "24e71f94c8acfc3aa59184c49a811d62f54fc93d90178bbebef6c8239912467b", "L33 pin")
    need(set(r["files_sha256"]) == set((
        "evidence/l36_falsification_report.json", "evidence/l37_integration_plan.json",
        "evidence/l37_validation.json", "evidence/l38_validation.json",
        "evidence/l39_recovery_matrix.json", "evidence/l40_outbox_validation.json",
        "evidence/l40_registry_snapshot.json", "code/l37_nonexecuted_candidate.py", "code/l37_runtime_guard.py"
    )), "Source coverage")
    for name, digest in r["files_sha256"].items():
        need(digest == manifest["files_sha256"][name] == sha(archive / name), "Evidence digest " + name)
    observed = {g["id"]: g["status"] for g in r["gates"]}
    need(len(r["gates"]) == len(EXPECTED_STATUS) == 20 and observed == EXPECTED_STATUS, "Gate status count/content")
    need(all(len(g["justification"]) >= 15 for g in r["gates"]), "Gate explanation")
    need(r["technical_test_counts"] == {"l36_adversarial_controls": 46, "l37_static_mutations": 12, "l38_adversarial_controls": 20, "l39_crash_matrix_cases": 20, "l40_recovery_windows": 2, "l40_rejected_faults": 7}, "Evidence counts")
    need([s["stage"] for s in r["acquisition_stages"]] == ["A", "B", "C", "D"], "Scientific stages")
    need(all(s["independently_qualified"] is False for s in r["acquisition_stages"]), "Unqualified scientific stage")
    need(r["claim_flags"] and all(v is False for v in r["claim_flags"].values()), "Scientific claim")
    need(len(r["claim_flags"]) == 10, "Claim coverage")
    need(r["scientific_pose_factors"] == r["health_labels"] == r["new_sensor_measurements"] == 0, "Scientific gate")
    need(r["readiness_verdict"] == "LIVE_CAPTURE_DENIED_SCIENCE_GATES_CLOSED", "Verdict")
    need([t["order"] for t in r["prioritized_next_steps"]] == [1, 2, 3, 4], "Action order")
    need(r["prioritized_next_steps"][0]["phase"] == "L42", "Next phase")
    need(r["negative_controls_count"] == 26 and len(r["negative_controls_rejected"]) == 26, "Negative controls")
    need(set(r["negative_controls_rejected"]) == {"false_ready_" + key for key in EXPECTED_STATUS} | {
        "replace_parent_commit", "increase_pose_factors", "declare_health_labels", "enable_live_authorization", "promote_independent_reference", "fake_test_count"
    }, "Negative control names")
    need(manifest["pose_factors_authorized"] == 0 and manifest["live_simulator_launch_authorized"] is False, "Manifest authority")
    result = {
        "schema": "TRUST_ROBOT_L41_INDEPENDENT_READINESS_VALIDATION_V1",
        "parent_commit": BASE,
        "assessment_report_sha256": sha(report_path),
        "assessment_source_sha256": sha(args.assessor),
        "verifier_source_sha256": sha(__file__),
        "independently_checked_gates": 20,
        "independently_checked_forgeries": 26,
        "scientific_stages_closed": 4,
        "live_gpu_launch_authorized": False,
        "scientific_pose_factors": 0,
        "health_labels": 0,
        "next": "L42_NONEXECUTED_HOOK_TO_OUTBOX_BINDING_DESIGN",
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("L41_INDEPENDENT_GATE_MATRIX=20_VERIFIED")
    print("L41_INDEPENDENT_NEGATIVE_CONTROLS=26_VERIFIED")
    print("L41_SCIENCE_GATES=4_CLOSED")
    print("L41_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("archive", "l33_contract", "assessor", "report", "validation"):
        p.add_argument("--" + name.replace("_", "-"), required=True)
    main(p.parse_args())
