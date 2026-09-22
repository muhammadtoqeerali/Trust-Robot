from pathlib import Path
import ast
import math
import unittest

from trust_robot.clean_backbone import (
    CleanBackboneConfig,
    CleanBackboneError,
    FixedCleanBackbone,
    PoseSE3,
    RelativePoseIncrement,
    build_clean_backbone_run_payload,
    clean_backbone_run_content_sha256,
    rotate_vector,
    run_clean_backbone,
)


ROOT = Path(__file__).resolve().parents[2]

MODULE = (
    ROOT
    / "src/trust_robot/clean_backbone.py"
)


def assert_vector_close(
    case,
    actual,
    expected,
    places=12,
):
    case.assertEqual(
        len(actual),
        len(expected),
    )

    for left, right in zip(
        actual,
        expected,
        strict=True,
    ):
        case.assertAlmostEqual(
            left,
            right,
            places=places,
        )


def base_config():
    return CleanBackboneConfig(
        world_frame_id="synthetic_world",
        body_frame_id="synthetic_body",
        relative_pose_source_id=
            "synthetic_relative_pose_source",
        initial_timestamp_ns=0,
        initial_pose_world_T_body=
            PoseSE3.identity(),
    )


def increment(
    timestamp_ns,
    pose,
    *,
    source_id="synthetic_relative_pose_source",
    body_frame_id="synthetic_body",
):
    return RelativePoseIncrement(
        timestamp_ns=timestamp_ns,
        body_frame_id=body_frame_id,
        source_id=source_id,
        delta_prev_body_T_current_body=pose,
    )


