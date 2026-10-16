"""L50 separate-process verification of source claims and gap matrix.

This is software verification, not independent physical attestation.
"""

import argparse
import hashlib
import json
from pathlib import Path

import l50_review as review


def need(condition, why):
    if not condition:
        raise AssertionError(why)


def sha(path):
    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def read(path):
    return json.loads(
        Path(path).read_bytes()
    )


def run(a):
    files = {
        f"{prefix}{phase}": getattr(
            a,
            f"{prefix}{phase}",
        )
        for phase in (46, 47, 48, 49)
        for prefix in ("c", "r", "v")
    }

    contract = read(a.contract)
    matrix = read(a.matrix)
    report = read(a.report)

    need(
        contract["schema"]
        == "TRUST_ROBOT_L50_CONSOLIDATED_REVIEW_CONTRACT_V1",
        "CONTRACT_SCHEMA",
    )

    need(
        report["schema"]
        == "TRUST_ROBOT_L50_CONSOLIDATED_REVIEW_REPORT_V1",
        "REPORT_SCHEMA",
    )

    need(
        contract["parent_commit"] == review.BASE
        and contract["engine_sha256"] == sha(a.engine),
        "ENGINE_LINEAGE",
    )

    need(
        contract["frozen_input_sha256"] == {
            key: sha(path)
            for key, path in sorted(files.items())
        },
        "FROZEN_INPUTS",
    )

    need(
        report["contract_sha256"] == sha(a.contract)
        and report["matrix_sha256"] == sha(a.matrix),
        "OUTPUT_LINEAGE",
    )

    for key in (
        "physical_source_proof",
        "distributed_security_proof",
        "physical_power_loss_tested",
    ):
        need(
            contract[key] is False,
            "UNSUPPORTED_CONTRACT_CLAIM:" + key,
        )

    need(
        contract["offline_scope_only"] is True
        and contract["scientific_pose_factors_authorized"] == 0,
        "OFFLINE_SCOPE",
    )

    counts = review.evidence(files)

    need(
        counts
        == matrix["evidence_counts"]
        == report["evidence_counts"],
        "INDEPENDENT_EVIDENCE_COUNTS",
    )

    need(
        matrix["schema"]
        == "TRUST_ROBOT_L50_TRUST_BOUNDARY_MATRIX_V1"
        and matrix["parent_commit"] == review.BASE,
        "MATRIX_SCHEMA",
    )

    need(
        len(matrix["gates"]) == 22
        and [
            x["gate"]
            for x in matrix["gates"][:6]
        ] == list(review.PROTOTYPES)
        and [
            x["gate"]
            for x in matrix["gates"][6:]
        ] == list(review.GAPS),
        "GATE_INVENTORY",
    )

    for i, gate in enumerate(matrix["gates"]):
        expected_status = (
            "OFFLINE_ENGINEERING_EVIDENCE"
            if i < 6
            else "NOT_QUALIFIED"
        )

        need(
            gate["status"] == expected_status
            and gate["trusted_sensor_provenance"] is False
            and gate[
                "supports_scientific_factor_admission"
            ] is False,
            "UNSUPPORTED_GATE_PROMOTION",
        )

    need(
        matrix["offline_prototype_gates"] == 6
        and matrix["unqualified_required_gates"] == 16,
        "GATE_COUNTS",
    )

    need(
        matrix["authority_verdict"]
        == "QUARANTINE_AND_NO_AUTOMATIC_PROMOTION"
        and matrix["next_scientific_priority"]
        == "RESUME_FIXED_CLEAN_6DOF_ESTIMATOR_AND_EVIDENCE_GATES",
        "MATRIX_VERDICT",
    )

    for key in review.CLOSED_FLAGS:
        need(
            matrix[key] is False,
            "UNQUALIFIED_CLAIM:" + key,
        )

    for key in (
        "new_sensor_measurements",
        "scientific_pose_factors",
        "health_labels",
    ):
        need(
            type(matrix[key]) is int
            and matrix[key] == 0,
            "MATRIX_SCIENCE:" + key,
        )

    denied = review.negative_controls(
        review.build_matrix(counts),
        counts,
    )

    need(
        denied == report["negative_controls_denied"]
        and report["negative_control_count"] == 32,
        "INDEPENDENT_NEGATIVE_CONTROLS",
    )

    need(
        report["reviewed_phases"] == [46, 47, 48, 49]
        and report["offline_prototype_gates"] == 6
        and report["unqualified_required_gates"] == 16,
        "REPORT_PHASE_COUNTS",
    )

    need(
        report["decision"]
        == "NO_GO_LIVE_CAPTURE_OR_SCIENTIFIC_POSE_FACTORS"
        and report["reconciliation_state"] == review.DENY,
        "REPORT_DECISION",
    )

    for key in (
        "automatic_unquarantine_authorized",
        "independent_sensor_witness_verified",
        "globally_unique_nonce_proven",
        "github_commit_or_push",
    ):
        need(
            report[key] is False,
            "UNSUPPORTED_REPORT_CLAIM:" + key,
        )

    for key in (
        "new_sensor_measurements",
        "scientific_pose_factors",
        "health_labels",
    ):
        need(
            type(report[key]) is int
            and report[key] == 0,
            "REPORT_SCIENCE:" + key,
        )

    need(
        report["recommended_next_work"]
        == "POST_CHECKPOINT_RETURN_TO_CORE_SCIENTIFIC_ESTIMATOR_AND_DATA_EVIDENCE",
        "NEXT_SCIENTIFIC_PRIORITY",
    )

    validation = {
        "schema":
            "TRUST_ROBOT_L50_INDEPENDENT_VALIDATION_V1",
        "engine_sha256": sha(a.engine),
        "verifier_sha256": sha(__file__),
        "contract_sha256": sha(a.contract),
        "matrix_sha256": sha(a.matrix),
        "report_sha256": sha(a.report),
        "verified_source_phases": 4,
        "verified_offline_engineering_gates": 6,
        "verified_unqualified_gates": 16,
        "verified_negative_controls": 32,
        "automatic_unquarantine_authorized": False,
        "physical_source_authenticity_proven": False,
        "distributed_replay_protection_proven": False,
        "new_sensor_measurements": 0,
        "pose_factors_authorized": 0,
        "health_labels_generated": 0,
    }

    review.dump(
        a.validation,
        validation,
    )

    print("L50_INDEPENDENT_SOURCE_PHASES=4_VERIFIED")
    print("L50_INDEPENDENT_GAP_MATRIX=22_VERIFIED")
    print("L50_INDEPENDENT_NEGATIVE_CONTROLS=32_REJECTED")
    print("L50_INDEPENDENT_VALIDATION=PASS")


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    p.add_argument(
        "--engine",
        required=True,
    )

    for phase in (46, 47, 48, 49):
        for prefix in ("c", "r", "v"):
            p.add_argument(
                "--" + prefix + str(phase),
                required=True,
            )

    for name in (
        "contract",
        "matrix",
        "report",
        "validation",
    ):
        p.add_argument(
            "--" + name,
            required=True,
        )

    run(p.parse_args())
