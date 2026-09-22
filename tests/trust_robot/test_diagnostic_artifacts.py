from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import ast
import json
import unittest

from trust_robot.diagnostic_artifacts import (
    DiagnosticArtifactError,
    build_lidar_diagnostic_artifact_record,
    validate_lidar_diagnostic_artifact_record,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase4_lidar_train_diagnostic_artifacts_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/diagnostic_artifacts.py"
)

RUNNER = (
    ROOT
    / "scripts/trust_robot/"
      "run_phase4_lidar_train_diagnostics_v1.py"
)


def source_record():
    return {
        "record_type":
            "relative_pose",

        "trajectory":
            "Circle_01",

        "scan_index":
            1,

        "previous_header_stamp_ns":
            100,

        "current_header_stamp_ns":
            200,

        "header_delta_ns":
            100,

        "delta_prev_lidar_T_current_lidar":
            {
                "synthetic":
                    True
            },

        "state_world_T_lidar":
            {
                "synthetic":
                    True
            },

        "diagnostics": {
            "source_point_count":
                47106,

            "target_point_count":
                47084,

            "fixed_point_iterations":
                17,

            "final_correspondence_count":
                47106,

            "final_nearest_neighbor_rmse_m":
                0.3006665968085355,

            "convergence_rule":
                "exact_nearest_neighbor_assignment_unchanged",

            "correspondence_rejection_used":
                False,

            "voxel_downsampling_used":
                False,
        },

        "scientific_scope": {
            "reference_data_used":
                False,

            "confirmation_test_data_used":
                False,

            "scan_temporal_reference_verified":
                False,

            "per_point_time_used":
                False,

            "deskew_performed":
                False,

            "correspondence_rejection_used":
                False,

            "voxel_downsampling_used":
                False,

            "ate_computed":
                False,

            "rpe_computed":
                False,

            "trajectory_scoring_performed":
                False,
        },
    }


