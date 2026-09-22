from pathlib import Path
from types import SimpleNamespace
import ast
import json
import math
import struct
import unittest

import numpy as np
from scipy.spatial.transform import Rotation

from trust_robot.clean_backbone import (
    CleanBackboneConfig,
    FixedCleanBackbone,
    PoseSE3,
)
from trust_robot.lidar_frontend import (
    EXPECTED_FIELDS,
    LidarFrontendError,
    SOURCE_ID,
    build_relative_pose_increment,
    decode_m2dgr_velodyne_xyz,
    pointcloud_field_descriptors,
    register_current_scan_to_previous,
    rigid_transform_kabsch,
    transform_xyz,
    validate_lidar_frontend_config,
)


ROOT = Path(__file__).resolve().parents[2]

MODULE = ROOT / "src/trust_robot/lidar_frontend.py"

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase2_clean_lidar_frontend_candidate_v1.json"
)


def pose_matrix(
    pose,
):
    w, x, y, z = pose.quaternion_wxyz

    rotation = Rotation.from_quat(
        [
            x,
            y,
            z,
            w,
        ]
    ).as_matrix()

    matrix = np.eye(
        4,
        dtype=np.float64,
    )

    matrix[:3, :3] = rotation
    matrix[:3, 3] = np.asarray(
        pose.translation_m
    )

    return matrix


def assert_pose_close(
    case,
    actual,
    expected,
    atol=1e-9,
):
    np.testing.assert_allclose(
        pose_matrix(
            actual
        ),
        pose_matrix(
            expected
        ),
        atol=atol,
        rtol=0.0,
    )


def make_message(
    points,
    *,
    timestamp_ns=1_000_000_000,
    frame_id="velodyne",
    fields=None,
    point_step=22,
    is_dense=True,
    is_bigendian=False,
):
    points = np.asarray(
        points,
        dtype=np.float32,
    )

    if fields is None:
        fields = (
            ("x", 0, 7, 1),
            ("y", 4, 7, 1),
            ("z", 8, 7, 1),
            ("intensity", 12, 7, 1),
            ("ring", 16, 4, 1),
            ("time", 18, 7, 1),
        )

    buffer = bytearray(
        points.shape[0]
        * point_step
    )

    for index, point in enumerate(
        points
    ):
        base = (
            index
            * point_step
        )

        struct.pack_into(
            "<fff",
            buffer,
            base,
            float(
                point[0]
            ),
            float(
                point[1]
            ),
            float(
                point[2]
            ),
        )

        if point_step >= 22:
            struct.pack_into(
                "<fHf",
                buffer,
                base + 12,
                1.0,
                0,
                0.0,
            )

    sec = (
        timestamp_ns
        // 1_000_000_000
    )

    nanosec = (
        timestamp_ns
        % 1_000_000_000
    )

    return SimpleNamespace(
        header=SimpleNamespace(
            frame_id=frame_id,
            stamp=SimpleNamespace(
                sec=sec,
                nanosec=nanosec,
            ),
        ),
        height=1,
        width=int(
            points.shape[0]
        ),
        fields=[
            SimpleNamespace(
                name=name,
                offset=offset,
                datatype=datatype,
                count=count,
            )
            for (
                name,
                offset,
                datatype,
                count,
            )
            in fields
        ],
        is_bigendian=is_bigendian,
        point_step=point_step,
        row_step=int(
            points.shape[0]
            * point_step
        ),
        data=bytes(
            buffer
        ),
        is_dense=is_dense,
    )


def synthetic_target():
    return np.asarray(
        [
            [-20.0, -10.0, -3.0],
            [-10.0, 13.0, 2.0],
            [0.0, -15.0, 7.0],
            [12.0, 4.0, -8.0],
            [24.0, -6.0, 3.0],
            [30.0, 17.0, 11.0],
            [-25.0, 21.0, 6.0],
            [17.0, -24.0, 14.0],
        ],
        dtype=np.float64,
    )


def known_prev_T_current():
    rotation = Rotation.from_euler(
        "xyz",
        [
            0.01,
            -0.015,
            0.02,
        ],
    ).as_quat()

    return PoseSE3(
        translation_m=(
            0.12,
            -0.08,
            0.04,
        ),
        quaternion_wxyz=(
            float(
                rotation[3]
            ),
            float(
                rotation[0]
            ),
            float(
                rotation[1]
            ),
            float(
                rotation[2]
            ),
        ),
    )


