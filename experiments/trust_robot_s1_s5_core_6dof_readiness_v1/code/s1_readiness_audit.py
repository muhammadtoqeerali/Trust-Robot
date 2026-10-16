"""S1 fixed-estimator and M2DGR scientific readiness audit.

Metadata and Python source inspection only.
No trajectory scoring, estimator execution or raw sensor access.
"""

import argparse
import ast
import collections
import hashlib
import importlib.util
import json
import platform
from pathlib import Path

MODULES = (
    "analytic_inertial_15d",
    "analytic_imu_preintegration",
    "analytic_schur_marginalization",
    "analytic_marginalized_fusion",
    "analytic_marginalized_support",
    "analytic_marginalized_horizon",
    "analytic_marginalization_consistency",
    "analytic_preintegrated_fusion",
    "analytic_factor_support",
    "analytic_estimator_robustness",
    "analytic_three_modality_bridge",
    "multimodal_factor_interface",
    "visual_sparse_correspondence",
    "visual_two_view_geometry",
    "m2dgr_evaluator_gate",
    "se4_health_model_training_resolution",
)

SOURCES = (
    "manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json",
    "configs/trust_robot/m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json",
    "manifests/m2dgr_reference_family_protocol_boundary_evidence_v1.json",
    "manifests/trust_robot_se4_health_model_training_blocked_frontier_freeze_v1.json",
    "docs/audits/trust_robot/TRUST_ROBOT_FIXED_LAG_ESTIMATOR_VALIDITY_CHECKPOINT_V1.md",
    "docs/audits/trust_robot/M2DGR_EVALUATOR_FAIL_CLOSED_ARCHITECTURE_V1.md",
    "docs/audits/trust_robot/TRUST_ROBOT_SE4_HEALTH_MODEL_TRAINING_BLOCKED_FRONTIER_FREEZE_V1.md",
)

PARENT = "79a2abf6de6ff68df23de8bd04b538ce0c95b46b"


def need(ok, reason):
    if not ok:
        raise ValueError("S1_INVALID:" + reason)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def safe(root, relative):
    p = root / relative

    need(
        p.is_file()
        and not p.is_symlink()
        and p.stat().st_size < 5000000,
        "SOURCE_FILE:" + relative,
    )

    return p


def load(root, relative):
    return json.loads(safe(root, relative).read_text())


