from pathlib import Path
from tempfile import TemporaryDirectory
import ast
import json
import unittest

from trust_robot.clean_backbone import (
    CleanBackboneState,
    PoseSE3,
    RelativePoseIncrement,
)
from trust_robot.lidar_frontend import (
    LidarRegistrationDiagnostics,
)
from trust_robot.lidar_train_run import (
    TRAIN_TRAJECTORIES,
    atomic_write_json,
    build_train_run_manifest,
    canonical_content_sha256,
    pair_record,
    trajectory_complete_record,
    trajectory_header_record,
)


ROOT = Path(__file__).resolve().parents[2]

MODULE = (
    ROOT
    / "src/trust_robot/lidar_train_run.py"
)

SCRIPT = (
    ROOT
    / "scripts/trust_robot/"
      "run_phase2_lidar_train_v1.py"
)


def state():
    return CleanBackboneState(
        sequence_index=1,
        timestamp_ns=200,
        pose_world_T_body=PoseSE3(
            translation_m=(
                1.0,
                2.0,
                3.0,
            ),
            quaternion_wxyz=(
                1.0,
                0.0,
                0.0,
                0.0,
            ),
        ),
        last_source_id=
            "m2dgr_velodyne_exact_nn_fixed_point_v1",
    )


def increment():
    return RelativePoseIncrement(
        timestamp_ns=200,
        body_frame_id="velodyne",
        source_id=
            "m2dgr_velodyne_exact_nn_fixed_point_v1",
        delta_prev_body_T_current_body=
            PoseSE3.identity(),
    )


def diagnostics():
    return LidarRegistrationDiagnostics(
        source_point_count=10,
        target_point_count=11,
        fixed_point_iterations=3,
        final_correspondence_count=10,
        final_nearest_neighbor_rmse_m=0.25,
        convergence_rule=
            "exact_nearest_neighbor_assignment_unchanged",
        correspondence_rejection_used=False,
        voxel_downsampling_used=False,
    )