class LidarFrontendTests(
    unittest.TestCase
):
    def test_01_candidate_config_validates(self):
        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        validate_lidar_frontend_config(
            payload
        )

    def test_02_candidate_config_has_no_numeric_registration_threshold(self):
        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        registration = payload[
            "registration_contract"
        ]

        self.assertIsNone(
            registration[
                "voxel_downsampling"
            ]
        )

        self.assertIsNone(
            registration[
                "correspondence_distance_threshold"
            ]
        )

        self.assertIsNone(
            registration[
                "numeric_convergence_tolerance"
            ]
        )

        self.assertIsNone(
            registration[
                "max_iterations"
            ]
        )

    def test_03_decode_expected_pointcloud_layout(self):
        points = synthetic_target()

        message = make_message(
            points
        )

        decoded = decode_m2dgr_velodyne_xyz(
            message
        )

        np.testing.assert_allclose(
            decoded,
            points,
            atol=1e-6,
            rtol=0.0,
        )

    def test_04_field_descriptors_are_explicit(self):
        message = make_message(
            synthetic_target()
        )

        descriptors = pointcloud_field_descriptors(
            message
        )

        self.assertEqual(
            tuple(
                item[0]
                for item in descriptors
            ),
            EXPECTED_FIELDS,
        )

    def test_05_wrong_frame_is_rejected(self):
        with self.assertRaises(
            LidarFrontendError
        ):
            decode_m2dgr_velodyne_xyz(
                make_message(
                    synthetic_target(),
                    frame_id="base_link",
                )
            )

    def test_06_wrong_field_layout_is_rejected(self):
        wrong_fields = (
            ("x", 0, 7, 1),
            ("y", 4, 7, 1),
            ("z", 8, 7, 1),
        )

        with self.assertRaises(
            LidarFrontendError
        ):
            decode_m2dgr_velodyne_xyz(
                make_message(
                    synthetic_target(),
                    fields=wrong_fields,
                )
            )

    def test_07_wrong_point_step_is_rejected(self):
        with self.assertRaises(
            LidarFrontendError
        ):
            decode_m2dgr_velodyne_xyz(
                make_message(
                    synthetic_target(),
                    point_step=24,
                )
            )

    def test_08_non_dense_cloud_is_rejected(self):
        with self.assertRaises(
            LidarFrontendError
        ):
            decode_m2dgr_velodyne_xyz(
                make_message(
                    synthetic_target(),
                    is_dense=False,
                )
            )

    def test_09_kabsch_identity_is_exact(self):
        target = synthetic_target()

        pose = rigid_transform_kabsch(
            target,
            target,
        )

        assert_pose_close(
            self,
            pose,
            PoseSE3.identity(),
        )

    def test_10_kabsch_recovers_known_corresponded_transform(self):
        target = synthetic_target()

        expected = known_prev_T_current()

        current = transform_xyz(
            expected.inverse(),
            target,
        )

        actual = rigid_transform_kabsch(
            current,
            target,
        )

        assert_pose_close(
            self,
            actual,
            expected,
        )

    def test_11_fixed_point_registration_recovers_small_known_motion(self):
        target = synthetic_target()

        expected = known_prev_T_current()

        current = transform_xyz(
            expected.inverse(),
            target,
        )

        result = register_current_scan_to_previous(
            target,
            current,
        )

        assert_pose_close(
            self,
            result.previous_lidar_T_current_lidar,
            expected,
        )

        self.assertFalse(
            result.diagnostics.correspondence_rejection_used
        )

        self.assertFalse(
            result.diagnostics.voxel_downsampling_used
        )

    def test_12_registration_is_deterministic(self):
        target = synthetic_target()

        expected = known_prev_T_current()

        current = transform_xyz(
            expected.inverse(),
            target,
        )

        first = register_current_scan_to_previous(
            target,
            current,
        )

        second = register_current_scan_to_previous(
            target,
            current,
        )

        self.assertEqual(
            first,
            second,
        )

    def test_13_registration_accepts_different_scan_point_counts(self):
        target = synthetic_target()

        source = target[
            :6
        ].copy()

        result = register_current_scan_to_previous(
            target,
            source,
        )

        self.assertEqual(
            result.diagnostics.source_point_count,
            6,
        )

        self.assertEqual(
            result.diagnostics.target_point_count,
            8,
        )

    def test_14_build_increment_uses_prev_T_current_convention(self):
        target = synthetic_target()

        expected = known_prev_T_current()

        current = transform_xyz(
            expected.inverse(),
            target,
        )

        previous_message = make_message(
            target,
            timestamp_ns=1_000_000_000,
        )

        current_message = make_message(
            current,
            timestamp_ns=1_100_000_000,
        )

        increment, diagnostics = (
            build_relative_pose_increment(
                previous_message=
                    previous_message,

                current_message=
                    current_message,
            )
        )

        assert_pose_close(
            self,
            increment.delta_prev_body_T_current_body,
            expected,
            atol=1e-6,
        )

        self.assertEqual(
            increment.body_frame_id,
            "velodyne",
        )

        self.assertEqual(
            increment.source_id,
            SOURCE_ID,
        )

        self.assertGreater(
            diagnostics.final_correspondence_count,
            0,
        )

    def test_15_nonincreasing_scan_timestamp_is_rejected(self):
        points = synthetic_target()

        with self.assertRaises(
            LidarFrontendError
        ):
            build_relative_pose_increment(
                previous_message=
                    make_message(
                        points,
                        timestamp_ns=
                            2_000_000_000,
                    ),

                current_message=
                    make_message(
                        points,
                        timestamp_ns=
                            2_000_000_000,
                    ),
            )

    def test_16_frontend_increment_integrates_with_clean_backbone(self):
        target = synthetic_target()

        expected = known_prev_T_current()

        current = transform_xyz(
            expected.inverse(),
            target,
        )

        previous_message = make_message(
            target,
            timestamp_ns=1_000_000_000,
        )

        current_message = make_message(
            current,
            timestamp_ns=1_100_000_000,
        )

        increment_value, _ = (
            build_relative_pose_increment(
                previous_message=
                    previous_message,

                current_message=
                    current_message,
            )
        )

        backbone = FixedCleanBackbone(
            CleanBackboneConfig(
                world_frame_id=
                    "phase2_lidar_first_scan_origin",

                body_frame_id=
                    "velodyne",

                relative_pose_source_id=
                    SOURCE_ID,

                initial_timestamp_ns=
                    1_000_000_000,

                initial_pose_world_T_body=
                    PoseSE3.identity(),
            )
        )

        state = backbone.apply(
            increment_value
        )

        assert_pose_close(
            self,
            state.pose_world_T_body,
            expected,
            atol=1e-6,
        )

    def test_17_no_reference_or_scoring_dependencies(self):
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

        for forbidden_name in (
            "compute_ate",
            "compute_rpe",
            "score_trajectory",
            "score_estimator",
            "associate_reference",
            "align_trajectory",
        ):
            self.assertNotIn(
                forbidden_name,
                source,
            )

    def test_18_registration_api_exposes_no_tuning_parameters(self):
        source = MODULE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(
                MODULE
            ),
        )

        functions = {
            node.name: node
            for node in tree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
        }

        registration = functions[
            "register_current_scan_to_previous"
        ]

        registration_args = [
            arg.arg
            for arg in registration.args.args
        ]

        self.assertEqual(
            registration_args,
            [
                "previous_xyz",
                "current_xyz",
            ],
        )

        self.assertEqual(
            registration.args.kwonlyargs,
            [],
        )

        kabsch = functions[
            "rigid_transform_kabsch"
        ]

        self.assertEqual(
            [
                arg.arg
                for arg in kabsch.args.args
            ],
            [
                "source_xyz",
                "target_xyz",
            ],
        )

        exposed_argument_names = {
            arg.arg
            for node in functions.values()
            for arg in (
                list(
                    node.args.posonlyargs
                )
                + list(
                    node.args.args
                )
                + list(
                    node.args.kwonlyargs
                )
            )
        }

        forbidden_tuning_arguments = {
            "voxel_size",
            "max_correspondence_distance",
            "correspondence_distance_threshold",
            "distance_threshold",
            "trim_fraction",
            "outlier_threshold",
            "keyframe_distance",
            "keyframe_rotation",
            "convergence_tolerance",
            "numeric_convergence_tolerance",
            "max_iterations",
        }

        self.assertTrue(
            forbidden_tuning_arguments.isdisjoint(
                exposed_argument_names
            ),
            (
                forbidden_tuning_arguments
                & exposed_argument_names
            ),
        )

        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        registration_contract = payload[
            "registration_contract"
        ]

        self.assertIsNone(
            registration_contract[
                "voxel_downsampling"
            ]
        )

        self.assertIsNone(
            registration_contract[
                "correspondence_distance_threshold"
            ]
        )

        self.assertIsNone(
            registration_contract[
                "outlier_rejection"
            ]
        )

        self.assertIsNone(
            registration_contract[
                "keyframe_rule"
            ]
        )

        self.assertIsNone(
            registration_contract[
                "numeric_convergence_tolerance"
            ]
        )

        self.assertIsNone(
            registration_contract[
                "max_iterations"
            ]
        )


if __name__ == "__main__":
    unittest.main()
