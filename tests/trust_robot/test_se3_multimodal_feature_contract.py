from copy import deepcopy
from io import BytesIO
from pathlib import Path
import ast
import json
import math
import unittest

import numpy as np
from PIL import Image

from trust_robot.se3_multimodal_feature_contract import (
    CAMERA_CONTRACT_ID,
    CAMERA_FEATURE_SPECS,
    CAMERA_STREAM,
    IMU_CONTRACT_ID,
    IMU_FEATURE_SPECS,
    IMU_STREAMS,
    LIDAR_CONTRACT_ID,
    LIDAR_FEATURE_NAMES,
    PHASE4_LIDAR_FREEZE_SHA256,
    SCHEMA,
    SE3FeatureContractError,
    build_feature_contract_manifest,
    content_sha256,
    decode_camera_grayscale,
    extract_camera_features,
    extract_camera_features_from_gray,
    extract_imu_features,
    validate_feature_contract_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "se3_multimodal_feature_contract_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
      "se3_multimodal_feature_contract.py"
)


class SE3MultimodalFeatureContractTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

    def test_01_schema(self):
        self.assertEqual(
            self.payload["schema"],
            SCHEMA,
        )

    def test_02_content_digest(self):
        self.assertEqual(
            self.payload[
                "content_sha256"
            ],
            content_sha256(
                self.payload
            ),
        )

    def test_03_builder_matches_config(self):
        self.assertEqual(
            self.payload,
            build_feature_contract_manifest(),
        )

    def test_04_stage_is_se3(self):
        self.assertEqual(
            self.payload[
                "stage"
            ][
                "stage_id"
            ],
            "SE3",
        )

        self.assertEqual(
            self.payload[
                "stage"
            ][
                "stage_name"
            ],
            "multimodal_feature_pipeline",
        )

    def test_05_resolution_is_prospective_not_supervised(self):
        basis = self.payload[
            "resolution_basis"
        ]

        self.assertEqual(
            basis["mode"],
            "prospective_measurement_semantics",
        )

        self.assertFalse(
            basis[
                "supervised_feature_ranking_used"
            ]
        )

        self.assertFalse(
            basis[
                "health_labels_used"
            ]
        )

    def test_06_missing_historical_basis_not_reconstructed(self):
        self.assertFalse(
            self.payload[
                "resolution_basis"
            ][
                "historical_missing_feature_basis_artifacts_reconstructed"
            ]
        )

    def test_07_camera_contract_identity(self):
        camera = self.payload[
            "camera"
        ]

        self.assertEqual(
            camera[
                "contract_id"
            ],
            CAMERA_CONTRACT_ID,
        )

        self.assertEqual(
            camera[
                "source_stream"
            ],
            CAMERA_STREAM,
        )

    def test_08_camera_feature_names_exact(self):
        self.assertEqual(
            [
                item["name"]
                for item
                in self.payload[
                    "camera"
                ][
                    "feature_specs"
                ]
            ],
            [
                spec.name
                for spec
                in CAMERA_FEATURE_SPECS
            ],
        )

        self.assertEqual(
            len(
                CAMERA_FEATURE_SPECS
            ),
            3,
        )

    def test_09_camera_has_no_threshold_or_normalization(self):
        camera = self.payload[
            "camera"
        ]

        self.assertEqual(
            camera[
                "normalization"
            ],
            "none",
        )

        self.assertEqual(
            camera[
                "thresholding"
            ],
            "none",
        )

        self.assertEqual(
            camera[
                "temporal_aggregation"
            ],
            "none_per_message",
        )

    def test_10_camera_gray_formula_exact(self):
        gray = np.asarray(
            [
                [0, 10],
                [20, 30],
            ],
            dtype=np.uint8,
        )

        mean, std, neighbor = (
            extract_camera_features_from_gray(
                gray
            )
        )

        self.assertAlmostEqual(
            mean,
            15.0,
        )

        self.assertAlmostEqual(
            std,
            math.sqrt(
                125.0
            ),
        )

        self.assertAlmostEqual(
            neighbor,
            15.0,
        )

    def test_11_camera_constant_image(self):
        gray = np.full(
            (
                8,
                8,
            ),
            100,
            dtype=np.uint8,
        )

        self.assertEqual(
            extract_camera_features_from_gray(
                gray
            ),
            (
                100.0,
                0.0,
                0.0,
            ),
        )

    def test_12_camera_rejects_wrong_dtype(self):
        with self.assertRaises(
            SE3FeatureContractError
        ):
            extract_camera_features_from_gray(
                np.zeros(
                    (
                        2,
                        2,
                    ),
                    dtype=np.float64,
                )
            )

    def test_13_camera_rejects_too_small(self):
        with self.assertRaises(
            SE3FeatureContractError
        ):
            extract_camera_features_from_gray(
                np.zeros(
                    (
                        1,
                        2,
                    ),
                    dtype=np.uint8,
                )
            )

    def test_14_camera_compressed_decode_deterministic(self):
        image = Image.fromarray(
            np.full(
                (
                    16,
                    16,
                ),
                123,
                dtype=np.uint8,
            ),
            mode="L",
        )

        buffer = BytesIO()

        image.save(
            buffer,
            format="JPEG",
            quality=100,
            subsampling=0,
        )

        payload = buffer.getvalue()

        first = extract_camera_features(
            payload
        )

        second = extract_camera_features(
            payload
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            decode_camera_grayscale(
                payload
            ).shape,
            (
                16,
                16,
            ),
        )

    def test_15_camera_rejects_invalid_compressed_payload(self):
        with self.assertRaises(
            SE3FeatureContractError
        ):
            extract_camera_features(
                b"not-an-image"
            )

    def test_16_imu_contract_identity(self):
        imu = self.payload[
            "imu"
        ]

        self.assertEqual(
            imu[
                "contract_id"
            ],
            IMU_CONTRACT_ID,
        )

        self.assertEqual(
            tuple(
                imu[
                    "source_streams"
                ]
            ),
            IMU_STREAMS,
        )

    def test_17_imu_feature_names_exact(self):
        self.assertEqual(
            [
                item["name"]
                for item
                in self.payload[
                    "imu"
                ][
                    "feature_specs"
                ]
            ],
            [
                spec.name
                for spec
                in IMU_FEATURE_SPECS
            ],
        )

        self.assertEqual(
            len(
                IMU_FEATURE_SPECS
            ),
            2,
        )

    def test_18_imu_norm_formula(self):
        angular, acceleration = (
            extract_imu_features(
                (
                    3.0,
                    4.0,
                    0.0,
                ),
                (
                    0.0,
                    0.0,
                    9.81,
                ),
            )
        )

        self.assertEqual(
            angular,
            5.0,
        )

        self.assertAlmostEqual(
            acceleration,
            9.81,
        )

    def test_19_imu_rejects_nonfinite(self):
        with self.assertRaises(
            SE3FeatureContractError
        ):
            extract_imu_features(
                (
                    float("nan"),
                    0.0,
                    0.0,
                ),
                (
                    0.0,
                    0.0,
                    9.81,
                ),
            )

    def test_20_imu_excludes_orientation_and_covariance(self):
        imu = self.payload[
            "imu"
        ]

        self.assertFalse(
            imu[
                "orientation_used"
            ]
        )

        self.assertFalse(
            imu[
                "covariance_used"
            ]
        )

    def test_21_imu_raw_axes_not_emitted(self):
        self.assertFalse(
            self.payload[
                "imu"
            ][
                "raw_axes_emitted_as_features"
            ]
        )

    def test_22_lidar_contract_preserved(self):
        lidar = self.payload[
            "lidar"
        ]

        self.assertEqual(
            lidar[
                "contract_id"
            ],
            LIDAR_CONTRACT_ID,
        )

        self.assertEqual(
            lidar[
                "phase4_freeze_sha256"
            ],
            PHASE4_LIDAR_FREEZE_SHA256,
        )

        self.assertEqual(
            tuple(
                lidar[
                    "feature_names"
                ]
            ),
            LIDAR_FEATURE_NAMES,
        )

        self.assertFalse(
            lidar[
                "contract_changed"
            ]
        )

    def test_23_missing_is_not_zero_vector(self):
        missing = self.payload[
            "missing_measurement_policy"
        ]

        self.assertFalse(
            missing[
                "missing_stream_is_zero_vector"
            ]
        )

        self.assertFalse(
            missing[
                "missing_record_is_zero_vector"
            ]
        )

        self.assertTrue(
            missing[
                "missing_measurement_preserved_as_absent"
            ]
        )

    def test_24_no_cross_modal_timing_assumption(self):
        timing = self.payload[
            "timing_boundary"
        ]

        self.assertFalse(
            timing[
                "bag_record_time_is_physical_measurement_time"
            ]
        )

        self.assertFalse(
            timing[
                "header_stamp_proves_shared_clock"
            ]
        )

        self.assertFalse(
            timing[
                "cross_modal_synchronization_selected"
            ]
        )

        self.assertFalse(
            timing[
                "feature_extraction_requires_cross_modal_alignment"
            ]
        )

    def test_25_scientific_boundary_fail_closed(self):
        boundary = self.payload[
            "scientific_boundary"
        ]

        for value in boundary.values():
            self.assertFalse(
                value
            )

    def test_26_exact_contracts_resolved_but_se3_not_complete(self):
        status = self.payload[
            "empirical_status"
        ]

        self.assertTrue(
            status[
                "camera_exact_contract_resolved"
            ]
        )

        self.assertTrue(
            status[
                "imu_exact_contract_resolved"
            ]
        )

        self.assertTrue(
            status[
                "lidar_frozen_contract_preserved"
            ]
        )

        self.assertFalse(
            status[
                "full_train_camera_feature_extraction_completed"
            ]
        )

        self.assertFalse(
            status[
                "full_train_imu_feature_extraction_completed"
            ]
        )

        self.assertFalse(
            status[
                "SE3_complete"
            ]
        )

    def test_27_se4_training_remains_blocked(self):
        self.assertFalse(
            self.payload[
                "next_action"
            ][
                "SE4_model_training_authorized"
            ]
        )

    def test_28_source_bindings_exact(self):
        bindings = self.payload[
            "source_bindings"
        ]

        self.assertEqual(
            bindings[
                "SE2_freeze_sha256"
            ],
            "63da52c788208ae715abc7e0b8eb0ba6777cc16d33d90466332779c630618230",
        )

        self.assertEqual(
            bindings[
                "phase5_camera_imu_train_source_evidence_sha256"
            ],
            "d4d2a73ddbcf73102cec0d0d4556fa65786a408217fefe1dece0f4d402cce675",
        )

    def test_29_validator_accepts_exact_manifest(self):
        validate_feature_contract_manifest(
            self.payload
        )

    def test_30_validator_rejects_feature_change(self):
        changed = deepcopy(
            self.payload
        )

        changed[
            "camera"
        ][
            "feature_specs"
        ][0][
            "name"
        ] = "invented_feature"

        with self.assertRaises(
            SE3FeatureContractError
        ):
            validate_feature_contract_manifest(
                changed
            )

    def test_31_validator_rejects_training_enable(self):
        changed = deepcopy(
            self.payload
        )

        changed[
            "scientific_boundary"
        ][
            "classifier_training_authorized"
        ] = True

        with self.assertRaises(
            SE3FeatureContractError
        ):
            validate_feature_contract_manifest(
                changed
            )

    def test_32_module_does_not_import_health_or_evaluation_code(self):
        tree = ast.parse(
            MODULE.read_text(
                encoding="utf-8"
            ),
            filename=str(
                MODULE
            ),
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
                    alias.name
                    for alias in node.names
                )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):
                imported.append(
                    node.module
                    or ""
                )

        for forbidden in (
            "health_supervision",
            "multimodal_health_model",
            "trajectory_evaluation",
            "evo",
            "sklearn",
            "torch",
        ):
            self.assertFalse(
                any(
                    forbidden
                    in name
                    for name in imported
                ),
                (
                    forbidden,
                    imported,
                ),
            )


if __name__ == "__main__":
    unittest.main()