class CleanBackboneTests(
    unittest.TestCase
):
    def test_01_identity_pose_is_exact(self):
        pose = PoseSE3.identity()

        self.assertEqual(
            pose.translation_m,
            (
                0.0,
                0.0,
                0.0,
            ),
        )

        self.assertEqual(
            pose.quaternion_wxyz,
            (
                1.0,
                0.0,
                0.0,
                0.0,
            ),
        )

    def test_02_identity_increment_preserves_pose(self):
        backbone = FixedCleanBackbone(
            base_config()
        )

        state = backbone.apply(
            increment(
                1,
                PoseSE3.identity(),
            )
        )

        self.assertEqual(
            state.pose_world_T_body,
            PoseSE3.identity(),
        )

        self.assertEqual(
            state.sequence_index,
            1,
        )

    def test_03_translation_composes_under_identity_rotation(self):
        backbone = FixedCleanBackbone(
            base_config()
        )

        state = backbone.apply(
            increment(
                1,
                PoseSE3(
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
            )
        )

        self.assertEqual(
            state.pose_world_T_body.translation_m,
            (
                1.0,
                2.0,
                3.0,
            ),
        )

    def test_04_translation_is_rotated_by_previous_orientation(self):
        half = math.sqrt(
            0.5
        )

        initial = PoseSE3(
            translation_m=(
                0.0,
                0.0,
                0.0,
            ),
            quaternion_wxyz=(
                half,
                0.0,
                0.0,
                half,
            ),
        )

        config = CleanBackboneConfig(
            world_frame_id="world",
            body_frame_id="body",
            relative_pose_source_id="source",
            initial_timestamp_ns=0,
            initial_pose_world_T_body=initial,
        )

        backbone = FixedCleanBackbone(
            config
        )

        state = backbone.apply(
            RelativePoseIncrement(
                timestamp_ns=1,
                body_frame_id="body",
                source_id="source",
                delta_prev_body_T_current_body=
                    PoseSE3(
                        translation_m=(
                            1.0,
                            0.0,
                            0.0,
                        ),
                        quaternion_wxyz=(
                            1.0,
                            0.0,
                            0.0,
                            0.0,
                        ),
                    ),
            )
        )

        assert_vector_close(
            self,
            state.pose_world_T_body.translation_m,
            (
                0.0,
                1.0,
                0.0,
            ),
        )

    def test_05_rotation_composition_is_6dof(self):
        half = math.sqrt(
            0.5
        )

        quarter_turn = PoseSE3(
            translation_m=(
                0.0,
                0.0,
                0.0,
            ),
            quaternion_wxyz=(
                half,
                0.0,
                0.0,
                half,
            ),
        )

        composed = quarter_turn.compose(
            quarter_turn
        )

        rotated = rotate_vector(
            composed.quaternion_wxyz,
            (
                1.0,
                0.0,
                0.0,
            ),
        )

        assert_vector_close(
            self,
            rotated,
            (
                -1.0,
                0.0,
                0.0,
            ),
        )

    def test_06_quaternion_scale_and_sign_are_canonicalized(self):
        positive = PoseSE3(
            translation_m=(
                0.0,
                0.0,
                0.0,
            ),
            quaternion_wxyz=(
                2.0,
                0.0,
                0.0,
                0.0,
            ),
        )

        negative = PoseSE3(
            translation_m=(
                0.0,
                0.0,
                0.0,
            ),
            quaternion_wxyz=(
                -3.0,
                0.0,
                0.0,
                0.0,
            ),
        )

        self.assertEqual(
            positive.quaternion_wxyz,
            negative.quaternion_wxyz,
        )

        self.assertEqual(
            positive.quaternion_wxyz,
            (
                1.0,
                0.0,
                0.0,
                0.0,
            ),
        )

    def test_07_pose_inverse_roundtrip(self):
        half = math.sqrt(
            0.5
        )

        pose = PoseSE3(
            translation_m=(
                2.0,
                -1.0,
                0.5,
            ),
            quaternion_wxyz=(
                half,
                0.0,
                half,
                0.0,
            ),
        )

        identity = pose.compose(
            pose.inverse()
        )

        assert_vector_close(
            self,
            identity.translation_m,
            (
                0.0,
                0.0,
                0.0,
            ),
        )

        assert_vector_close(
            self,
            identity.quaternion_wxyz,
            (
                1.0,
                0.0,
                0.0,
                0.0,
            ),
        )

    def test_08_zero_quaternion_is_rejected(self):
        with self.assertRaises(
            CleanBackboneError
        ):
            PoseSE3(
                translation_m=(
                    0.0,
                    0.0,
                    0.0,
                ),
                quaternion_wxyz=(
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                ),
            )

    def test_09_nonfinite_pose_is_rejected(self):
        with self.assertRaises(
            CleanBackboneError
        ):
            PoseSE3(
                translation_m=(
                    float("nan"),
                    0.0,
                    0.0,
                ),
                quaternion_wxyz=(
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                ),
            )

    def test_10_nonmonotonic_timestamp_is_rejected(self):
        backbone = FixedCleanBackbone(
            base_config()
        )

        backbone.apply(
            increment(
                5,
                PoseSE3.identity(),
            )
        )

        with self.assertRaises(
            CleanBackboneError
        ):
            backbone.apply(
                increment(
                    4,
                    PoseSE3.identity(),
                )
            )

    def test_11_duplicate_timestamp_is_rejected(self):
        backbone = FixedCleanBackbone(
            base_config()
        )

        backbone.apply(
            increment(
                5,
                PoseSE3.identity(),
            )
        )

        with self.assertRaises(
            CleanBackboneError
        ):
            backbone.apply(
                increment(
                    5,
                    PoseSE3.identity(),
                )
            )

    def test_12_body_frame_mismatch_is_rejected(self):
        backbone = FixedCleanBackbone(
            base_config()
        )

        with self.assertRaises(
            CleanBackboneError
        ):
            backbone.apply(
                increment(
                    1,
                    PoseSE3.identity(),
                    body_frame_id="other_body",
                )
            )

    def test_13_source_mismatch_is_rejected(self):
        backbone = FixedCleanBackbone(
            base_config()
        )

        with self.assertRaises(
            CleanBackboneError
        ):
            backbone.apply(
                increment(
                    1,
                    PoseSE3.identity(),
                    source_id="different_source",
                )
            )

    def test_14_empty_source_id_is_rejected(self):
        with self.assertRaises(
            CleanBackboneError
        ):
            CleanBackboneConfig(
                world_frame_id="world",
                body_frame_id="body",
                relative_pose_source_id="",
                initial_timestamp_ns=0,
                initial_pose_world_T_body=
                    PoseSE3.identity(),
            )

    def test_15_sequence_run_is_deterministic(self):
        increments = (
            increment(
                10,
                PoseSE3(
                    translation_m=(
                        1.0,
                        0.0,
                        0.0,
                    ),
                    quaternion_wxyz=(
                        1.0,
                        0.0,
                        0.0,
                        0.0,
                    ),
                ),
            ),
            increment(
                20,
                PoseSE3(
                    translation_m=(
                        0.0,
                        2.0,
                        0.0,
                    ),
                    quaternion_wxyz=(
                        1.0,
                        0.0,
                        0.0,
                        0.0,
                    ),
                ),
            ),
        )

        first = run_clean_backbone(
            base_config(),
            increments,
        )

        second = run_clean_backbone(
            base_config(),
            increments,
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            len(first),
            3,
        )

        self.assertEqual(
            first[-1].pose_world_T_body.translation_m,
            (
                1.0,
                2.0,
                0.0,
            ),
        )

    def test_16_run_payload_digest_is_deterministic_and_fail_scoped(self):
        increments = (
            increment(
                10,
                PoseSE3.identity(),
            ),
        )

        first = build_clean_backbone_run_payload(
            base_config(),
            increments,
        )

        second = build_clean_backbone_run_payload(
            base_config(),
            increments,
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            first[
                "content_sha256"
            ],
            clean_backbone_run_content_sha256(
                first
            ),
        )

        scope = first[
            "scientific_scope"
        ]

        self.assertFalse(
            scope[
                "reference_data_used"
            ]
        )

        self.assertFalse(
            scope[
                "confirmation_test_data_used"
            ]
        )

        self.assertFalse(
            scope[
                "evaluation_metric_computed"
            ]
        )

        self.assertFalse(
            scope[
                "phase2_exit_evidence_satisfied"
            ]
        )

    def test_17_module_has_no_historical_model_or_evaluation_dependency(self):
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

        for node in ast.walk(tree):
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
            "numpy",
            "scipy",
            "pandas",
            "torch",
            "open3d",
            "gtsam",
            "evo",
            "imu_reliability",
        ):
            self.assertNotIn(
                forbidden,
                imported_roots,
            )

        self.assertNotIn(
            "m2dgr",
            source.lower(),
        )

        function_names = {
            node.name
            for node in ast.walk(
                tree
            )
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }

        for forbidden in (
            "compute_ate",
            "compute_rpe",
            "score_trajectory",
            "score_estimator",
            "select_threshold",
            "infer_health",
            "inject_fault",
        ):
            self.assertNotIn(
                forbidden,
                function_names,
            )


if __name__ == "__main__":
    unittest.main()
