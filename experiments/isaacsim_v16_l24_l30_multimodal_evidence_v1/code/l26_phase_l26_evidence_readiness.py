"""TRUST-ROBOT L26 evidence readiness audit.

Offline analysis only. Never admits estimator factors or health labels.
Unknown evidence is not silently treated as independent verification.
"""

import argparse
import hashlib
import json
from pathlib import Path

THRESHOLDS = ("0.01", "0.02", "0.04")

GATES = {
    "lidar_pose_factor_admission": (
        "physical_correspondence_validation",
        "qualified_exposure_synchronization",
        "calibrated_factor_uncertainty",
        "verified_extrinsic_transform",
    ),

    "scientific_6dof_accuracy_claim": (
        "independent_6dof_reference",
        "qualified_exposure_synchronization",
        "verified_extrinsic_transform",
        "heldout_6dof_accuracy_evaluation",
    ),

    "supervised_sensor_health_labels": (
        "adjudicated_sensor_failure_labels",
        "independent_source_authenticity",
        "validated_detection_error_rates",
    ),

    "live_sensor_freshness_admission": (
        "independent_source_authenticity",
        "trusted_hardware_exposure_time",
        "qualified_exposure_synchronization",
        "independently_verified_replay_monitor",
    ),
}


def sha(path):
    assert path.is_file() and not path.is_symlink(), str(path)

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def read(path):
    sha(path)
    return json.loads(path.read_text())


def stable(obj):
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ) + "\n"
    ).encode()


def summarize(l23, l24, l25):
    old = {
        x["scenario"]: x
        for x in l23["scenario_summaries"]
    }

    rows = l25["scenario_summaries"]

    assert len(old) == len(rows) == 11

    assert len({
        x["scenario"] for x in rows
    }) == 11

    assert set(old) == {
        x["scenario"] for x in rows
    }

    items = []

    for row in rows:
        name = row["scenario"]
        counterpart = old[name]

        assert row["l23_decision_changes"] == (
            counterpart["decision_changes"]
        )

        assert row["pinned_recording_review"] is True
        assert row["pose_factor_authorized"] is False

        assert row[
            "frozen_reference_is_not_live_trust_anchor"
        ] is True

        flags = row[
            "scripted_motion_excess_threshold_reviews"
        ]

        assert set(flags) == set(THRESHOLDS)
        assert all(type(v) is bool for v in flags.values())

        assert type(
            row["incoming_sequence_review"]
        ) is bool

        assert type(
            row[
                "geometry_fingerprint_changed_from_archived_capture"
            ]
        ) is bool

        assert type(
            row["emitter_ordered_fingerprint_changed"]
        ) is bool

        items.append({
            "scenario": name,

            "l23_screen_decisions_changed":
                row["l23_decision_changes"],

            "incoming_sequence_review":
                row["incoming_sequence_review"],

            "scripted_motion_review_at_threshold_m":
                flags,

            "frozen_snapshot_review":
                row["pinned_recording_review"],

            "geometry_pointset_changed":
                row[
                    "geometry_fingerprint_changed_from_archived_capture"
                ],

            "emitter_ordered_fingerprint_changed":
                row[
                    "emitter_ordered_fingerprint_changed"
                ],

            "internal_diagnostic_reactions_not_detection_labels":
                True,
        })

    assert sum(
        x["l23_screen_decisions_changed"]
        for x in items
    ) == 5

    assert sum(
        x["incoming_sequence_review"]
        for x in items
    ) == 1

    assert sum(
        x["frozen_snapshot_review"]
        for x in items
    ) == 11

    assert sum(
        x["geometry_pointset_changed"]
        for x in items
    ) == 9

    for threshold, expected in (
        ("0.01", 5),
        ("0.02", 3),
        ("0.04", 1),
    ):
        actual = sum(
            x[
                "scripted_motion_review_at_threshold_m"
            ][threshold]
            for x in items
        )

        assert actual == expected

    byname = {
        x["scenario"]: x
        for x in items
    }

    # These geometry alterations had no reaction
    # in the specified internal diagnostic checks.
    for name in (
        "single_return_20mm_101",
        "nonrigid_shear_3pct",
        "nonrigid_shear_15pct",
        "coherent_translation_80mm",
    ):
        x = byname[name]

        assert x["l23_screen_decisions_changed"] == 0
        assert x["incoming_sequence_review"] is False

        assert all(
            v is False
            for v in x[
                "scripted_motion_review_at_threshold_m"
            ].values()
        )

        assert x["geometry_pointset_changed"] is True

    # Reordering storage is not by itself a fault.
    corrected = byname[
        "point_order_changed_mapping_corrected"
    ]

    assert corrected["geometry_pointset_changed"] is False
    assert corrected[
        "emitter_ordered_fingerprint_changed"
    ] is False

    assert corrected["frozen_snapshot_review"] is True
    assert corrected["l23_screen_decisions_changed"] == 0

    stale = byname[
        "point_order_changed_mapping_stale"
    ]

    assert stale["geometry_pointset_changed"] is False

    assert stale[
        "emitter_ordered_fingerprint_changed"
    ] is True

    assert stale["l23_screen_decisions_changed"] == 1

    camera = l25["camera_replay_content_control"]

    assert camera[
        "new_exact_duplicate_camera_content_review"
    ] is True

    assert camera[
        "existing_l24_sequence_review"
    ] is False

    assert camera[
        "duplicate_camera_content_is_proof_of_fault"
    ] is False

    assert l24["incoming_sequence_review_count"] == 8
    assert l24["pinned_review_count"] == 11

    no_reaction = {}

    for threshold in THRESHOLDS:
        no_reaction[threshold] = [
            x["scenario"]
            for x in items
            if x["l23_screen_decisions_changed"] == 0
            and x["incoming_sequence_review"] is False
            and not x[
                "scripted_motion_review_at_threshold_m"
            ][threshold]
        ]

    return {
        "scenario_comparison": items,
        "scenario_count": len(items),

        "l23_total_decision_changes": 5,

        "l24_pinned_challenges_flagged": 11,

        "l24_incoming_sequence_challenges_flagged":
            8,

        "l25_sequence_scenarios_flagged": 1,

        "l25_motion_flag_counts_by_threshold_m": {
            t: sum(
                x[
                    "scripted_motion_review_at_threshold_m"
                ][t]
                for x in items
            )
            for t in THRESHOLDS
        },

        "no_observed_reaction_scenarios_by_threshold_m":
            no_reaction,

        "point_storage_reordering_is_not_a_sensor_failure":
            True,

        "motion_thresholds_are_uncalibrated": True,

        "change_in_warning_is_not_detection_success":
            True,
    }