def raw_sha():
    raw = (
        json.dumps(
            source_record(),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    return sha256(raw).hexdigest()


class Phase4DiagnosticArtifactTests(
    unittest.TestCase
):
    def test_01_config_digest_and_preflight_identity_are_exact(self):
        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        stored = payload.pop(
            "content_sha256"
        )

        actual = sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()

        self.assertEqual(
            stored,
            actual,
        )

        self.assertEqual(
            payload[
                "preflight_binding"
            ][
                "expected_feature_extraction_aggregate_sha256"
            ],
            "42658bdb5739200f02dc1397f753b78ca60eb22f6bc5d913e42c6a208fc61020",
        )

    def test_02_valid_pair_record_extracts_exact_five_values(self):
        artifact = build_lidar_diagnostic_artifact_record(
            source_record(),
            source_line_number=2,
            source_raw_line_sha256=raw_sha(),
        )

        self.assertEqual(
            artifact[
                "feature_values"
            ],
            [
                47106,
                47084,
                17,
                47106,
                0.3006665968085355,
            ],
        )

        validate_lidar_diagnostic_artifact_record(
            artifact
        )

    def test_03_record_identity_is_deterministic(self):
        first = build_lidar_diagnostic_artifact_record(
            source_record(),
            source_line_number=2,
            source_raw_line_sha256=raw_sha(),
        )

        second = build_lidar_diagnostic_artifact_record(
            source_record(),
            source_line_number=2,
            source_raw_line_sha256=raw_sha(),
        )

        self.assertEqual(
            first,
            second,
        )

    def test_04_nonrelative_record_is_rejected(self):
        record = source_record()
        record[
            "record_type"
        ] = "trajectory_header"

        with self.assertRaises(
            DiagnosticArtifactError
        ):
            build_lidar_diagnostic_artifact_record(
                record,
                source_line_number=1,
                source_raw_line_sha256=raw_sha(),
            )

    def test_05_top_level_schema_change_is_rejected(self):
        record = source_record()
        record[
            "unexpected"
        ] = 1

        with self.assertRaises(
            DiagnosticArtifactError
        ):
            build_lidar_diagnostic_artifact_record(
                record,
                source_line_number=2,
                source_raw_line_sha256=raw_sha(),
            )

    def test_06_diagnostic_schema_change_is_rejected(self):
        record = source_record()
        del record[
            "diagnostics"
        ][
            "fixed_point_iterations"
        ]

        with self.assertRaises(
            DiagnosticArtifactError
        ):
            build_lidar_diagnostic_artifact_record(
                record,
                source_line_number=2,
                source_raw_line_sha256=raw_sha(),
            )

    def test_07_timestamp_delta_inconsistency_is_rejected(self):
        record = source_record()
        record[
            "header_delta_ns"
        ] = 99

        with self.assertRaises(
            DiagnosticArtifactError
        ):
            build_lidar_diagnostic_artifact_record(
                record,
                source_line_number=2,
                source_raw_line_sha256=raw_sha(),
            )

    def test_08_source_scientific_scope_true_is_rejected(self):
        record = source_record()
        record[
            "scientific_scope"
        ][
            "reference_data_used"
        ] = True

        with self.assertRaises(
            DiagnosticArtifactError
        ):
            build_lidar_diagnostic_artifact_record(
                record,
                source_line_number=2,
                source_raw_line_sha256=raw_sha(),
            )

    def test_09_invalid_raw_line_digest_is_rejected(self):
        with self.assertRaises(
            DiagnosticArtifactError
        ):
            build_lidar_diagnostic_artifact_record(
                source_record(),
                source_line_number=2,
                source_raw_line_sha256="not-a-sha",
            )

    def test_10_artifact_digest_tampering_is_rejected(self):
        artifact = build_lidar_diagnostic_artifact_record(
            source_record(),
            source_line_number=2,
            source_raw_line_sha256=raw_sha(),
        )

        artifact[
            "feature_values"
        ][
            2
        ] = 18

        with self.assertRaises(
            DiagnosticArtifactError
        ):
            validate_lidar_diagnostic_artifact_record(
                artifact
            )

    def test_11_artifact_emits_no_threshold_health_or_score(self):
        artifact = build_lidar_diagnostic_artifact_record(
            source_record(),
            source_line_number=2,
            source_raw_line_sha256=raw_sha(),
        )

        scope = artifact[
            "scientific_scope"
        ]

        for key in (
            "threshold_applied",
            "health_label_emitted",
            "fault_label_emitted",
            "reliability_score_emitted",
            "accuracy_score_emitted",
            "reference_data_used",
            "confirmation_test_data_used",
            "ate_computed",
            "rpe_computed",
            "estimator_scoring_performed",
        ):
            self.assertFalse(
                scope[
                    key
                ]
            )

    def test_12_module_and_runner_have_no_estimator_or_historical_runtime_dependency(self):
        module_source = MODULE.read_text(
            encoding="utf-8"
        )

        runner_source = RUNNER.read_text(
            encoding="utf-8"
        )

        for source, path in (
            (
                module_source,
                MODULE,
            ),
            (
                runner_source,
                RUNNER,
            ),
        ):
            tree = ast.parse(
                source,
                filename=str(path),
            )

            imported = []

            for node in ast.walk(
                tree
            ):
                if isinstance(
                    node,
                    ast.Import,
                ):
                    imported.extend(
                        item.name
                        for item
                        in node.names
                    )

                elif isinstance(
                    node,
                    ast.ImportFrom,
                ):
                    imported.append(
                        node.module
                        or ""
                    )

            for name in imported:
                lowered = name.lower()

                self.assertNotIn(
                    "imu_reliability",
                    lowered,
                )

                self.assertNotIn(
                    "evaluation",
                    lowered,
                )

                self.assertNotIn(
                    "reference",
                    lowered,
                )

            self.assertNotIn(
                "register_current_scan_to_previous",
                source,
            )

            self.assertNotIn(
                "AnyReader",
                source,
            )

            self.assertNotIn(
                "rosbags",
                source,
            )


if __name__ == "__main__":
    unittest.main()
