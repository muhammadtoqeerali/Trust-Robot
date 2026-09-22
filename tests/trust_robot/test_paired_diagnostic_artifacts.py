from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import ast
import json
import unittest

from trust_robot.paired_diagnostic_artifacts import (
    PairedDiagnosticArtifactError,
    build_phase3_paired_diagnostic_artifact,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase4_lidar_paired_diagnostics_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/paired_diagnostic_artifacts.py"
)

RUNNER = (
    ROOT
    / "scripts/trust_robot/run_phase4_lidar_paired_diagnostics_v1.py"
)


def canonical_sha(
    payload,
):
    value = dict(
        payload
    )

    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def diagnostics(
    source_count,
    target_count,
    iterations,
    rmse,
):
    return {
        "source_point_count":
            source_count,

        "target_point_count":
            target_count,

        "fixed_point_iterations":
            iterations,

        "final_correspondence_count":
            source_count,

        "final_nearest_neighbor_rmse_m":
            rmse,

        "convergence_rule":
            "exact_nearest_neighbor_assignment_unchanged",

        "correspondence_rejection_used":
            False,

        "voxel_downsampling_used":
            False,

        "interpretation":
            "execution_diagnostic_only_not_accuracy_score",
    }


def registration_record(
    pair_index,
    previous_origin,
    current_origin,
    previous_timestamp,
    current_timestamp,
    diagnostic,
):
    return {
        "pair_index":
            pair_index,

        "previous_event_index":
            pair_index,

        "current_event_index":
            pair_index + 1,

        "previous_clean_origin_index":
            previous_origin,

        "current_clean_origin_index":
            current_origin,

        "previous_timestamp_ns":
            previous_timestamp,

        "current_timestamp_ns":
            current_timestamp,

        "previous_xyz_sha256":
            "a" * 64,

        "current_xyz_sha256":
            "b" * 64,

        "previous_lidar_T_current_lidar": {
            "translation_m":
                [0.0, 0.0, 0.0],

            "quaternion_wxyz":
                [1.0, 0.0, 0.0, 0.0],
        },

        "diagnostics":
            diagnostic,
    }


