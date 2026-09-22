from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import ast
import json
import math
import unittest

from trust_robot.diagnostics import (
    DiagnosticFeatureError,
    LIDAR_REGISTRATION_EXTRACTOR_ID,
    LIDAR_REGISTRATION_FEATURE_ORDER,
    LIDAR_REGISTRATION_FEATURE_UNITS,
    build_diagnostic_feature_manifest,
    extract_lidar_registration_diagnostics,
)
from trust_robot.lidar_frontend import (
    LidarRegistrationDiagnostics,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase4_lidar_registration_diagnostics_candidate_v1.json"
)

PHASE_PLAN = (
    ROOT
    / "docs/TRUST_ROBOT_PHASE_PLAN.md"
)

MODULE = (
    ROOT
    / "src/trust_robot/diagnostics.py"
)


def diagnostic():
    return LidarRegistrationDiagnostics(
        source_point_count=
            1200,

        target_point_count=
            1250,

        fixed_point_iterations=
            17,

        final_correspondence_count=
            1200,

        final_nearest_neighbor_rmse_m=
            0.25,

        convergence_rule=
            "exact_nearest_neighbor_assignment_unchanged",

        correspondence_rejection_used=
            False,

        voxel_downsampling_used=
            False,
    )


class Phase4LidarRegistrationDiagnosticTests(
    unittest.TestCase
):
    def test_01_config_digest_and_phase_plan_are_exact(self):
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
            ).encode(
                "utf-8"
            )
        ).hexdigest()

        self.assertEqual(
            stored,
            actual,
        )

        self.assertEqual(
            payload[
                "phase"
            ][
                "objective"
            ],
            "Per-modality diagnostics",
        )

        self.assertEqual(
            payload[
                "phase"
            ][
                "exit_evidence"
            ],
            "Validated diagnostic feature extraction",
        )

        self.assertFalse(
            payload[
                "phase"
            ][
                "exit_evidence_satisfied"
            ]
        )

        self.assertIn(
            (
                "| 4 | Per-modality diagnostics | "
                "Validated diagnostic feature extraction |"
            ),
            PHASE_PLAN.read_text(
                encoding="utf-8"
            ),
        )

    def test_02_feature_order_is_explicit_and_stable(self):
        self.assertEqual(
            LIDAR_REGISTRATION_FEATURE_ORDER,
            (
                "source_point_count",
                "target_point_count",
                "fixed_point_iterations",
                "final_correspondence_count",
                "final_nearest_neighbor_rmse_m",
            ),
        )

    def test_03_feature_units_are_explicit_and_stable(self):
        self.assertEqual(
            LIDAR_REGISTRATION_FEATURE_UNITS,
            (
                "count",
                "count",
                "count",
                "count",
                "m",
            ),
        )

    def test_04_extraction_is_direct_and_value_preserving(self):
        record = extract_lidar_registration_diagnostics(
            diagnostic()
        )

        self.assertEqual(
            record.extractor_id,
            LIDAR_REGISTRATION_EXTRACTOR_ID,
        )

        self.assertEqual(
            record.feature_names,
            LIDAR_REGISTRATION_FEATURE_ORDER,
        )

        self.assertEqual(
            record.numeric_values,
            (
                1200.0,
                1250.0,
                17.0,
                1200.0,
                0.25,
            ),
        )

    def test_05_categorical_semantics_are_preserved_as_metadata(self):
        record = extract_lidar_registration_diagnostics(
            diagnostic()
        )

        self.assertEqual(
            dict(
                record.metadata
            ),
            {
                "convergence_rule":
                    "exact_nearest_neighbor_assignment_unchanged",

                "correspondence_rejection_used":
                    False,

                "voxel_downsampling_used":
                    False,
            },
        )

    def test_06_record_fingerprint_is_deterministic(self):
        first = extract_lidar_registration_diagnostics(
            diagnostic()
        )

        second = extract_lidar_registration_diagnostics(
            diagnostic()
        )

        self.assertEqual(
            first.fingerprint_sha256,
            second.fingerprint_sha256,
        )

    def test_07_manifest_is_deterministic(self):
        record = extract_lidar_registration_diagnostics(
            diagnostic()
        )

        first = build_diagnostic_feature_manifest(
            (
                record,
                record,
            )
        )

        second = build_diagnostic_feature_manifest(
            (
                record,
                record,
            )
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            first[
                "record_count"
            ],
            2,
        )

    def test_08_invalid_count_values_are_rejected(self):
        for field_name, value in (
            (
                "source_point_count",
                0,
            ),
            (
                "target_point_count",
                -1,
            ),
            (
                "fixed_point_iterations",
                0,
            ),
            (
                "final_correspondence_count",
                0,
            ),
        ):
            with self.subTest(
                field_name=field_name
            ):
                with self.assertRaises(
                    DiagnosticFeatureError
                ):
                    extract_lidar_registration_diagnostics(
                        replace(
                            diagnostic(),
                            **{
                                field_name:
                                    value
                            },
                        )
                    )

    def test_09_nonfinite_or_negative_rmse_is_rejected(self):
        for value in (
            float(
                "nan"
            ),
            float(
                "inf"
            ),
            -0.01,
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    DiagnosticFeatureError
                ):
                    extract_lidar_registration_diagnostics(
                        replace(
                            diagnostic(),
                            final_nearest_neighbor_rmse_m=
                                value,
                        )
                    )

    def test_10_correspondence_count_must_match_frozen_no_rejection_semantics(self):
        with self.assertRaises(
            DiagnosticFeatureError
        ):
            extract_lidar_registration_diagnostics(
                replace(
                    diagnostic(),
                    final_correspondence_count=
                        1199,
                )
            )

    def test_11_wrong_convergence_rule_is_rejected(self):
        with self.assertRaises(
            DiagnosticFeatureError
        ):
            extract_lidar_registration_diagnostics(
                replace(
                    diagnostic(),
                    convergence_rule=
                        "numeric_tolerance",
                )
            )

    def test_12_rejection_or_downsampling_semantic_change_is_rejected(self):
        for field_name in (
            "correspondence_rejection_used",
            "voxel_downsampling_used",
        ):
            with self.subTest(
                field_name=field_name
            ):
                with self.assertRaises(
                    DiagnosticFeatureError
                ):
                    extract_lidar_registration_diagnostics(
                        replace(
                            diagnostic(),
                            **{
                                field_name:
                                    True
                            },
                        )
                    )

    def test_13_extractor_emits_no_health_fault_threshold_or_accuracy_decision(self):
        record = extract_lidar_registration_diagnostics(
            diagnostic()
        )

        payload = record.to_dict()

        scope = payload[
            "scientific_scope"
        ]

        for key in (
            "normalization_applied",
            "window_aggregation_applied",
            "threshold_applied",
            "health_label_emitted",
            "fault_label_emitted",
            "reliability_score_emitted",
            "accuracy_score_emitted",
            "reference_data_used",
            "confirmation_test_data_used",
            "ate_computed",
            "rpe_computed",
        ):
            self.assertFalse(
                scope[
                    key
                ]
            )

    def test_14_no_historical_reliability_or_evaluation_runtime_dependency(self):
        source = MODULE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(
                MODULE
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

        forbidden = (
            "imu_reliability",
            "evaluation",
            "readiness",
            "reference",
            "evo",
        )

        for imported in modules:
            self.assertFalse(
                any(
                    token
                    in imported.lower()
                    for token
                    in forbidden
                ),
                imported,
            )

        lidar_imports = set()

        for node in ast.walk(
            tree
        ):
            if (
                isinstance(
                    node,
                    ast.ImportFrom,
                )
                and node.module
                == "lidar_frontend"
            ):
                lidar_imports.update(
                    alias.name
                    for alias
                    in node.names
                )

        self.assertEqual(
            lidar_imports,
            {
                "LidarRegistrationDiagnostics",
            },
        )


if __name__ == "__main__":
    unittest.main()
