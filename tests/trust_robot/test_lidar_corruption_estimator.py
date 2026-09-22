from pathlib import Path
import ast
import json
import math
import unittest

import numpy as np

from trust_robot.corruption import (
    CorruptionSpec,
    EventStream,
    apply_corruption,
)
from trust_robot.lidar_corruption_estimator import (
    run_frozen_lidar_registration_path,
    run_paired_frozen_lidar_registration,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase3_lidar_paired_estimator_registration_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/lidar_corruption_estimator.py"
)


def base_points():
    return np.asarray(
        [
            [0.00, 0.00, 0.00],
            [1.00, 0.10, 0.20],
            [0.20, 1.20, 0.30],
            [0.30, 0.40, 1.40],
            [1.30, 1.10, 0.50],
            [1.60, 0.40, 1.20],
            [0.60, 1.70, 1.10],
            [1.80, 1.50, 1.60],
        ],
        dtype=np.float64,
    )


def clean_stream():
    points = base_points()

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
            points,
            points
            + np.asarray(
                [
                    0.01,
                    0.00,
                    0.00,
                ]
            ),
            points
            + np.asarray(
                [
                    0.02,
                    0.00,
                    0.00,
                ]
            ),
        ),
    )


def event_gap_pair():
    return apply_corruption(
        clean_stream(),
        CorruptionSpec(
            family=
                "EVENT_GAP",

            modality=
                "lidar",

            start_index=
                1,

            length=
                1,
        ),
    )


class Phase3LidarPairedEstimatorTests(
    unittest.TestCase
):
    def test_01_contract_disallows_output_driven_spec_change(self):
        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        policy = payload[
            "output_policy"
        ]

        self.assertFalse(
            policy[
                "output_may_modify_current_corruption_spec"
            ]
        )

        self.assertFalse(
            policy[
                "output_may_select_future_severity"
            ]
        )

    def test_02_expected_topology_is_frozen(self):
        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        topology = payload[
            "expected_path_topology"
        ]

        self.assertEqual(
            topology[
                "clean_origin_pairs"
            ],
            [
                [0, 1],
                [1, 2],
            ],
        )

        self.assertEqual(
            topology[
                "corrupt_origin_pairs"
            ],
            [
                [0, 2],
            ],
        )

    def test_03_clean_path_uses_two_consecutive_edges(self):
        result = run_frozen_lidar_registration_path(
            clean_stream()
        )

        self.assertEqual(
            result[
                "origin_pairs"
            ],
            [
                [0, 1],
                [1, 2],
            ],
        )

        self.assertEqual(
            result[
                "increment_count"
            ],
            2,
        )

    def test_04_corrupt_path_uses_direct_zero_to_two_edge(self):
        pair = event_gap_pair()

        result = run_frozen_lidar_registration_path(
            pair.corrupt
        )

        self.assertEqual(
            result[
                "origin_pairs"
            ],
            [
                [0, 2],
            ],
        )

        self.assertEqual(
            result[
                "increment_count"
            ],
            1,
        )

    def test_05_paired_execution_reports_topology_change(self):
        result = run_paired_frozen_lidar_registration(
            event_gap_pair()
        )

        self.assertTrue(
            result[
                "path_topology"
            ][
                "registration_path_changed_by_corruption"
            ]
        )

    def test_06_repeated_paired_execution_is_exact(self):
        first = run_paired_frozen_lidar_registration(
            event_gap_pair()
        )

        second = run_paired_frozen_lidar_registration(
            event_gap_pair()
        )

        self.assertEqual(
            first,
            second,
        )

    def test_07_registration_does_not_mutate_streams(self):
        pair = event_gap_pair()

        clean_before = pair.clean.fingerprint()
        corrupt_before = pair.corrupt.fingerprint()

        run_paired_frozen_lidar_registration(
            pair
        )

        self.assertEqual(
            pair.clean.fingerprint(),
            clean_before,
        )

        self.assertEqual(
            pair.corrupt.fingerprint(),
            corrupt_before,
        )

    def test_08_registration_outputs_are_finite(self):
        result = run_paired_frozen_lidar_registration(
            event_gap_pair()
        )

        for branch in (
            "clean",
            "corrupt",
        ):
            for record in result[
                branch
            ][
                "records"
            ]:
                pose = record[
                    "previous_lidar_T_current_lidar"
                ]

                values = (
                    pose[
                        "translation_m"
                    ]
                    + pose[
                        "quaternion_wxyz"
                    ]
                )

                self.assertTrue(
                    all(
                        math.isfinite(
                            float(
                                value
                            )
                        )
                        for value
                        in values
                    )
                )

    def test_09_diagnostics_are_declared_nonscoring(self):
        result = run_paired_frozen_lidar_registration(
            event_gap_pair()
        )

        for branch in (
            "clean",
            "corrupt",
        ):
            for record in result[
                branch
            ][
                "records"
            ]:
                self.assertEqual(
                    record[
                        "diagnostics"
                    ][
                        "interpretation"
                    ],
                    "execution_diagnostic_only_not_accuracy_score",
                )

    def test_10_scientific_scope_contains_no_scoring(self):
        result = run_paired_frozen_lidar_registration(
            event_gap_pair()
        )

        scope = result[
            "scientific_scope"
        ]

        for key in (
            "reference_data_used",
            "confirmation_test_data_used",
            "ground_truth_association_performed",
            "alignment_performed",
            "ate_computed",
            "rpe_computed",
            "trajectory_scoring_performed",
            "estimator_scoring_performed",
            "accuracy_comparison_performed",
            "severity_selection_performed",
            "attack_budget_selection_performed",
        ):
            self.assertFalse(
                scope[
                    key
                ]
            )

    def test_11_module_imports_frozen_registration_function(self):
        source = MODULE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(
                MODULE
            ),
        )

        names = set()

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
                names.update(
                    alias.name
                    for alias
                    in node.names
                )

        self.assertEqual(
            names,
            {
                "register_current_scan_to_previous",
            },
        )

    def test_12_no_evaluation_or_reference_runtime_dependency(self):
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
                ast.ImportFrom,
            ):
                modules.append(
                    node.module
                    or ""
                )

            elif isinstance(
                node,
                ast.Import,
            ):
                modules.extend(
                    alias.name
                    for alias
                    in node.names
                )

        forbidden_tokens = (
            "evaluation",
            "reference",
            "readiness",
            "evo",
        )

        for module in modules:
            self.assertFalse(
                any(
                    token in module.lower()
                    for token
                    in forbidden_tokens
                ),
                module,
            )


if __name__ == "__main__":
    unittest.main()
