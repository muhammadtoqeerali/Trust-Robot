from pathlib import Path
import ast
import json
import unittest

import numpy as np

from trust_robot.corruption import (
    CorruptionSpec,
    EventStream,
    apply_corruption,
    build_pair_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase3_lidar_event_gap_real_smoke_v1.json"
)

SMOKE = (
    ROOT
    / "scripts/trust_robot/"
      "run_phase3_lidar_event_gap_real_smoke_v1.py"
)


def config():
    return json.loads(
        CONFIG.read_text(
            encoding="utf-8"
        )
    )


def synthetic_three_event_stream():
    return EventStream(
        modality=
            "lidar",

        source_id=
            "/velodyne_points",

        timestamps_ns=
            np.asarray(
                [
                    100,
                    200,
                    300,
                ],
                dtype=np.int64,
            ),

        payloads=(
            np.asarray(
                [
                    [0.0, 0.0, 0.0],
                    [1.0, 0.0, 0.0],
                    [2.0, 0.0, 0.0],
                ],
                dtype=np.float64,
            ),

            np.asarray(
                [
                    [0.1, 0.0, 0.0],
                    [1.1, 0.0, 0.0],
                    [2.1, 0.0, 0.0],
                ],
                dtype=np.float64,
            ),

            np.asarray(
                [
                    [0.2, 0.0, 0.0],
                    [1.2, 0.0, 0.0],
                    [2.2, 0.0, 0.0],
                ],
                dtype=np.float64,
            ),
        ),
    )


class Phase3RealLidarEventGapSmokeTests(
    unittest.TestCase
):
    def test_01_config_is_real_train_mechanical_smoke(self):
        payload = config()

        self.assertEqual(
            payload[
                "schema"
            ],
            "TRUST_ROBOT_PHASE3_LIDAR_EVENT_GAP_REAL_SMOKE_V1",
        )

        self.assertEqual(
            payload[
                "source"
            ][
                "split"
            ],
            "train",
        )

        self.assertEqual(
            payload[
                "source"
            ][
                "trajectory"
            ],
            "Circle_01",
        )

    def test_02_source_slice_is_exactly_three_preidentified_events(self):
        payload = config()

        source = payload[
            "source"
        ]

        self.assertEqual(
            source[
                "source_event_count"
            ],
            3,
        )

        self.assertEqual(
            len(
                source[
                    "expected_header_stamps_ns"
                ]
            ),
            3,
        )

        self.assertEqual(
            len(
                source[
                    "expected_raw_pointcloud_data_sha256"
                ]
            ),
            3,
        )

    def test_03_corruption_is_exact_minimal_event_gap(self):
        spec = config()[
            "corruption_spec"
        ]

        self.assertEqual(
            spec[
                "family"
            ],
            "EVENT_GAP",
        )

        self.assertEqual(
            spec[
                "start_index"
            ],
            1,
        )

        self.assertEqual(
            spec[
                "length"
            ],
            1,
        )

        self.assertIsNone(
            spec[
                "severity_id"
            ]
        )

        self.assertIsNone(
            spec[
                "seed"
            ]
        )

        self.assertEqual(
            spec[
                "parameters"
            ],
            {},
        )

    def test_04_selection_does_not_use_performance_or_protected_data(self):
        selection = config()[
            "prospective_selection_rationale"
        ]

        for key in (
            "chosen_from_estimator_output",
            "chosen_from_reference_error",
            "chosen_from_reference_trajectory",
            "chosen_from_validation_metric",
            "chosen_from_confirmation_test",
            "severity_grid_selected",
            "performance_condition_selected",
            "intended_as_localization_accuracy_experiment",
        ):
            self.assertFalse(
                selection[
                    key
                ]
            )

    def test_05_gap_removes_only_middle_origin(self):
        clean = synthetic_three_event_stream()

        payload = config()

        pair = apply_corruption(
            clean,
            CorruptionSpec(
                **payload[
                    "corruption_spec"
                ]
            ),
        )

        np.testing.assert_array_equal(
            pair.corrupt.origin_indices,
            np.asarray(
                [
                    0,
                    2,
                ],
                dtype=np.int64,
            ),
        )

    def test_06_gap_preserves_surviving_payloads_exactly(self):
        clean = synthetic_three_event_stream()

        pair = apply_corruption(
            clean,
            CorruptionSpec(
                **config()[
                    "corruption_spec"
                ]
            ),
        )

        np.testing.assert_array_equal(
            pair.corrupt.payloads[
                0
            ],
            clean.payloads[
                0
            ],
        )

        np.testing.assert_array_equal(
            pair.corrupt.payloads[
                1
            ],
            clean.payloads[
                2
            ],
        )

    def test_07_clean_stream_is_not_mutated(self):
        clean = synthetic_three_event_stream()

        before = clean.fingerprint()

        apply_corruption(
            clean,
            CorruptionSpec(
                **config()[
                    "corruption_spec"
                ]
            ),
        )

        self.assertEqual(
            clean.fingerprint(),
            before,
        )

    def test_08_corruption_manifest_is_deterministic(self):
        clean = synthetic_three_event_stream()

        spec = CorruptionSpec(
            **config()[
                "corruption_spec"
            ]
        )

        first = apply_corruption(
            clean,
            spec,
        )

        second = apply_corruption(
            clean,
            spec,
        )

        self.assertEqual(
            build_pair_manifest(
                first
            ),
            build_pair_manifest(
                second
            ),
        )

        self.assertEqual(
            first.truths[
                0
            ].injection_id,
            second.truths[
                0
            ].injection_id,
        )

    def test_09_pair_manifest_scientific_boundary_is_unscored(self):
        pair = apply_corruption(
            synthetic_three_event_stream(),
            CorruptionSpec(
                **config()[
                    "corruption_spec"
                ]
            ),
        )

        scope = build_pair_manifest(
            pair
        )[
            "scientific_scope"
        ]

        for key in (
            "reference_data_used",
            "confirmation_test_data_used",
            "severity_selected_by_engine",
            "attack_budget_selected_by_engine",
            "estimator_scoring_performed",
            "ate_computed",
            "rpe_computed",
        ):
            self.assertFalse(
                scope[
                    key
                ]
            )

    def test_10_real_smoke_script_cannot_execute_estimator(self):
        source = SMOKE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(
                SMOKE
            ),
        )

        imported_names = set()

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                ast.ImportFrom,
            ):
                imported_names.update(
                    alias.name
                    for alias
                    in node.names
                )

        for forbidden in (
            "build_relative_pose_increment",
            "register_current_scan_to_previous",
            "FixedCleanBackbone",
            "run_fixed_clean_backbone",
        ):
            self.assertNotIn(
                forbidden,
                imported_names,
            )

        self.assertNotIn(
            "ATE",
            source,
        )

        self.assertNotIn(
            "RPE",
            source,
        )


if __name__ == "__main__":
    unittest.main()
