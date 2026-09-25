from hashlib import sha256
from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests/trust_robot_se2_health_supervision_protocol_freeze_v1.json"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/se2_health_supervision_protocol_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/health_supervision_resolution.py"
)

IMPL_TEST = (
    ROOT
    / "tests/trust_robot/test_se2_health_supervision_protocol.py"
)

PROJECT_STATE = (
    ROOT
    / "docs/TRUST_ROBOT_PROJECT_STATE.md"
)

EXPECTED_MANIFEST_FILE_SHA = "63da52c788208ae715abc7e0b8eb0ba6777cc16d33d90466332779c630618230"
EXPECTED_MANIFEST_CONTENT_SHA = "4dba6de872f3f65bee2ccf526cbc126192c6ea0e06274017332c914a610f38ab"


def file_sha(path):
    return sha256(
        path.read_bytes()
    ).hexdigest()


def canonical_sha(payload):
    value = dict(payload)
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
        ).encode("utf-8")
    ).hexdigest()


class SE2HealthSupervisionProtocolFreezeTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            MANIFEST.read_text(
                encoding="utf-8"
            )
        )

    def test_01_manifest_file_sha(self):
        self.assertEqual(
            file_sha(MANIFEST),
            EXPECTED_MANIFEST_FILE_SHA,
        )

    def test_02_manifest_content_sha(self):
        self.assertEqual(
            self.payload["content_sha256"],
            EXPECTED_MANIFEST_CONTENT_SHA,
        )

        self.assertEqual(
            canonical_sha(self.payload),
            EXPECTED_MANIFEST_CONTENT_SHA,
        )

    def test_03_schema(self):
        self.assertEqual(
            self.payload["schema"],
            "TRUST_ROBOT_SE2_HEALTH_SUPERVISION_PROTOCOL_FREEZE_V1",
        )

    def test_04_stage_identity(self):
        stage = self.payload["stage"]

        self.assertEqual(
            stage["stage_id"],
            "SE2",
        )

        self.assertEqual(
            stage["stage_name"],
            "health_supervision_protocol",
        )

    def test_05_stage_complete(self):
        self.assertEqual(
            self.payload["stage"]["status"],
            "protocol_resolved_and_frozen_ready_for_SE3",
        )

        self.assertTrue(
            self.payload[
                "transition_policy"
            ][
                "SE2_complete"
            ]
        )

    def test_06_parent_commit(self):
        self.assertEqual(
            self.payload[
                "parent_frontier"
            ][
                "commit"
            ],
            "e540b093bae81defa2cb96f777db27595785921d",
        )

    def test_07_parent_tree(self):
        self.assertEqual(
            self.payload[
                "parent_frontier"
            ][
                "tree"
            ],
            "f9a23e51b74f4c00047c3a9921f71e80f9b0e9e7",
        )

    def test_08_implementation_hashes(self):
        implementation = self.payload[
            "implementation"
        ]

        self.assertEqual(
            file_sha(MODULE),
            implementation[
                "module_sha256"
            ],
        )

        self.assertEqual(
            file_sha(CONFIG),
            implementation[
                "config_sha256"
            ],
        )

        self.assertEqual(
            file_sha(IMPL_TEST),
            implementation[
                "implementation_test_sha256"
            ],
        )

    def test_09_protocol_content_hash(self):
        config = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            config[
                "content_sha256"
            ],
            self.payload[
                "implementation"
            ][
                "config_content_sha256"
            ],
        )

    def test_10_three_state_vocabulary(self):
        self.assertEqual(
            self.payload[
                "scientific_resolution"
            ][
                "state_vocabulary"
            ],
            [
                "healthy",
                "degraded",
                "unusable",
            ],
        )

    def test_11_availability_not_health(self):
        self.assertFalse(
            self.payload[
                "scientific_resolution"
            ][
                "availability_is_health_label"
            ]
        )

    def test_12_clean_and_corrupt_identity_not_health(self):
        resolution = self.payload[
            "scientific_resolution"
        ]

        self.assertFalse(
            resolution[
                "clean_identity_alone_is_health_label"
            ]
        )

        self.assertFalse(
            resolution[
                "corruption_identity_alone_is_health_label"
            ]
        )

    def test_13_final_error_not_health(self):
        self.assertFalse(
            self.payload[
                "scientific_resolution"
            ][
                "final_localization_error_is_health_label"
            ]
        )

    def test_14_missing_not_zero_vector(self):
        self.assertFalse(
            self.payload[
                "scientific_resolution"
            ][
                "missing_measurement_is_zero_feature_vector"
            ]
        )

    def test_15_current_source_counts_zero(self):
        readiness = self.payload[
            "current_empirical_readiness"
        ]

        self.assertEqual(
            readiness[
                "accepted_baseline_nominality_source_count"
            ],
            0,
        )

        self.assertEqual(
            readiness[
                "accepted_health_supervision_source_count"
            ],
            0,
        )

    def test_16_current_health_label_count_zero(self):
        self.assertEqual(
            self.payload[
                "current_empirical_readiness"
            ][
                "real_health_label_count"
            ],
            0,
        )

    def test_17_empirical_supervision_unavailable(self):
        readiness = self.payload[
            "current_empirical_readiness"
        ]

        self.assertFalse(
            readiness[
                "empirical_health_supervision_available"
            ]
        )

        self.assertFalse(
            readiness[
                "health_label_generation_authorized"
            ]
        )

    def test_18_train_only_access(self):
        execution = self.payload[
            "execution_status"
        ]

        self.assertTrue(
            execution[
                "train_access"
            ]
        )

        self.assertFalse(
            execution[
                "validation_access"
            ]
        )

        self.assertFalse(
            execution[
                "confirmation_access"
            ]
        )

    def test_19_no_reference_access(self):
        self.assertFalse(
            self.payload[
                "execution_status"
            ][
                "reference_trajectory_access"
            ]
        )

    def test_20_no_training_selection_calibration(self):
        execution = self.payload[
            "execution_status"
        ]

        for key in (
            "feature_selection_executed",
            "model_training_executed",
            "probability_calibration_executed",
            "threshold_selection_executed",
        ):
            self.assertFalse(
                execution[key]
            )

    def test_21_no_ate_rpe_or_final_scoring(self):
        execution = self.payload[
            "execution_status"
        ]

        self.assertFalse(
            execution[
                "ate_rpe_computed"
            ]
        )

        self.assertFalse(
            execution[
                "final_scoring_executed"
            ]
        )

    def test_22_se3_is_next_train_only_stage(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertEqual(
            transition[
                "next_stage"
            ],
            "SE3",
        )

        self.assertEqual(
            transition[
                "next_stage_name"
            ],
            "multimodal_feature_pipeline",
        )

        self.assertTrue(
            transition[
                "SE3_may_proceed"
            ]
        )

        self.assertTrue(
            transition[
                "SE3_train_only"
            ]
        )

    def test_23_se4_training_blocked(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertFalse(
            transition[
                "SE4_model_training_authorized"
            ]
        )

        self.assertTrue(
            transition[
                "SE4_requires_admissible_train_supervision"
            ]
        )

    def test_24_validation_confirmation_and_se9_closed(self):
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


if __name__ == "__main__":
    unittest.main()
