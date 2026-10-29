"""R135-A21: cross-study evidence consistency and admission review.

Replays the four frozen manufactured studies R135-A17..A20.
Validates cross-version parity and separates numerical solver
acceptance from active measurement support and physical evidence.

This is an offline synthetic scientific decision aid, not
a health classifier, trust score or real-data admission action.
"""
from __future__ import annotations

import hashlib
import json
import math

from trust_robot.analytic_15d_exhaustive_lidar_dropout_v1 import (
    run_matrix as run_a17,
    DENIALS as A17_DENIALS,
)

from trust_robot.analytic_15d_joint_imu_lidar_stress_v1 import (
    run_matrix as run_a18,
    DENIALS as A18_DENIALS,
)

from trust_robot.analytic_15d_long_horizon_joint_stress_v1 import (
    run_matrix as run_a19,
    DENIALS as A19_DENIALS,
)

from trust_robot.analytic_15d_combined_imu_faults_v1 import (
    run_matrix as run_a20,
    DENIALS as A20_DENIALS,
)

SCHEMA = "TRUST_ROBOT_R135_A21_EVIDENCE_REVIEW_V1"
STATUS = "SYNTHETIC_ONLY_NO_SCIENTIFIC_ADMISSION"

BLOCKED_CAPABILITIES = (
    "real_sensor_factor_admission",
    "physical_localization_accuracy_claims",
    "physical_localization_recovery_claims",
    "independent_same_edge_camera_lidar_weighting",
    "health_probability_inference",
    "health_label_assignment",
    "learned_health_controlled_factor_weighting",
    "recorded_ground_truth_scoring",
    "confirmation_test_access",
)

STUDY_COUNTS = {
    "A17": 128,
    "A18": 256,
    "A19": 15,
    "A20": 20,
}


class EvidenceReviewError(ValueError):
    """Cross-study inconsistency or unsupported scientific claim."""


def _require(ok, message):
    if not ok:
        raise EvidenceReviewError(message)


def _key_edges(row):
    return tuple(
        tuple(edge) for edge in row["removed_edges"]
    )


def _index(rows, key):
    entries = {}

    for row in rows:
        identity = key(row)

        _require(
            identity not in entries,
            "Duplicate published configuration",
        )

        entries[identity] = row

    return entries


def _audit_study(rows, label, denials):
    _require(
        len(rows) == STUDY_COUNTS[label],
        "Unexpected published study size: " + label,
    )

    accepted = 0
    rejected = 0

    for row in rows:
        _require(
            all(row[k] is False for k in denials),
            "Scientific denial altered: " + label,
        )

        outcome = row["solver_outcome"]

        if outcome == "ACCEPTED":
            accepted += 1

            _require(
                row["synthetic_final_position_m"] is not None
                and len(row["synthetic_state_sha256"]) == 64
                and math.isfinite(
                    row["total_window_cost_diagnostic"]
                ),
                "Invalid accepted synthetic output",
            )

        elif outcome == "NUMERICALLY_REJECTED":
            rejected += 1

            _require(
                row["numerical_rejection"].startswith(
                    "Marginalized window solve failed at "
                ),
                "Unexpected numerical rejection",
            )

        else:
            raise EvidenceReviewError(
                "Unknown published solver outcome"
            )

    _require(
        accepted + rejected == STUDY_COUNTS[label],
        "Incomplete solver outcomes",
    )

    return {
        "configuration_count": len(rows),
        "accepted_count": accepted,
        "numerically_rejected_count": rejected,
        "physical_validation_established": False,
    }