class LidarTrainRunTests(
    unittest.TestCase
):
    def test_01_exact_frozen_train_order(self):
        self.assertEqual(
            len(
                TRAIN_TRAJECTORIES
            ),
            22,
        )

        self.assertEqual(
            TRAIN_TRAJECTORIES[0],
            "Circle_01",
        )

        self.assertEqual(
            TRAIN_TRAJECTORIES[-1],
            "walk_01",
        )

        self.assertEqual(
            len(
                set(
                    TRAIN_TRAJECTORIES
                )
            ),
            22,
        )

    def test_02_confirmation_names_are_absent(self):
        forbidden = {
            "Circle_02",
            "gate_02",
            "hall_02",
            "lift_01",
            "room_01",
            "room_dark_05",
            "street_06",
        }

        self.assertTrue(
            forbidden.isdisjoint(
                TRAIN_TRAJECTORIES
            )
        )

    def test_03_manifest_is_deterministic_and_fail_scoped(self):
        sizes = {
            trajectory:
                index + 1
            for index, trajectory
            in enumerate(
                TRAIN_TRAJECTORIES
            )
        }

        kwargs = {
            "split_manifest_sha256":
                "a" * 64,

            "frontend_config_file_sha256":
                "b" * 64,

            "frontend_config_content_sha256":
                "c" * 64,

            "repo_component_hashes": {
                "module":
                    "d" * 64,
            },

            "bag_file_sizes_bytes":
                sizes,
        }

        first = build_train_run_manifest(
            **kwargs
        )

        second = build_train_run_manifest(
            **kwargs
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            first[
                "content_sha256"
            ],
            canonical_content_sha256(
                first
            ),
        )

        scope = first[
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
            "scan_temporal_reference_verified",
            "per_point_time_used",
            "deskew_performed",
            "phase2_exit_evidence_satisfied",
        ):
            self.assertFalse(
                scope[
                    key
                ]
            )

    def test_04_manifest_has_no_automatic_threshold_or_timeout(self):
        sizes = {
            trajectory:
                index + 1
            for index, trajectory
            in enumerate(
                TRAIN_TRAJECTORIES
            )
        }

        manifest = build_train_run_manifest(
            split_manifest_sha256="a" * 64,
            frontend_config_file_sha256="b" * 64,
            frontend_config_content_sha256="c" * 64,
            repo_component_hashes={},
            bag_file_sizes_bytes=sizes,
        )

        execution = manifest[
            "execution_contract"
        ]

        self.assertIsNone(
            execution[
                "registration_timeout"
            ]
        )

        self.assertIsNone(
            execution[
                "automatic_residual_threshold"
            ]
        )

        self.assertIsNone(
            execution[
                "automatic_iteration_limit"
            ]
        )

        self.assertIsNone(
            execution[
                "automatic_exclusion_rule"
            ]
        )

        self.assertEqual(
            execution[
                "scan_skip_policy"
            ],
            "none",
        )

        self.assertEqual(
            execution[
                "trajectory_skip_policy"
            ],
            "none",
        )

    def test_05_header_record_is_local_velodyne_origin(self):
        record = trajectory_header_record(
            trajectory="Circle_01",
            initial_timestamp_ns=100,
        )

        self.assertEqual(
            record[
                "body_frame_id"
            ],
            "velodyne",
        )

        self.assertEqual(
            record[
                "world_frame_id"
            ],
            "phase2_lidar_first_scan_origin",
        )

        self.assertFalse(
            record[
                "reference_data_used"
            ]
        )

    def test_06_pair_record_preserves_diagnostics_without_scoring(self):
        record = pair_record(
            trajectory="Circle_01",
            scan_index=1,
            previous_timestamp_ns=100,
            increment=increment(),
            state=state(),
            diagnostics=diagnostics(),
        )

        self.assertEqual(
            record[
                "header_delta_ns"
            ],
            100,
        )

        self.assertEqual(
            record[
                "diagnostics"
            ][
                "final_nearest_neighbor_rmse_m"
            ],
            0.25,
        )

        scope = record[
            "scientific_scope"
        ]

        self.assertFalse(
            scope[
                "trajectory_scoring_performed"
            ]
        )

        self.assertFalse(
            scope[
                "ate_computed"
            ]
        )

        self.assertFalse(
            scope[
                "rpe_computed"
            ]
        )

    def test_07_complete_record_is_not_a_score(self):
        record = trajectory_complete_record(
            trajectory="Circle_01",
            scan_count=2,
            final_state=state(),
        )

        self.assertEqual(
            record[
                "increment_count"
            ],
            1,
        )

        self.assertFalse(
            record[
                "trajectory_scoring_performed"
            ]
        )

    def test_08_atomic_json_roundtrip(self):
        with TemporaryDirectory() as tmp:
            path = (
                Path(tmp)
                / "value.json"
            )

            payload = {
                "hello":
                    "world",

                "value":
                    3,
            }

            atomic_write_json(
                path,
                payload,
            )

            self.assertEqual(
                json.loads(
                    path.read_text(
                        encoding="utf-8"
                    )
                ),
                payload,
            )

    def test_09_run_module_has_no_evaluation_stack(self):
        source = MODULE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(
                MODULE
            ),
        )

        imported_roots = set()

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                ast.Import,
            ):
                for alias in node.names:
                    imported_roots.add(
                        alias.name.split(".")[0]
                    )

            elif (
                isinstance(
                    node,
                    ast.ImportFrom,
                )
                and node.module
                and node.level == 0
            ):
                imported_roots.add(
                    node.module.split(".")[0]
                )

        for forbidden in (
            "evo",
            "gtsam",
            "open3d",
            "imu_reliability",
        ):
            self.assertNotIn(
                forbidden,
                imported_roots,
            )

        for forbidden in (
            "compute_ate",
            "compute_rpe",
            "score_trajectory",
            "score_estimator",
            "align_trajectory",
            "associate_reference",
        ):
            self.assertNotIn(
                forbidden,
                source,
            )

    def test_10_full_train_cli_exposes_no_trajectory_selection(self):
        source = SCRIPT.read_text(
            encoding="utf-8"
        )

        for forbidden in (
            "--trajectory",
            "--max-iterations",
            "--threshold",
            "--voxel",
            "--reference",
            "--ground-truth",
            "--alignment",
        ):
            self.assertNotIn(
                forbidden,
                source,
            )


if __name__ == "__main__":
    unittest.main()