def evidence_ledger(l16, l19, l23, l24, l25):
    assert l16[
        "kinematic_usd_is_independent_ground_truth"
    ] is False

    assert l19[
        "physical_emitter_identity_verified"
    ] is False

    assert l23[
        "thresholds_scientifically_calibrated"
    ] is False

    assert l23["false_positive_rate_estimated"] is False
    assert l23["false_negative_rate_estimated"] is False

    assert l24[
        "independent_source_authenticity_verified"
    ] is False

    assert l24["physical_exposure_sync_verified"] is False
    assert l25["physical_exposure_sync_verified"] is False

    assert l25[
        "sensor_failure_detection_validated"
    ] is False

    assert l25[
        "stored_capture_hash_is_not_live_sensor_authenticity"
    ] is True

    assert l25[
        "scripted_usd_motion_is_not_independent_ground_truth"
    ] is True

    assert l25["health_labels_generated"] == 0

    # UNQUALIFIED: reports explicitly deny qualification.
    # NOT_EVIDENCED: reviewed reports lack admissible proof.
    # Neither means the wider project can never satisfy it.
    ledger = {
        "physical_correspondence_validation": (
            "UNQUALIFIED",
            "Inferred beam indices are not verified physical surface matches",
        ),

        "qualified_exposure_synchronization": (
            "UNQUALIFIED",
            "L24/L25 explicitly deny verified physical exposure synchronization",
        ),

        "calibrated_factor_uncertainty": (
            "NOT_EVIDENCED",
            "Deterministic perturbation tests do not establish calibrated factor covariance",
        ),

        "verified_extrinsic_transform": (
            "NOT_EVIDENCED",
            "No admissible cross-sensor extrinsic certification in reviewed reports",
        ),

        "independent_6dof_reference": (
            "UNQUALIFIED",
            "Scripted USD motion is not an independent reference",
        ),

        "heldout_6dof_accuracy_evaluation": (
            "NOT_EVIDENCED",
            "No independent held-out 6DoF accuracy evaluation in reviewed evidence",
        ),

        "adjudicated_sensor_failure_labels": (
            "UNQUALIFIED",
            "Synthetic perturbations are not adjudicated physical health labels",
        ),

        "independent_source_authenticity": (
            "UNQUALIFIED",
            "Local recording hashes are not independently attested source provenance",
        ),

        "validated_detection_error_rates": (
            "UNQUALIFIED",
            "False-positive and false-negative rates have not been estimated",
        ),

        "trusted_hardware_exposure_time": (
            "UNQUALIFIED",
            "Read-step times and GMO timestamps are not qualified exposure times",
        ),

        "independently_verified_replay_monitor": (
            "NOT_EVIDENCED",
            "Sequence-only freshness checks have demonstrated blind spots",
        ),
    }

    required = {
        name
        for names in GATES.values()
        for name in names
    }

    assert set(ledger) == required

    return [
        {
            "requirement": name,
            "status": status,
            "reason": reason,

            "not_proven_for_entire_project":
                status == "NOT_EVIDENCED",
        }
        for name, (status, reason)
        in sorted(ledger.items())
    ]