def run_review():
    """Produce the closed-gate scientific evidence decision.

    No external observations, callbacks, ground truth,
    thresholds, health labels or factor weights are accepted.
    """
    a17 = run_a17()
    a18 = run_a18()
    a19 = run_a19()
    a20 = run_a20()

    study_rows = (
        ("A17", a17, A17_DENIALS),
        ("A18", a18, A18_DENIALS),
        ("A19", a19, A19_DENIALS),
        ("A20", a20, A20_DENIALS),
    )

    inventory = {
        name: _audit_study(rows, name, denials)
        for name, rows, denials in study_rows
    }

    _require(
        sum(
            item["configuration_count"]
            for item in inventory.values()
        ) == 419,
        "Incorrect cross-study inventory",
    )

    a17_by = _index(a17, _key_edges)

    a18_by = _index(
        a18,
        lambda row: (row["imu_mode"], _key_edges(row)),
    )

    a19_by = _index(
        a19,
        lambda row: (
            row["imu_mode"], row["outage_name"]
        ),
    )

    a20_by = _index(
        a20,
        lambda row: (
            row["imu_mode"], row["outage_name"]
        ),
    )

    _require(
        len(a17_by) == 128
        and len(a18_by) == 256
        and len(a19_by) == 15
        and len(a20_by) == 20,
        "Published configuration identities inconsistent",
    )

    # A17 and A18 must reproduce the same clean-IMU
    # estimator results for each identical dropout set.
    clean_parity = 0

    for removed, old in a17_by.items():
        current = a18_by["clean", removed]

        _require(
            old["solver_outcome"]
            == current["solver_outcome"]
            and old["synthetic_state_sha256"]
            == current["synthetic_state_sha256"]
            and old["windows_without_current_lidar"]
            == current["windows_without_current_lidar"],
            "Five-node cross-study parity failure",
        )

        clean_parity += 1

    # A20 must leave all fifteen A19 single-fault
    # configurations numerically unchanged.
    long_parity = 0

    for identity, old in a19_by.items():
        current = a20_by[identity]

        _require(
            old["solver_outcome"]
            == current["solver_outcome"]
            and old["synthetic_state_sha256"]
            == current["synthetic_state_sha256"]
            and old["windows_without_current_lidar"]
            == current["windows_without_current_lidar"],
            "Twelve-node cross-study parity failure",
        )

        long_parity += 1

    missing_a17 = sum(
        row["solver_outcome"] == "ACCEPTED"
        and row["windows_without_current_lidar"] > 0
        for row in a17
    )

    missing_a18 = sum(
        row["solver_outcome"] == "ACCEPTED"
        and row["windows_without_current_lidar"] > 0
        for row in a18
    )

    total_dropout = a17_by[
        tuple((
            (0, 1), (0, 2), (1, 2), (1, 3),
            (2, 3), (2, 4), (3, 4),
        ))
    ]

    _require(
        total_dropout["remaining_lidar_factor_count"]
        == 0
        and total_dropout[
            "all_windows_have_current_lidar"
        ] is False,
        "Complete LiDAR dropout misrepresented",
    )

    if total_dropout["solver_outcome"] == "ACCEPTED":
        _require(
            total_dropout["windows_without_current_lidar"]
            == 4,
            "Complete dropout has unexpected support",
        )

    # Compare paired clean and biased IMU estimates,
    # without claiming independent position accuracy.
    paired_count = 0
    paired_max_m = 0.0

    for removed in a17_by:
        clean = a18_by["clean", removed]
        biased = a18_by["accel_bias", removed]

        if (
            clean["solver_outcome"] != "ACCEPTED"
            or biased["solver_outcome"] != "ACCEPTED"
        ):
            continue

        delta = math.dist(
            clean["synthetic_final_position_m"],
            biased["synthetic_final_position_m"],
        )

        _require(
            math.isfinite(delta),
            "Nonfinite synthetic IMU comparison",
        )

        paired_count += 1
        paired_max_m = max(paired_max_m, delta)

    outcomes = {}

    for outage in (
        "none", "mid_four", "mid_six",
        "late_five", "complete",
    ):
        values = {
            mode: a20_by[mode, outage]
            for mode in (
                "clean", "accel_bias",
                "gyro_bias", "combined_bias",
            )
        }

        combined = values["combined_bias"]
        interaction = combined[
            "synthetic_joint_interaction_norm_m"
        ]

        if interaction is not None:
            _require(
                all(
                    r["solver_outcome"] == "ACCEPTED"
                    for r in values.values()
                )
                and math.isfinite(interaction)
                and interaction >= 0,
                "Invalid combined-IMU interaction",
            )

        outcomes[outage] = {
            "current_lidar_factors":
                combined["lidar_factor_count"],
            "combined_solver_outcome":
                combined["solver_outcome"],
            "combined_delta_from_clean_m":
                combined["delta_from_clean_same_outage_m"],
            "interaction_norm_m": interaction,
        }

    complete = outcomes["complete"]

    _require(
        complete["current_lidar_factors"] == 0,
        "Complete outage contains LiDAR factors",
    )

    # Evidence-based closure. These values represent
    # scientific permissions, not a learned trust score.
    admission = {
        name: "BLOCKED"
        for name in BLOCKED_CAPABILITIES
    }

    report = {
        "schema": SCHEMA,
        "status": STATUS,
        "source_commit":
            "f9ffcb63c39b2387194ee835c8e6a82b4942524c",
        "studies": inventory,
        "total_study_configurations": 419,
        "five_node_clean_parity_cases": clean_parity,
        "twelve_node_published_parity_cases": long_parity,
        "a17_accepted_with_missing_current_lidar":
            missing_a17,
        "a18_accepted_with_missing_current_lidar":
            missing_a18,
        "a17_complete_lidar_outage_outcome":
            total_dropout["solver_outcome"],
        "five_node_clean_biased_accepted_pairs":
            paired_count,
        "five_node_max_imu_output_delta_m":
            paired_max_m,
        "long_horizon_combined_outages": outcomes,
        "long_horizon_complete_outage": complete,
        "numerical_solver_acceptance_proves_accuracy":
            False,
        "numeric_rank_proves_physical_observability":
            False,
        "baseline_delta_is_ground_truth_error": False,
        "synthetic_sensor_independence_proven": False,
        "physical_recovery_proven": False,
        "real_sensor_admission_authorized": False,
        "health_inference_authorized": False,
        "factor_weighting_authorized": False,
        "recorded_data_accessed": False,
        "held_out_confirmation_data_accessed": False,
        "m2dgr_gates_closed": 11,
        "m2dgr_split": {
            "train": 22,
            "validation_calibration": 7,
            "confirmation_test": 7,
        },
        "admission_decision": admission,
        "next_scientific_priorities": [
            "independent_sensor_timing_and_frame_evidence",
            "camera_lidar_metric_calibration_and_provenance",
            "defensible_sensor_health_supervision",
            "factor_information_and_uncertainty_validation",
            "controlled_multi_scene_robustness_evaluation",
            "admission_gated_recorded_dataset_study",
        ],
    }

    _require(
        clean_parity == 128
        and long_parity == 15
        and all(v == "BLOCKED" for v in admission.values()),
        "Insufficient or contradictory scientific evidence",
    )

    return report


def evidence_digest(report):
    """Deterministic hash of a validated evidence report."""
    _require(
        type(report) is dict
        and report.get("schema") == SCHEMA
        and report.get("m2dgr_gates_closed") == 11,
        "Invalid evidence report",
    )

    raw = json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()