def receipt():
    spec_id = (
        "TRC_SPEC_d7fdcb5f67999476d8f0391d"
    )

    injection_id = (
        "TRC_INJ_2413029fc605422de2dd737f"
    )

    clean_records = [
        registration_record(
            0,
            0,
            1,
            100,
            200,
            diagnostics(
                1000,
                1010,
                10,
                0.20,
            ),
        ),
        registration_record(
            1,
            1,
            2,
            200,
            300,
            diagnostics(
                1010,
                1020,
                11,
                0.21,
            ),
        ),
    ]

    corrupt_records = [
        registration_record(
            0,
            0,
            2,
            100,
            300,
            diagnostics(
                1000,
                1020,
                14,
                0.30,
            ),
        ),
    ]

    payload = {
        "schema":
            "TRUST_ROBOT_PHASE3_LIDAR_PAIRED_ESTIMATOR_REGISTRATION_RECEIPT_V1",

        "schema_version":
            1,

        "status":
            "completed",

        "source": {
            "dataset_id":
                "M2DGR",

            "split":
                "train",

            "trajectory":
                "Circle_01",

            "topic":
                "/velodyne_points",

            "event_slice":
                "first_three_velodyne_messages_in_bag_order",
        },

        "corruption": {
            "family":
                "EVENT_GAP",

            "spec_id":
                spec_id,

            "injection_id":
                injection_id,

            "clean_origin_indices":
                [0, 1, 2],

            "corrupt_origin_indices":
                [0, 2],
        },

        "registration_execution": {
            "schema":
                "TRUST_ROBOT_PHASE3_PAIRED_FROZEN_LIDAR_REGISTRATION_V1",

            "clean": {
                "schema":
                    "TRUST_ROBOT_PHASE3_FROZEN_LIDAR_REGISTRATION_PATH_V1",

                "modality":
                    "lidar",

                "source_id":
                    "/velodyne_points",

                "event_count":
                    3,

                "increment_count":
                    2,

                "origin_pairs":
                    [[0, 1], [1, 2]],

                "records":
                    clean_records,
            },

            "corrupt": {
                "schema":
                    "TRUST_ROBOT_PHASE3_FROZEN_LIDAR_REGISTRATION_PATH_V1",

                "modality":
                    "lidar",

                "source_id":
                    "/velodyne_points",

                "event_count":
                    2,

                "increment_count":
                    1,

                "origin_pairs":
                    [[0, 2]],

                "records":
                    corrupt_records,
            },

            "corruption_spec_ids":
                [spec_id],

            "corruption_injection_ids":
                [injection_id],

            "path_topology": {
                "clean_origin_pairs":
                    [[0, 1], [1, 2]],

                "corrupt_origin_pairs":
                    [[0, 2]],

                "registration_path_changed_by_corruption":
                    True,
            },
        },

        "determinism": {
            "paired_execution_repeated_exactly":
                True,

            "clean_stream_unchanged":
                True,

            "corrupt_stream_unchanged":
                True,
        },

        "interpretation": {
            "mechanical_estimator_input_path_proof":
                True,

            "localization_accuracy_comparison":
                False,

            "clean_corrupt_error_metric":
                None,

            "observed_output_may_modify_corruption_spec":
                False,

            "observed_output_may_select_future_severity":
                False,
        },

        "scientific_scope": {
            "real_train_data_used":
                True,

            "controlled_corruption_used":
                True,

            "frozen_phase2_registration_kernel_used":
                True,

            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "ground_truth_association_performed":
                False,

            "alignment_performed":
                False,

            "ate_computed":
                False,

            "rpe_computed":
                False,

            "trajectory_scoring_performed":
                False,

            "estimator_scoring_performed":
                False,

            "accuracy_comparison_performed":
                False,

            "severity_selection_performed":
                False,

            "phase3_exit_evidence_satisfied":
                False,
        },
    }

    payload[
        "content_sha256"
    ] = canonical_sha(
        payload
    )

    return payload


