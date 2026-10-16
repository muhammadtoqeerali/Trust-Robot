"""L50 offline consolidated trust-boundary review.

No independent physical attestation or distributed security proof.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path

BASE = "c2e013f549b87e8646a8e51095a3372df0d09581"
DENY = "QUARANTINE_REVIEW_REQUIRED"

GAPS = (
    "independently_authenticated_capture_origin",
    "independently_administered_witness_authority",
    "globally_consistent_nonce_consumption",
    "tamper_resistant_witness_retention",
    "trusted_physical_exposure_time",
    "independently_verified_sensor_calibration",
    "independent_6dof_reference",
    "sensor_payload_capture_attestation",
    "real_power_loss_durability",
    "real_multi_host_partition_replay_protection",
    "fixed_clean_6dof_estimator_scientifically_qualified",
    "trained_three_state_modality_health_model",
    "validated_health_probability_calibration",
    "health_aware_factor_admission_and_weighting",
    "guarded_closed_loop_safety_validation",
    "independently_approved_live_capture",
)

PROTOTYPES = (
    "l46_ephemeral_two_role_mac_simulation",
    "l47_single_file_concurrent_nonce_exclusion",
    "l47_split_registry_double_admission_demonstration",
    "l48_duplicate_nonce_quarantine_detection",
    "l49_simulated_authority_failure_quarantine",
    "l49_outbox_publication_and_recovery_rehearsal",
)

CLOSED_FLAGS = (
    "live_simulator_launch_authorized",
    "trusted_physical_sensor_origin_proven",
    "globally_unique_nonce_proven",
    "scientific_pose_factor_admission_authorized",
    "trained_health_labels_qualified",
    "scientific_6dof_accuracy_scoring_authorized",
)


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def read(path):
    p = Path(path)

    need(
        p.is_file()
        and not p.is_symlink()
        and p.stat().st_nlink == 1
        and p.stat().st_size < 5000000,
        "UNSAFE_INPUT:" + str(p),
    )

    return json.loads(p.read_bytes())


def dump(path, obj):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(
            obj,
            f,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        f.write("\n")


def evidence(p):
    c46 = read(p["c46"])
    r46 = read(p["r46"])
    v46 = read(p["v46"])

    c47 = read(p["c47"])
    r47 = read(p["r47"])
    v47 = read(p["v47"])

    c48 = read(p["c48"])
    r48 = read(p["r48"])
    v48 = read(p["v48"])

    c49 = read(p["c49"])
    r49 = read(p["r49"])
    v49 = read(p["v49"])

    need(
        all(
            c["parent_commit"] == BASE
            for c in (c46, c47, c48, c49)
        ),
        "PARENT_COMMIT",
    )

    for phase, c, r, v in (
        (46, c46, r46, v46),
        (47, c47, r47, v47),
        (48, c48, r48, v48),
        (49, c49, r49, v49),
    ):
        need(
            r["contract_sha256"] == sha(p[f"c{phase}"])
            and v["report_sha256"] == sha(p[f"r{phase}"]),
            f"LINEAGE_{phase}",
        )

    need(
        r46["test_results"]["negative_controls_denied"] == 35
        and r46["test_results"][
            "coherent_software_forgery_internally_accepted"
        ] is True
        and r46["test_results"][
            "coherent_software_forgery_trusted"
        ] is False
        and r46["test_results"][
            "independent_registry_clone_double_acceptance"
        ] is True
        and v46["fresh_negative_controls_reproduced"] == 35
        and v46["independent_physical_witness_qualified"]
        is False,
        "L46_PROVENANCE",
    )

    need(
        r47["central_single_host_successes"] == 1
        and r47["central_single_host_replays_denied"] == 7
        and r47["split_registry_same_nonce_admissions"] == 2
        and r47["globally_unique_admission_proven"] is False
        and r47["invalid_request_control_count"] == 20
        and r47["fault_count"] == 8
        and v47["rechecked_bad_request_controls"] == 20
        and v47["rechecked_ledger_faults"] == 8,
        "L47_DUPLICATE",
    )

    need(
        r48["verified_local_receipts"] == 3
        and r48["same_nonce_local_admissions"] == 3
        and r48["detected_duplicate_nonce"] is True
        and r48["quarantine_decision"] == DENY
        and r48["metadata_mutation_count"] == 24
        and r48["ledger_fault_count"] == 10
        and r48["capture_promotion_authorized"] is False
        and v48["verified_mutations_denied"] == 24
        and v48["verified_ledger_faults_denied"] == 10,
        "L48_QUARANTINE",
    )

    need(
        r49["scenario_count"]
        == r49["quarantine_decisions"]
        == 18
        and r49["negative_claim_count"] == 12
        and len(r49["recovery_windows"]) == 3
        and r49["receipt_fault_count"] == 10
        and v49["verified_outage_scenarios"] == 18
        and v49["verified_false_promotions"] == 12
        and v49["verified_publication_paths"] == 3
        and v49["verified_fault_denials"] == 10,
        "L49_FAILURE",
    )

    need(
        len(r49["scenarios"]) == 18
        and all(
            item["decision"] == DENY
            and item["promoted_capture"] is False
            and item["reconciliation_performed"] is False
            for item in r49["scenarios"]
        ),
        "L49_SCENARIO_DENIAL",
    )

    need(
        len(r48["ledgers"]) == 3
        and len(r49["source_ledgers"]) == 3,
        "THREE_LEDGER_LINEAGE",
    )

    for previous, current in zip(
        r48["ledgers"],
        r49["source_ledgers"],
    ):
        need(
            all(
                previous[key] == current[key]
                for key in (
                    "label",
                    "session_id",
                    "nonce_sha256",
                    "request_sha256",
                    "database_sha256",
                    "receipt_sha256",
                )
            ),
            "L48_L49_LEDGER_BINDING",
        )

    need(
        len({
            item["nonce_sha256"]
            for item in r48["ledgers"]
        }) == 1,
        "DUPLICATE_NONCE_PRESENT",
    )

    need(
        r47["central"]["nonce_sha256"]
        == r48["ledgers"][0]["nonce_sha256"]
        and all(
            previous["receipt_sha256"]
            == current["receipt_sha256"]
            for previous, current in zip(
                [r47["central"], *r47["split"]],
                r48["ledgers"],
            )
        ),
        "L47_L48_RECEIPTS",
    )

    for report in (r46, r47, r48, r49):
        for key in (
            "new_sensor_measurements",
            "pose_factors_authorized",
            "health_labels_generated",
        ):
            if key in report:
                need(
                    type(report[key]) is int
                    and report[key] == 0,
                    "SCIENTIFIC_GATE_" + key,
                )

    for report in (r48, r49):
        for key in (
            "scientific_pose_factors",
            "health_labels",
        ):
            need(
                type(report[key]) is int
                and report[key] == 0,
                "SCIENTIFIC_GATE_" + key,
            )

    need(
        r48["real_sensor_measurements"] == 0
        and r49["new_sensor_measurements"] == 0,
        "NO_SENSOR_MEASUREMENTS",
    )

    need(
        c49["independent_witness_present"] is False
        and c49["global_nonce_ledger_present"] is False
        and r49["global_replay_prevention_verified"] is False
        and r49["physical_witness_verified"] is False
        and r49["real_power_failure_tested"] is False,
        "L49_QUALIFICATION",
    )

    return {
        "l46_role_controls_denied": 35,
        "l47_local_admissions": 1,
        "l47_local_replays_denied": 7,
        "l47_split_duplicate_admissions": 2,
        "l48_quarantined_conflicts": 1,
        "l48_mutations_denied": 24,
        "l48_faults_denied": 10,
        "l49_outage_scenarios_quarantined": 18,
        "l49_false_promotions_denied": 12,
        "l49_publication_paths_tested": 3,
        "l49_faults_denied": 10,
    }


def build_matrix(counts):
    gates = []

    for name in PROTOTYPES:
        gates.append({
            "gate": name,
            "status": "OFFLINE_ENGINEERING_EVIDENCE",
            "trusted_sensor_provenance": False,
            "supports_scientific_factor_admission": False,
        })

    for name in GAPS:
        gates.append({
            "gate": name,
            "status": "NOT_QUALIFIED",
            "trusted_sensor_provenance": False,
            "supports_scientific_factor_admission": False,
        })

    return {
        "schema": "TRUST_ROBOT_L50_TRUST_BOUNDARY_MATRIX_V1",
        "parent_commit": BASE,
        "evidence_counts": counts,
        "gates": gates,
        "offline_prototype_gates": len(PROTOTYPES),
        "unqualified_required_gates": len(GAPS),
        "authority_verdict":
            "QUARANTINE_AND_NO_AUTOMATIC_PROMOTION",
        "next_scientific_priority":
            "RESUME_FIXED_CLEAN_6DOF_ESTIMATOR_AND_EVIDENCE_GATES",
        "live_simulator_launch_authorized": False,
        "trusted_physical_sensor_origin_proven": False,
        "globally_unique_nonce_proven": False,
        "scientific_pose_factor_admission_authorized": False,
        "trained_health_labels_qualified": False,
        "scientific_6dof_accuracy_scoring_authorized": False,
        "new_sensor_measurements": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
    }


def check_matrix(matrix, counts):
    expected = build_matrix(counts)

    need(
        type(matrix) is dict and matrix == expected,
        "MATRIX_POLICY_OR_INTEGRITY",
    )

    return True


def negative_controls(matrix, counts):
    cases = []

    for i, gate in enumerate(GAPS):
        changed = copy.deepcopy(matrix)

        changed["gates"][
            len(PROTOTYPES) + i
        ]["status"] = "QUALIFIED"

        cases.append((
            "false_qualification_" + gate,
            changed,
        ))

    for key in CLOSED_FLAGS:
        changed = copy.deepcopy(matrix)
        changed[key] = True

        cases.append((
            "false_authorization_" + key,
            changed,
        ))

    for key in list(counts)[:6]:
        changed = copy.deepcopy(matrix)

        changed["evidence_counts"][key] += 1

        cases.append((
            "falsified_count_" + key,
            changed,
        ))

    for key, value in (
        ("parent_commit", "0" * 40),
        ("authority_verdict", "ACCEPT"),
        ("offline_prototype_gates", 0),
        ("unqualified_required_gates", 0),
    ):
        changed = copy.deepcopy(matrix)
        changed[key] = value

        cases.append((
            "inaccurate_" + key,
            changed,
        ))

    need(
        len(cases) == 32,
        "NEGATIVE_CONTROL_COUNT",
    )

    denied = []

    for name, changed in cases:
        try:
            check_matrix(changed, counts)

        except ValueError:
            denied.append(name)

        else:
            raise AssertionError(
                "FALSE_PROMOTION_ACCEPTED:" + name
            )

    need(
        len(denied) == len(set(denied)) == 32,
        "NEGATIVE_CONTROL_UNIQUENESS",
    )

    return denied


def run(args):
    files = {
        f"{prefix}{phase}": getattr(
            args,
            f"{prefix}{phase}",
        )
        for phase in (46, 47, 48, 49)
        for prefix in ("c", "r", "v")
    }

    counts = evidence(files)

    matrix = build_matrix(counts)
    check_matrix(matrix, counts)

    denied = negative_controls(
        matrix,
        counts,
    )

    contract = {
        "schema":
            "TRUST_ROBOT_L50_CONSOLIDATED_REVIEW_CONTRACT_V1",
        "parent_commit": BASE,
        "engine_sha256": sha(__file__),
        "frozen_input_sha256": {
            key: sha(path)
            for key, path in sorted(files.items())
        },
        "offline_scope_only": True,
        "physical_source_proof": False,
        "distributed_security_proof": False,
        "physical_power_loss_tested": False,
        "scientific_pose_factors_authorized": 0,
    }

    dump(
        args.contract,
        contract,
    )

    dump(
        args.matrix,
        matrix,
    )

    report = {
        "schema":
            "TRUST_ROBOT_L50_CONSOLIDATED_REVIEW_REPORT_V1",
        "contract_sha256": sha(args.contract),
        "matrix_sha256": sha(args.matrix),
        "reviewed_phases": [46, 47, 48, 49],
        "evidence_counts": counts,
        "offline_prototype_gates": len(PROTOTYPES),
        "unqualified_required_gates": len(GAPS),
        "negative_controls_denied": denied,
        "negative_control_count": len(denied),
        "decision":
            "NO_GO_LIVE_CAPTURE_OR_SCIENTIFIC_POSE_FACTORS",
        "reconciliation_state": DENY,
        "automatic_unquarantine_authorized": False,
        "independent_sensor_witness_verified": False,
        "globally_unique_nonce_proven": False,
        "recommended_next_work":
            "POST_CHECKPOINT_RETURN_TO_CORE_SCIENTIFIC_ESTIMATOR_AND_DATA_EVIDENCE",
        "new_sensor_measurements": 0,
        "scientific_pose_factors": 0,
        "health_labels": 0,
        "github_commit_or_push": False,
    }

    dump(
        args.report,
        report,
    )

    print("L50_L46_L49_SOURCE_CHAIN=VERIFIED")
    print("L50_ENGINEERING_EVIDENCE_GATES=6_DOCUMENTED")
    print("L50_UNQUALIFIED_SCIENCE_AND_AUTHORITY_GATES=16_CLOSED")
    print("L50_FALSE_PROMOTION_CONTROLS=32_REJECTED")
    print("L50_TRUST_BOUNDARY_VERDICT=NO_GO_QUARANTINE")
    print("L50_CONSOLIDATED_OFFLINE_REVIEW=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    for phase in (46, 47, 48, 49):
        for prefix in ("c", "r", "v"):
            name = f"{prefix}{phase}"

            p.add_argument(
                "--" + name,
                required=True,
            )

    for name in (
        "contract",
        "matrix",
        "report",
    ):
        p.add_argument(
            "--" + name,
            required=True,
        )

    run(p.parse_args())