def assess(root):
    split = load(root, SOURCES[0])
    protocol = load(root, SOURCES[1])
    reference = load(root, SOURCES[2])
    health = load(root, SOURCES[3])

    trajectories = split["records"]

    need(
        len(trajectories) == 36,
        "M2DGR_TRAJECTORY_COUNT",
    )

    counts = dict(
        collections.Counter(
            x["split"] for x in trajectories
        )
    )

    need(
        counts == {
            "train": 22,
            "validation_calibration": 7,
            "confirmation_test": 7,
        },
        "FROZEN_SPLIT",
    )

    identities = [
        x["base_trajectory_id"]
        for x in trajectories
    ]

    need(
        len(set(identities)) == 36,
        "TRAJECTORY_DUPLICATION",
    )

    sync = [
        item
        for record in trajectories
        for item in record["synchronization"]
    ]

    need(
        len(sync) == 140,
        "SYNC_ENTRY_COUNT",
    )

    need(
        all(
            item["verification_status"] == "unverified"
            and item["fixed_offset_seconds"] is None
            and item["tolerance_seconds"] is None
            for item in sync
        ),
        "SYNCHRONIZATION_PREMATURE_PROMOTION",
    )

    overlap = [
        (rec["base_trajectory_id"], x["stream_id"])
        for rec in trajectories
        for x in rec["streams"]
        if x["estimator_input"] and x["reference_only"]
    ]

    need(
        not overlap,
        "REFERENCE_INPUT_LEAKAGE",
    )

    auth = protocol["authorization"]

    need(
        protocol["status"]
        == "blocked_pending_physical_evidence",
        "PROTOCOL_STATUS",
    )

    for flag in (
        "association_execution_authorized",
        "alignment_execution_authorized",
        "estimator_scoring_authorized",
        "evaluation_ready",
        "dataset_calibration_verified",
        "evaluation_interval_authorized",
    ):
        need(
            auth[flag] is False,
            "UNQUALIFIED_PROTOCOL:" + flag,
        )

    need(
        auth["confirmation_test_partition_closed"] is True,
        "CONFIRMATION_ACCESS_GATE",
    )

    need(
        protocol["temporal_association"]["selected_method"]
        == "unselected"
        and protocol["frame_alignment"]["selected_mode"]
        == "unselected",
        "UNSELECTED_ASSOCIATION",
    )

    boundary = reference["protocol_boundary_conclusion"]

    need(
        boundary["any_reference_family_ate_or_rpe_admissible_now"]
        is False
        and boundary["dimension_gating_definition_admissible"]
        is True,
        "REFERENCE_EVALUATION_GATE",
    )

    state = health["supervision_state"]
    model = health["model_state"]

    need(
        health["stage"]["SE4_complete"] is False
        and state["accepted_health_supervision_source_count"] == 0
        and state["real_health_label_count"] == 0
        and state["empirical_health_supervision_available"]
        is False,
        "HEALTH_SUPERVISION",
    )

    need(
        model["classifier_training_authorized"] is False
        and model["model_training_executed"] is False
        and model["health_inference_authorized"] is False,
        "HEALTH_MODEL_TRAINING",
    )

    inventory = []
    hashes = {}

    for relative in SOURCES:
        hashes[relative] = digest(
            safe(root, relative)
        )

    for name in MODULES:
        source = "src/trust_robot/" + name + ".py"
        test = (
            "tests/trust_robot/test_" + name + ".py"
        )

        p = safe(root, source)
        t = safe(root, test)

        tree = ast.parse(
            p.read_text(encoding="utf-8")
        )

        ast.parse(
            t.read_text(encoding="utf-8")
        )

        definitions = [
            node.name
            for node in tree.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                ),
            )
        ]

        inventory.append({
            "module": name,
            "source": source,
            "test": test,
            "source_sha256": digest(p),
            "test_sha256": digest(t),
            "top_level_definitions": definitions,
            "source_syntax_checked": True,
            "test_syntax_checked": True,
            "unit_test_executed_in_s1": False,
            "real_sensor_qualified_in_s1": False,
        })

        hashes[source] = digest(p)
        hashes[test] = digest(t)

    dependencies = {
        name: (
            importlib.util.find_spec(name) is not None
        )
        for name in (
            "numpy",
            "scipy",
            "pytest",
        )
    }

    return {
        "schema":
            "TRUST_ROBOT_S1_CORE_6DOF_READINESS_AUDIT_V1",
        "parent_commit": PARENT,
        "audit_source_sha256": digest(
            Path(__file__)
        ),
        "m2dgr_trajectory_count": len(trajectories),
        "m2dgr_split_counts": counts,
        "m2dgr_sync_entries": len(sync),
        "m2dgr_sync_qualified": 0,
        "m2dgr_estimator_scoring_authorized": False,
        "m2dgr_reference_family_scoring_admissible": False,
        "m2dgr_confirmation_closed_to_selection": True,
        "m2dgr_dataset_calibration_verified": False,
        "m2dgr_reference_input_overlap": 0,
        "se4_real_health_labels": 0,
        "se4_training_authorized": False,
        "analytic_implementation_inventory": inventory,
        "analytic_module_count": len(inventory),
        "environment": {
            "python": platform.python_version(),
            "available_packages": dependencies,
        },
        "frozen_source_sha256": hashes,
        "scientific_decision":
            "REUSE_ANALYTIC_ESTIMATOR_BUT_REAL_SENSOR_FACTORS_BLOCKED",
        "recommended_next_actions": [
            "Run controlled existing estimator regression tests in a validated CPU environment",
            "Inspect the existing recorded-source factor-admission interface",
            "Define the narrowest train-only sensor-backed factor integration contract that preserves timing and calibration uncertainty",
            "Do not activate M2DGR scoring or empirical health training without new qualified evidence",
        ],
        "raw_bag_read": False,
        "confirmation_sensor_data_read": False,
        "estimator_executed": False,
        "scientific_metrics_computed": False,
        "real_sensor_pose_factors_authorized": 0,
        "health_labels_generated": 0,
        "live_simulator_launch_authorized": False,
        "git_modified": False,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo", required=True
    )
    parser.add_argument(
        "--report", required=True
    )

    args = parser.parse_args()

    report = assess(
        Path(args.repo)
    )

    with Path(args.report).open(
        "x",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")

    print("S1_M2DGR_TRAJECTORIES=36")
    print("S1_FROZEN_SPLIT=22_TRAIN_7_VALIDATION_7_CONFIRMATION")
    print("S1_UNQUALIFIED_SYNC_ENTRIES=140")
    print(
        "S1_ANALYTIC_MODULE_AND_TEST_PAIRS="
        f"{report['analytic_module_count']}_SYNTAX_VERIFIED"
    )
    print(
        "S1_PYTHON_PACKAGES="
        + json.dumps(
            report["environment"]["available_packages"],
            sort_keys=True,
        )
    )
    print("S1_M2DGR_ESTIMATOR_SCORING=BLOCKED")
    print("S1_HEALTH_MODEL_TRAINING=BLOCKED")
    print("S1_READ_ONLY_SCIENCE_AUDIT=PASS")


if __name__ == "__main__":
    main()