def gate(ledger, gate_name, user_claims=None):
    evidence = {
        row["requirement"]: row["status"]
        for row in ledger
    }

    if gate_name not in GATES:
        return {
            "gate": gate_name,
            "decision": "DENIED_UNKNOWN_GATE",
            "missing_requirements": [],
            "ignored_untrusted_claims":
                bool(user_claims),
            "factor_authorized": False,
        }

    missing = [
        name
        for name in GATES[gate_name]
        if evidence[name] != "INDEPENDENTLY_QUALIFIED"
    ]

    # This is a diagnostic readiness veto, not
    # an estimator-side admission implementation.
    assert missing

    return {
        "gate": gate_name,

        "decision":
            "DENIED_INSUFFICIENT_EVIDENCE",

        "missing_requirements": missing,

        "ignored_untrusted_claims":
            bool(user_claims),

        "factor_authorized": False,
    }


def challenges(ledger):
    attempts = []

    for name in GATES:
        attempts.append({
            "challenge": "baseline_" + name,
            "result": gate(ledger, name),
        })

    claimsets = [
        (
            "forged_independent_pose",
            "scientific_6dof_accuracy_claim",
            {"independent_6dof_reference": True},
        ),

        (
            "usd_as_ground_truth",
            "scientific_6dof_accuracy_claim",
            {"usd_is_independent_ground_truth": True},
        ),

        (
            "rehashed_payload_as_authenticity",
            "live_sensor_freshness_admission",
            {"independent_source_authenticity": True},
        ),

        (
            "read_step_as_exposure",
            "live_sensor_freshness_admission",
            {"trusted_hardware_exposure_time": True},
        ),

        (
            "unflagged_pair_as_factor",
            "lidar_pose_factor_admission",
            {"screen_not_flagged": True},
        ),

        (
            "synthetic_fault_as_health_label",
            "supervised_sensor_health_labels",
            {"synthetic_fault_label": True},
        ),
    ]

    for name, target, claims in claimsets:
        attempts.append({
            "challenge": name,
            "result": gate(ledger, target, claims),
        })

    attempts.append({
        "challenge": "unknown_policy",

        "result": gate(
            ledger,
            "unrecognized_request",
            {"accept": True},
        ),
    })

    assert len(attempts) == 11

    assert all(
        x["result"]["decision"].startswith("DENIED_")
        for x in attempts
    )

    assert all(
        x["result"]["factor_authorized"] is False
        for x in attempts
    )

    return attempts