class Phase4PairedDiagnosticArtifactTests(
    unittest.TestCase
):
    def test_01_config_digest_and_source_binding_are_exact(self):
        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        stored = payload.pop(
            "content_sha256"
        )

        self.assertEqual(
            stored,
            canonical_sha(
                payload
            ),
        )

        self.assertEqual(
            payload[
                "source"
            ][
                "file_sha256"
            ],
            "2ac381057b5a1c05cc9164ad8f7d7c4e4f81ad1d7d196eb78b97e3f340eaf2c2",
        )

    def test_02_clean_and_corrupt_topology_are_preserved(self):
        artifact = build_phase3_paired_diagnostic_artifact(
            receipt()
        )

        self.assertEqual(
            artifact[
                "clean"
            ][
                "origin_pairs"
            ],
            [[0, 1], [1, 2]],
        )

        self.assertEqual(
            artifact[
                "corrupt"
            ][
                "origin_pairs"
            ],
            [[0, 2]],
        )

    def test_03_record_counts_are_two_clean_one_corrupt(self):
        artifact = build_phase3_paired_diagnostic_artifact(
            receipt()
        )

        self.assertEqual(
            artifact[
                "clean"
            ][
                "registration_count"
            ],
            2,
        )

        self.assertEqual(
            artifact[
                "corrupt"
            ][
                "registration_count"
            ],
            1,
        )

    def test_04_clean_feature_values_are_direct(self):
        artifact = build_phase3_paired_diagnostic_artifact(
            receipt()
        )

        features = artifact[
            "clean"
        ][
            "records"
        ][
            0
        ][
            "feature_record"
        ][
            "features"
        ]

        self.assertEqual(
            [
                feature[
                    "value"
                ]
                for feature
                in features
            ],
            [
                1000,
                1010,
                10,
                1000,
                0.20,
            ],
        )

    def test_05_corrupt_feature_values_are_direct(self):
        artifact = build_phase3_paired_diagnostic_artifact(
            receipt()
        )

        features = artifact[
            "corrupt"
        ][
            "records"
        ][
            0
        ][
            "feature_record"
        ][
            "features"
        ]

        self.assertEqual(
            [
                feature[
                    "value"
                ]
                for feature
                in features
            ],
            [
                1000,
                1020,
                14,
                1000,
                0.30,
            ],
        )

    def test_06_artifact_is_exactly_deterministic(self):
        first = build_phase3_paired_diagnostic_artifact(
            receipt()
        )

        second = build_phase3_paired_diagnostic_artifact(
            receipt()
        )

        self.assertEqual(
            first,
            second,
        )

    def test_07_corruption_identity_is_preserved(self):
        artifact = build_phase3_paired_diagnostic_artifact(
            receipt()
        )

        self.assertEqual(
            artifact[
                "corruption"
            ][
                "spec_id"
            ],
            "TRC_SPEC_d7fdcb5f67999476d8f0391d",
        )

        self.assertEqual(
            artifact[
                "corruption"
            ][
                "injection_id"
            ],
            "TRC_INJ_2413029fc605422de2dd737f",
        )

    def test_08_source_receipt_digest_tampering_is_rejected(self):
        payload = receipt()

        payload[
            "content_sha256"
        ] = "0" * 64

        with self.assertRaises(
            PairedDiagnosticArtifactError
        ):
            build_phase3_paired_diagnostic_artifact(
                payload
            )

    def test_09_topology_inconsistency_is_rejected(self):
        payload = receipt()

        payload[
            "registration_execution"
        ][
            "path_topology"
        ][
            "corrupt_origin_pairs"
        ] = [[0, 1]]

        payload[
            "content_sha256"
        ] = canonical_sha(
            payload
        )

        with self.assertRaises(
            PairedDiagnosticArtifactError
        ):
            build_phase3_paired_diagnostic_artifact(
                payload
            )

    def test_10_scoring_interpretation_is_rejected(self):
        payload = receipt()

        payload[
            "registration_execution"
        ][
            "corrupt"
        ][
            "records"
        ][
            0
        ][
            "diagnostics"
        ][
            "interpretation"
        ] = "accuracy_score"

        payload[
            "content_sha256"
        ] = canonical_sha(
            payload
        )

        with self.assertRaises(
            PairedDiagnosticArtifactError
        ):
            build_phase3_paired_diagnostic_artifact(
                payload
            )

    def test_11_reference_or_confirmation_scope_is_rejected(self):
        for key in (
            "reference_data_used",
            "confirmation_test_data_used",
        ):
            payload = receipt()

            payload[
                "scientific_scope"
            ][
                key
            ] = True

            payload[
                "content_sha256"
            ] = canonical_sha(
                payload
            )

            with self.subTest(
                key=key
            ):
                with self.assertRaises(
                    PairedDiagnosticArtifactError
                ):
                    build_phase3_paired_diagnostic_artifact(
                        payload
                    )

    def test_12_no_estimator_historical_or_health_runtime_dependency(self):
        for path in (
            MODULE,
            RUNNER,
        ):
            source = path.read_text(
                encoding="utf-8"
            )

            tree = ast.parse(
                source,
                filename=str(
                    path
                ),
            )

            modules = []

            for node in ast.walk(
                tree
            ):
                if isinstance(
                    node,
                    ast.Import,
                ):
                    modules.extend(
                        alias.name
                        for alias
                        in node.names
                    )

                elif isinstance(
                    node,
                    ast.ImportFrom,
                ):
                    modules.append(
                        node.module
                        or ""
                    )

            for forbidden in (
                "imu_reliability",
                "rosbags",
                "evaluation",
                "reference",
                "readiness",
                "evo",
            ):
                self.assertFalse(
                    any(
                        forbidden
                        in module.lower()
                        for module
                        in modules
                    ),
                    (
                        path,
                        forbidden,
                        modules,
                    ),
                )

            self.assertNotIn(
                "register_current_scan_to_previous",
                source,
            )


if __name__ == "__main__":
    unittest.main()
