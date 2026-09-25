from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import ast
import json
import unittest

from trust_robot.se4_health_model_training_resolution import (
    CAMERA_FEATURES,
    FROZEN_INPUT_SHA256,
    HEALTH_STATES,
    IMU_FEATURES,
    LIDAR_FEATURES,
    RESOLUTION_ID,
    SCHEMA,
    SE3_FREEZE_CONTENT_SHA256,
    SE4HealthModelTrainingResolutionError,
    assert_se5_entry_authorized,
    assert_training_execution_authorized,
    build_se4_health_model_training_resolution,
    content_sha256,
    validate_se4_health_model_training_resolution,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_health_model_training_resolution_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_health_model_training_resolution.py"
)

SE2_FREEZE = (
    ROOT
    / "manifests/"
    "trust_robot_se2_health_supervision_protocol_freeze_v1.json"
)

SE3_FREEZE = (
    ROOT
    / "manifests/"
    "trust_robot_se3_multimodal_feature_pipeline_freeze_v1.json"
)

LEGACY_INTERFACE = (
    ROOT
    / "configs/trust_robot/"
    "phase5_multimodal_health_model_interface_candidate_v1.json"
)

PHASE5_FREEZE = (
    ROOT
    / "manifests/"
    "trust_robot_phase5_multimodal_software_architecture_freeze_v1.json"
)


def file_sha(path):
    return sha256(
        path.read_bytes()
    ).hexdigest()


class SE4HealthModelTrainingResolutionTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

    def test_01_schema_identity(self):
        self.assertEqual(
            self.payload[
                "schema"
            ],
            SCHEMA,
        )

        self.assertEqual(
            self.payload[
                "resolution_id"
            ],
            RESOLUTION_ID,
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
            build_se4_health_model_training_resolution(),
        )

    def test_04_stage_is_se4(self):
        stage = self.payload[
            "stage"
        ]

        self.assertEqual(
            stage[
                "stage_id"
            ],
            "SE4",
        )

        self.assertEqual(
            stage[
                "stage_name"
            ],
            "health_model_training",
        )

    def test_05_se4_not_complete(self):
        self.assertFalse(
            self.payload[
                "stage"
            ][
                "SE4_complete"
            ]
        )

        self.assertFalse(
            self.payload[
                "transition_policy"
            ][
                "SE4_complete"
            ]
        )

    def test_06_health_states_exact(self):
        self.assertEqual(
            tuple(
                self.payload[
                    "health_states"
                ]
            ),
            HEALTH_STATES,
        )

    def test_07_camera_features_bind_se3(self):
        self.assertEqual(
            tuple(
                self.payload[
                    "frozen_diagnostic_inputs"
                ][
                    "camera"
                ][
                    "feature_names"
                ]
            ),
            CAMERA_FEATURES,
        )

    def test_08_imu_features_bind_se3(self):
        self.assertEqual(
            tuple(
                self.payload[
                    "frozen_diagnostic_inputs"
                ][
                    "imu"
                ][
                    "feature_names"
                ]
            ),
            IMU_FEATURES,
        )

    def test_09_lidar_features_preserved(self):
        lidar = self.payload[
            "frozen_diagnostic_inputs"
        ][
            "lidar"
        ]

        self.assertEqual(
            tuple(
                lidar[
                    "feature_names"
                ]
            ),
            LIDAR_FEATURES,
        )

        self.assertFalse(
            lidar[
                "phase4_contract_reopened"
            ]
        )

    def test_10_gnss_remains_optional_unresolved(self):
        gnss = self.payload[
            "frozen_diagnostic_inputs"
        ][
            "gnss"
        ]

        self.assertEqual(
            gnss[
                "role"
            ],
            "optional",
        )

        self.assertFalse(
            gnss[
                "feature_contract_resolved"
            ]
        )

        self.assertEqual(
            gnss[
                "feature_names"
            ],
            [],
        )

    def test_11_historical_phase5_interface_not_rewritten(self):
        historical = self.payload[
            "historical_phase5_interface"
        ]

        self.assertTrue(
            historical[
                "interface_is_hash_frozen"
            ]
        )

        self.assertTrue(
            historical[
                "interface_predates_SE3_exact_camera_IMU_resolution"
            ]
        )

        self.assertFalse(
            historical[
                "historical_artifact_rewritten"
            ]
        )

    def test_12_historical_empty_feature_lists_preserved(self):
        legacy = json.loads(
            LEGACY_INTERFACE.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            legacy[
                "diagnostic_inputs"
            ][
                "camera"
            ][
                "exact_feature_names"
            ],
            [],
        )

        self.assertEqual(
            legacy[
                "diagnostic_inputs"
            ][
                "imu"
            ][
                "exact_feature_names"
            ],
            [],
        )

    def test_13_zero_supervision_sources(self):
        gate = self.payload[
            "supervision_gate"
        ]

        self.assertEqual(
            gate[
                "accepted_baseline_nominality_source_count"
            ],
            0,
        )

        self.assertEqual(
            gate[
                "accepted_health_supervision_source_count"
            ],
            0,
        )

    def test_14_zero_real_health_labels(self):
        self.assertEqual(
            self.payload[
                "supervision_gate"
            ][
                "real_health_label_count"
            ],
            0,
        )

    def test_15_training_label_source_unselected(self):
        self.assertFalse(
            self.payload[
                "supervision_gate"
            ][
                "training_label_source_selected"
            ]
        )

    def test_16_training_unauthorized(self):
        self.assertFalse(
            self.payload[
                "supervision_gate"
            ][
                "classifier_training_authorized"
            ]
        )

        self.assertFalse(
            self.payload[
                "transition_policy"
            ][
                "SE4_training_may_execute"
            ]
        )

    def test_17_training_guard_raises(self):
        with self.assertRaises(
            SE4HealthModelTrainingResolutionError
        ):
            assert_training_execution_authorized(
                self.payload
            )

    def test_18_model_architecture_unselected(self):
        model = self.payload[
            "model_state"
        ]

        self.assertEqual(
            model[
                "classifier_architecture"
            ],
            "unselected",
        )

        self.assertFalse(
            model[
                "classifier_architecture_selected"
            ]
        )

    def test_19_no_model_training_executed(self):
        self.assertFalse(
            self.payload[
                "model_state"
            ][
                "model_training_executed"
            ]
        )

        self.assertIsNone(
            self.payload[
                "model_state"
            ][
                "trained_model_artifact_sha256"
            ]
        )

    def test_20_no_health_outputs_enabled(self):
        model = self.payload[
            "model_state"
        ]

        self.assertFalse(
            model[
                "health_probability_output_enabled"
            ]
        )

        self.assertFalse(
            model[
                "health_state_output_enabled"
            ]
        )

    def test_21_future_grouping_requirements_frozen(self):
        future = self.payload[
            "future_training_requirements"
        ]

        self.assertTrue(
            future[
                "trajectory_grouping_required"
            ]
        )

        self.assertTrue(
            future[
                "derivative_lineage_grouping_required"
            ]
        )

        self.assertTrue(
            future[
                "cross_partition_training_forbidden"
            ]
        )

    def test_22_train_only_partition_access(self):
        access = self.payload[
            "partition_access"
        ]

        self.assertTrue(
            access[
                "train_access"
            ]
        )

        self.assertFalse(
            access[
                "validation_access"
            ]
        )

        self.assertFalse(
            access[
                "confirmation_access"
            ]
        )

        self.assertFalse(
            access[
                "reference_trajectory_access"
            ]
        )

    def test_23_execution_boundary_all_closed(self):
        boundary = self.payload[
            "execution_boundary"
        ]

        self.assertTrue(
            all(
                value is False
                for value
                in boundary.values()
            )
        )

    def test_24_se5_remains_blocked(self):
        self.assertFalse(
            self.payload[
                "transition_policy"
            ][
                "SE5_may_proceed"
            ]
        )

        with self.assertRaises(
            SE4HealthModelTrainingResolutionError
        ):
            assert_se5_entry_authorized(
                self.payload
            )

    def test_25_validation_confirmation_se9_closed(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertTrue(
            transition[
                "validation_remains_closed"
            ]
        )

        self.assertTrue(
            transition[
                "confirmation_remains_closed"
            ]
        )

        self.assertTrue(
            transition[
                "SE9_remains_closed"
            ]
        )

    def test_26_frozen_file_hashes_exact(self):
        self.assertEqual(
            file_sha(
                SE2_FREEZE
            ),
            FROZEN_INPUT_SHA256[
                "SE2_health_supervision_freeze"
            ],
        )

        self.assertEqual(
            file_sha(
                SE3_FREEZE
            ),
            FROZEN_INPUT_SHA256[
                "SE3_multimodal_feature_pipeline_freeze"
            ],
        )

        self.assertEqual(
            file_sha(
                LEGACY_INTERFACE
            ),
            FROZEN_INPUT_SHA256[
                "phase5_multimodal_health_model_interface"
            ],
        )

        self.assertEqual(
            file_sha(
                PHASE5_FREEZE
            ),
            FROZEN_INPUT_SHA256[
                "phase5_multimodal_software_architecture_freeze"
            ],
        )

    def test_27_se3_content_binding_exact(self):
        se3 = json.loads(
            SE3_FREEZE.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            se3[
                "content_sha256"
            ],
            SE3_FREEZE_CONTENT_SHA256,
        )

    def test_28_validator_accepts_only_exact_resolution(self):
        self.assertIs(
            validate_se4_health_model_training_resolution(
                self.payload
            ),
            self.payload,
        )

        changed = deepcopy(
            self.payload
        )

        changed[
            "supervision_gate"
        ][
            "real_health_label_count"
        ] = 1

        with self.assertRaises(
            SE4HealthModelTrainingResolutionError
        ):
            validate_se4_health_model_training_resolution(
                changed
            )

    def test_29_validator_rejects_fake_training_enable(self):
        changed = deepcopy(
            self.payload
        )

        changed[
            "transition_policy"
        ][
            "SE4_training_may_execute"
        ] = True

        with self.assertRaises(
            SE4HealthModelTrainingResolutionError
        ):
            validate_se4_health_model_training_resolution(
                changed
            )

    def test_30_validator_rejects_feature_reselection(self):
        changed = deepcopy(
            self.payload
        )

        changed[
            "frozen_diagnostic_inputs"
        ][
            "camera"
        ][
            "feature_names"
        ] = [
            "invented_feature"
        ]

        with self.assertRaises(
            SE4HealthModelTrainingResolutionError
        ):
            validate_se4_health_model_training_resolution(
                changed
            )

    def test_31_no_ml_training_dependency(self):
        tree = ast.parse(
            MODULE.read_text(
                encoding="utf-8"
            ),
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

        for forbidden in (
            "torch",
            "sklearn",
            "tensorflow",
            "jax",
            "numpy",
        ):
            self.assertFalse(
                any(
                    forbidden
                    in module.lower()
                    for module
                    in modules
                ),
                (
                    forbidden,
                    modules,
                ),
            )

    def test_32_no_fit_predict_classify_api(self):
        tree = ast.parse(
            MODULE.read_text(
                encoding="utf-8"
            ),
            filename=str(
                MODULE
            ),
        )

        names = {
            node.name.lower()
            for node
            in tree.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }

        for forbidden in (
            "fit",
            "train",
            "predict",
            "classify",
            "calibrate",
            "assign_health_label",
        ):
            self.assertNotIn(
                forbidden,
                names,
            )


if __name__ == "__main__":
    unittest.main()