def main():
    parser = argparse.ArgumentParser()

    for name in (
        "l16", "l19", "l20", "l23",
        "l24", "l25", "s23", "s24",
        "s25", "out",
    ):
        parser.add_argument(
            "--" + name,
            required=True,
            type=Path,
        )

    args = parser.parse_args()

    assert args.out.is_dir()
    assert not args.out.is_symlink()

    r16, r19, r20, r23, r24, r25 = [
        read(getattr(args, name))
        for name in (
            "l16", "l19", "l20",
            "l23", "l24", "l25",
        )
    ]

    assert r23["implementation_sha256"] == (
        sha(args.s23)
    )

    assert r24["implementation_sha256"] == (
        sha(args.s24)
    )

    assert r25["implementation_sha256"] == (
        sha(args.s25)
    )

    assert r23["upstream_sha256"]["l19"] == (
        sha(args.l19)
    )

    assert r23["upstream_sha256"]["l20"] == (
        sha(args.l20)
    )

    assert r25["upstream_report_sha256"]["l23"] == (
        sha(args.l23)
    )

    assert r25["upstream_report_sha256"]["l24"] == (
        sha(args.l24)
    )

    assert r25["reused_source_sha256"]["l23"] == (
        sha(args.s23)
    )

    assert r25["reused_source_sha256"]["l24"] == (
        sha(args.s24)
    )

    for document in (
        r16, r19, r20, r23, r24, r25
    ):
        assert document[
            "pose_factors_authorized"
        ] == 0

    assert r23["total_pair_trials"] == 110
    assert r23["decision_changes"] == 5

    assert r24["challenge_count"] == 11

    assert r25["scenario_count"] == 11
    assert r25["two_derivations_identical"] is True

    comparison = summarize(
        r23, r24, r25
    )

    ledger = evidence_ledger(
        r16, r19, r23, r24, r25
    )

    decisions = [
        gate(ledger, name)
        for name in GATES
    ]

    tests = challenges(ledger)

    content = {
        "scenario_analysis": comparison,
        "requirements": ledger,
        "readiness_decisions": decisions,

        "adversarial_promotion_challenges":
            tests,
    }

    # Deterministically rederive the entire result.
    repeat = {
        "scenario_analysis":
            summarize(r23, r24, r25),

        "requirements":
            evidence_ledger(
                r16, r19, r23, r24, r25
            ),

        "readiness_decisions": [
            gate(ledger, name)
            for name in GATES
        ],

        "adversarial_promotion_challenges":
            challenges(ledger),
    }

    assert stable(content) == stable(repeat)

    report = {
        "schema":
            "TRUST_ROBOT_L26_EVIDENCE_READINESS_AND_COMMON_MODE_GAP_AUDIT_V1",

        "implementation_sha256":
            sha(Path(__file__)),

        "upstream_sha256": {
            name: sha(getattr(args, name))
            for name in (
                "l16", "l19", "l20",
                "l23", "l24", "l25",
            )
        },

        "source_sha256": {
            name: sha(getattr(args, name))
            for name in ("s23", "s24", "s25")
        },

        "observed_evidence_only_no_real_time_qualification":
            True,

        "diagnostic_gate_is_not_estimator_integration":
            True,

        "hash_mismatch_does_not_prove_sensor_fault":
            True,

        "unflagged_does_not_mean_healthy_or_accurate":
            True,

        "full_6dof_ground_truth_available": False,
        "independent_exposure_sync_verified": False,

        "supervised_health_labels_generated": 0,
        "pose_factors_authorized": 0,

        "two_derivations_identical": True,

        **content,
    }

    destination = (
        args.out
        / "l26_evidence_readiness_report_v1.json"
    )

    with destination.open("x") as file:
        json.dump(
            report,
            file,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        file.write("\n")

    for row in decisions:
        print(
            "L26_READINESS_GATE=",
            json.dumps(
                row, sort_keys=True
            ),
            flush=True,
        )

    for threshold, names in comparison[
        "no_observed_reaction_scenarios_by_threshold_m"
    ].items():
        print(
            "L26_UNREACTED_AT_THRESHOLD=",
            json.dumps({
                "threshold_m": threshold,
                "scenarios": names,
            }, sort_keys=True),
            flush=True,
        )

    print("L26_CHALLENGE_COUNT=", len(tests))

    print(
        "L26_INDEPENDENT_REQUIREMENTS_QUALIFIED=",
        sum(
            row["status"] == "INDEPENDENTLY_QUALIFIED"
            for row in ledger
        ),
    )

    print("L26_SCENARIO_CROSSCHECK=PASS")
    print("L26_EVIDENCE_POLICY_NEGATIVE_CONTROLS=PASS")
    print("L26_EVIDENCE_READINESS_AUDIT=PASS")
    print("L26_REPORT_SHA256=", sha(destination))


if __name__ == "__main__":
    main()
