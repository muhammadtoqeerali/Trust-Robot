"""TRUST-ROBOT L41: read-only evidence-derived acquisition readiness audit."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

BASE = "8d5a1701df3e9d755ac0a4b5adda2845873f52eb"
L33_HASH = "24e71f94c8acfc3aa59184c49a811d62f54fc93d90178bbebef6c8239912467b"
EXPECTED_PINS = {
    "evidence/l36_falsification_report.json": "18ba0c5ee8644581987321a955133518481e86f5c702600b11cf2d9dc904ba96",
    "evidence/l37_integration_plan.json": "51aa9fd4b612af45ac53d049fe21184ad15123b8154b7d72a8c71f5692d0f466",
    "evidence/l37_validation.json": "ecc7e2cee1c066b1dc39f85136efd850422901b08936cd892b13d981ba6ff926",
    "evidence/l38_validation.json": "d3ec936ccc7ebeb1aeb7d629d90b0767a8fc15d9ff6e772637a4c2c9ca7adba8",
    "evidence/l39_recovery_matrix.json": "c9c7afe88785c3e59b8e2954834973ca6478d424b4402a008d756fabb3762b1c",
    "evidence/l40_outbox_validation.json": "5bf243322cac38204defd66402b20b771d547ef6c6027567f91fc283fab6f2cf",
    "evidence/l40_registry_snapshot.json": "a31283d5d4b070397e98aa72e0d4abb90c7d860d53220ba57bd76cafe3f9c7ab",
    "code/l37_nonexecuted_candidate.py": "4384b085f79dff51af5dbbf8a4c4bf4cae6deffc906bfbcaf8a8ef00a7e05dec",
    "code/l37_runtime_guard.py": "b6bcabaf081bb1d6bf31b0ff907369bef841cf012d33b4ec407efd9bd6d94965",
}
GATES = [
    ("archived_checkpoint_integrity", "PASS_ARCHIVED", "Reproducible published evidence integrity"),
    ("offline_preflight_contract", "PROTOTYPE_ONLY", "L36 46 negative controls; design only"),
    ("pre_simulator_hook_position", "PROTOTYPE_ONLY", "L37 static preflight hook; intentionally denied"),
    ("post_export_seal_hook_position", "PROTOTYPE_ONLY", "L37 static sealing hook; intentionally denied"),
    ("single_host_nonce_consumption", "PROTOTYPE_ONLY", "L38 process-restart rejection without trusted issuer"),
    ("transactional_receipt_outbox", "PROTOTYPE_ONLY", "L40 committed bytes, two simulated recovery windows"),
    ("incomplete_session_quarantine", "PROTOTYPE_ONLY", "L39 20 simulated cases; no real power failure"),
    ("guarded_live_gpu_launch_authorization", "BLOCKED", "No separate live authorization, live guard denied"),
    ("candidate_scene_and_metadata_staging", "BLOCKED", "L37 source hash/run identity not rebound; assets absent"),
    ("capture_hook_to_persistent_outbox", "BLOCKED", "L37 hook not wired into L38/L40 prototypes"),
    ("per_sensor_acquisition_session_binding", "BLOCKED", "Actual per-modality payload witness not acquired"),
    ("independent_immutable_witness_storage", "BLOCKED", "No separately controlled immutable acquisition witness"),
    ("independent_sensor_source_authenticity", "NOT_QUALIFIED", "No independent physical acquisition origin"),
    ("hardware_backed_attestation", "NOT_QUALIFIED", "No independently authenticated hardware witness"),
    ("power_loss_durability", "NOT_QUALIFIED", "No actual interruption/power failure study"),
    ("multi_host_replay_protection", "NOT_QUALIFIED", "SQLite prototype is single-host"),
    ("physical_exposure_clock_synchronization", "NOT_QUALIFIED", "No qualified exposure-clock mapping"),
    ("sensor_intrinsic_extrinsic_calibration", "NOT_QUALIFIED", "Independent calibration/provenance not established"),
    ("independent_six_dof_reference", "NOT_QUALIFIED", "Scripted USD transform is not independent six-DoF truth"),
    ("heldout_scientific_pose_health_evaluation", "NOT_QUALIFIED", "No qualified ATE/RPE/factor uncertainty/health labels"),
]
NEXT_TASKS = [
    {"order": 1, "phase": "L42", "task": "Draft offline-only hook-to-outbox binding with exact source/scene/script/run identifiers and per-modality witness schema", "success_gate": "Falsify inconsistent session bindings without Isaac Sim execution"},
    {"order": 2, "phase": "L43", "task": "Test adversarial atomic state transitions, stale challenges, tampered payload handles and incomplete captures", "success_gate": "Fail closed without replacing evidence or reopening nonce"},
    {"order": 3, "phase": "L44", "task": "Build separately scoped witness/attestation trust-boundary review and crash/power durability test plan", "success_gate": "Document independent assumptions and required real fault injection"},
    {"order": 4, "phase": "FUTURE_AUTHORIZED", "task": "Only after guarded source/scene metadata binding, explicit authorization and safety review, plan one new synthetic acquisition", "success_gate": "Do not equate successful capture with physical exposure or six-DoF qualification"},
]


def need(cond, msg):
    if not cond:
        raise ValueError(msg)


def sha(path):
    p = Path(path)
    need(p.is_file() and not p.is_symlink() and p.stat().st_nlink == 1, "Unsafe input " + str(p))
    need(p.stat().st_size < 3_000_000, "Oversized input " + str(p))
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_report(report):
    need(report["schema"] == "TRUST_ROBOT_L41_ACQUISITION_WITNESS_READINESS_V1", "Schema")
    need(report["parent_commit"] == BASE, "Parent revision")
    need(report["l33_contract_sha256"] == L33_HASH, "L33 provenance")
    need(report["technical_test_counts"] == {"l36_adversarial_controls": 46, "l37_static_mutations": 12, "l38_adversarial_controls": 20, "l39_crash_matrix_cases": 20, "l40_recovery_windows": 2, "l40_rejected_faults": 7}, "Test count")
    need(report["gates"] == [dict(id=i, status=s, justification=j) for i, s, j in GATES], "Gate matrix")
    need(report["prioritized_next_steps"] == NEXT_TASKS, "Action plan")
    need(report["acquisition_stages"] == [{"stage": s, "name": name, "independently_qualified": False} for s, name in (("A", "source_provenance"), ("B", "exposure_timing_and_calibration"), ("C", "independent_six_dof_reference"), ("D", "prospective_heldout_validation"))], "Qualification stage")
    need(report["claim_flags"] == {k: False for k in (
        "live_simulator_execution_authorized", "live_guard_satisfied", "independent_source_authenticity_verified", "hardware_attestation_verified", "physical_sync_verified", "independent_6dof_reference_verified", "power_loss_durability_verified", "multi_host_replay_verified", "scientific_accuracy_qualified", "witness_independent_of_capture_host")}, "Scientific claim")
    need(report["scientific_pose_factors"] == 0 and report["health_labels"] == 0 and report["new_sensor_measurements"] == 0, "Admission restriction")
    need(report["readiness_verdict"] == "LIVE_CAPTURE_DENIED_SCIENCE_GATES_CLOSED", "Readiness verdict")
    need(report["checkpoint_manifest_sha256"] and report["assessment_source_sha256"] and report["files_sha256"] == EXPECTED_PINS, "Source manifest integrity fields")


def main(args):
    archive = Path(args.archive)
    contract_path = Path(args.l33_contract)
    report_path = Path(args.report)
    need(not report_path.exists(), "Output collision")
    need(sha(contract_path) == L33_HASH, "Frozen L33 contract mismatch")

    manifest = load(archive / "checkpoint_manifest_v1.json")
    need(manifest["schema"] == "TRUST_ROBOT_KIOS_L36_L40_CHECKPOINT_V1", "Checkpoint schema")
    need(manifest["parent_commit"] == "0b542e8644f3c4b98ed92c0f83a7c82a4635ae52", "Checkpoint lineage")
    need(manifest["new_sensor_acquisitions"] == 0 and manifest["pose_factors_authorized"] == 0 and manifest["health_labels_generated"] == 0, "Prior science promotion")
    for key in ("independent_source_authenticity_verified", "hardware_attestation_verified", "physical_sync_verified", "real_power_loss_durability_verified", "live_simulator_launch_authorized"):
        need(manifest[key] is False, "Prior qualification claim " + key)

    for relative, expected in EXPECTED_PINS.items():
        need(manifest["files_sha256"][relative] == expected and sha(archive / relative) == expected, "Published file mismatch: " + relative)

    l33 = load(contract_path)
    need(l33["schema"] == "TRUST_ROBOT_L33_PROSPECTIVE_ACQUISITION_CONTRACT_V1", "L33 schema")
    stages = l33["future_capture_stages"]
    need([(s["stage"], s["name"], s["qualification"]) for s in stages] == [
        ("A", "source_provenance", "NOT_YET_VERIFIED"),
        ("B", "exposure_timing_and_calibration", "NOT_YET_VERIFIED"),
        ("C", "independent_six_dof_reference", "NOT_YET_VERIFIED"),
        ("D", "prospective_heldout_validation", "NOT_YET_VERIFIED")], "L33 stage status")
    need(len(l33["requirements_preserved"]) == 11, "L33 scientific requirements")

    r36 = load(archive / "evidence/l36_falsification_report.json")
    r37 = load(archive / "evidence/l37_validation.json")
    p37 = load(archive / "evidence/l37_integration_plan.json")
    r38 = load(archive / "evidence/l38_validation.json")
    r39 = load(archive / "evidence/l39_recovery_matrix.json")
    r40 = load(archive / "evidence/l40_outbox_validation.json")
    s40 = load(archive / "evidence/l40_registry_snapshot.json")
    source = (archive / "code/l37_nonexecuted_candidate.py").read_text(encoding="utf-8")
    guard = (archive / "code/l37_runtime_guard.py").read_text(encoding="utf-8")

    need(r36["negative_controls_count"] == 46 and r36["simulator_launch_authorized"] is False, "L36")
    need(r37["static_mutations_rejected_count"] == 12 and r37["runtime_preflight_denied"] and r37["runtime_seal_denied"], "L37")
    need(p37["live_simulator_launch_enabled"] is False and p37["scene_and_runtime_assets_staged"] is False and p37["candidate_metadata_rebound_to_new_script_hash"] is False, "L37 not staged")
    need("L37_LIVE_SIMULATOR_LAUNCH_NOT_AUTHORIZED" in guard and "L37_LIVE_CAPTURE_SEAL_NOT_QUALIFIED" in guard, "Guard claims")
    need(source.index("from l37_runtime_guard import preflight_gate") < source.index("from isaacsim import SimulationApp"), "Preflight location")
    need(source.index("from l37_runtime_guard import seal_after_capture") > source.index("    _l29_export("), "Sealing location")
    need("l38_registry" not in source and "l40_outbox" not in source, "Outbox already wired; reassess L41 assumptions")
    need(r38["final_registry_state"] == "SEALED" and r38["adversarial_mutations_count"] == 20 and r38["separate_process_replay_rejection_observed"] is True and r38["multi_host_replay_protection_verified"] is False, "L38")
    need(r39["case_count"] == 20 and r39["decision_counts"] == {"VERIFIED_SEALED": 1, "ISSUED_REVIEW_REQUIRED": 1, "ADMITTED_REVIEW_REQUIRED": 1, "QUARANTINED": 17} and r39["real_power_failure_experiment_performed"] is False, "L39")
    need(r40["recovery_count"] == 2 and r40["faults_rejected_count"] == 7 and r40["nonce_replay_rejected"] is True and r40["actual_power_failure_tested"] is False, "L40")
    need(s40["state"] == "SEALED" and len(s40["outbox"]) == 3 and all(x["published"] == 1 for x in s40["outbox"]), "Outbox snapshot")

    result = {
        "schema": "TRUST_ROBOT_L41_ACQUISITION_WITNESS_READINESS_V1",
        "parent_commit": BASE,
        "checkpoint_manifest_sha256": sha(archive / "checkpoint_manifest_v1.json"),
        "assessment_source_sha256": sha(__file__),
        "l33_contract_sha256": L33_HASH,
        "files_sha256": EXPECTED_PINS,
        "technical_test_counts": {
            "l36_adversarial_controls": 46, "l37_static_mutations": 12,
            "l38_adversarial_controls": 20, "l39_crash_matrix_cases": 20,
            "l40_recovery_windows": 2, "l40_rejected_faults": 7},
        "gates": [dict(id=i, status=s, justification=j) for i, s, j in GATES],
        "acquisition_stages": [{"stage": s["stage"], "name": s["name"], "independently_qualified": False} for s in stages],
        "prioritized_next_steps": NEXT_TASKS,
        "claim_flags": {k: False for k in (
            "live_simulator_execution_authorized", "live_guard_satisfied",
            "independent_source_authenticity_verified", "hardware_attestation_verified",
            "physical_sync_verified", "independent_6dof_reference_verified",
            "power_loss_durability_verified", "multi_host_replay_verified",
            "scientific_accuracy_qualified", "witness_independent_of_capture_host")},
        "scientific_pose_factors": 0,
        "health_labels": 0,
        "new_sensor_measurements": 0,
        "readiness_verdict": "LIVE_CAPTURE_DENIED_SCIENCE_GATES_CLOSED",
    }
    check_report(result)

    # Mutation controls demonstrate denial when prospective readiness is forged.
    cases = {}
    for i, _, _ in GATES:
        def edit(x, i=i):
            row = next(t for t in x["gates"] if t["id"] == i)
            row["status"] = "READY_FOR_LIVE_CAPTURE"
        cases["false_ready_" + i] = edit
    cases.update({
        "replace_parent_commit": lambda x: x.update(parent_commit="0" * 40),
        "increase_pose_factors": lambda x: x.update(scientific_pose_factors=1),
        "declare_health_labels": lambda x: x.update(health_labels=1),
        "enable_live_authorization": lambda x: x["claim_flags"].update(live_simulator_execution_authorized=True),
        "promote_independent_reference": lambda x: x["acquisition_stages"][2].update(independently_qualified=True),
        "fake_test_count": lambda x: x["technical_test_counts"].update(l40_rejected_faults=8),
    })
    rejected = []
    for name, change in cases.items():
        tampered = copy.deepcopy(result)
        change(tampered)
        try:
            check_report(tampered)
        except (ValueError, KeyError, TypeError, StopIteration):
            rejected.append(name)
        else:
            raise AssertionError("Forgery admitted: " + name)
    need(len(rejected) == 26 and len(set(rejected)) == 26, "Negative control count")
    result["negative_controls_rejected"] = rejected
    result["negative_controls_count"] = len(rejected)
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")

    print("L41_EVIDENCE_DERIVED_GATES=" + str(len(GATES)))
    print("L41_L33_FOUR_QUALIFICATION_STAGES=CLOSED")
    print("L41_READINESS_FORGERY_CONTROLS=26_REJECTED")
    print("L41_LIVE_GPU_LAUNCH=DENIED")
    print("L41_EVIDENCE_READINESS_AUDIT=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--l33-contract", required=True)
    parser.add_argument("--report", required=True)
    main(parser.parse_args())
