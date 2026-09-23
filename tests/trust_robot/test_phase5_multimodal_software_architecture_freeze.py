import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_phase5_multimodal_software_architecture_freeze_v1.json"
)


class TestPhase5MultimodalSoftwareArchitectureFreeze(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            MANIFEST.read_text(
                encoding="utf-8"
            )
        )

    def test_01_schema(self):
        self.assertEqual(
            self.payload["schema"],
            "TRUST_ROBOT_PHASE5_MULTIMODAL_SOFTWARE_ARCHITECTURE_FREEZE_V1",
        )

    def test_02_phase(self):
        self.assertEqual(
            self.payload[
                "checkpoint_semantics"
            ]["phase"],
            5,
        )

    def test_03_software_implemented(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "software_architecture_implemented"
            ]
        )

    def test_04_empirical_not_complete(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "empirical_health_model_complete"
            ]
        )

    def test_05_no_empirical_completion_claim(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "empirical_completion_claimed"
            ]
        )

    def test_06_physical_validation_deferred(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "physical_validation_deferred"
            ]
        )

    def test_07_confirmation_closed(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "confirmation_remains_closed"
            ]
        )

    def test_08_pre_freeze_path_count(self):
        self.assertEqual(
            self.payload[
                "closure_evidence"
            ][
                "pre_freeze_repository_path_count"
            ],
            63,
        )

    def test_09_pre_freeze_inventory_count(self):
        self.assertEqual(
            len(
                self.payload[
                    "closure_evidence"
                ][
                    "pre_freeze_artifact_sha256"
                ]
            ),
            63,
        )

    def test_10_core_modalities(self):
        self.assertEqual(
            self.payload[
                "multimodal_architecture"
            ][
                "core_modalities"
            ],
            [
                "camera",
                "imu",
                "lidar",
            ],
        )

    def test_11_gnss_optional(self):
        self.assertEqual(
            self.payload[
                "multimodal_architecture"
            ][
                "optional_modalities"
            ],
            ["gnss"],
        )

    def test_12_three_health_states(self):
        self.assertEqual(
            self.payload[
                "multimodal_architecture"
            ][
                "health_states"
            ],
            [
                "healthy",
                "degraded",
                "unusable",
            ],
        )

    def test_13_camera_channels(self):
        self.assertEqual(
            self.payload[
                "multimodal_architecture"
            ][
                "camera_persistent_health_channels"
            ],
            [
                "low_level_signal_summary",
                "frontend_diagnostic",
                "residual_history",
            ],
        )

    def test_14_imu_channels(self):
        self.assertEqual(
            self.payload[
                "multimodal_architecture"
            ][
                "imu_persistent_health_channels"
            ],
            [
                "low_level_signal_summary",
                "frontend_diagnostic",
                "residual_history",
            ],
        )

    def test_15_lidar_validated(self):
        self.assertTrue(
            self.payload[
                "multimodal_architecture"
            ][
                "lidar_phase4_feature_contract_validated"
            ]
        )

    def test_16_lidar_not_reopened(self):
        self.assertFalse(
            self.payload[
                "multimodal_architecture"
            ][
                "lidar_phase4_feature_contract_reopened"
            ]
        )

    def test_17_zero_baseline_sources(self):
        self.assertEqual(
            self.payload[
                "current_empirical_gate"
            ][
                "accepted_baseline_nominality_source_count"
            ],
            0,
        )

    def test_18_zero_supervision_sources(self):
        self.assertEqual(
            self.payload[
                "current_empirical_gate"
            ][
                "accepted_health_supervision_source_count"
            ],
            0,
        )

    def test_19_zero_health_labels(self):
        self.assertEqual(
            self.payload[
                "current_empirical_gate"
            ][
                "real_health_label_count"
            ],
            0,
        )

    def test_20_training_blocked(self):
        self.assertFalse(
            self.payload[
                "current_empirical_gate"
            ][
                "classifier_training_authorized"
            ]
        )

    def test_21_inference_blocked(self):
        self.assertFalse(
            self.payload[
                "current_empirical_gate"
            ][
                "health_inference_authorized"
            ]
        )

    def test_22_availability_not_health(self):
        self.assertFalse(
            self.payload[
                "protected_scientific_boundaries"
            ][
                "availability_is_health_label"
            ]
        )

    def test_23_missing_not_zero_vector(self):
        self.assertFalse(
            self.payload[
                "protected_scientific_boundaries"
            ][
                "missing_measurement_encoded_as_zero_feature_vector"
            ]
        )

    def test_24_confirmation_selection_blocked(self):
        self.assertFalse(
            self.payload[
                "protected_scientific_boundaries"
            ][
                "confirmation_selection_authorized"
            ]
        )

    def test_25_no_ate_rpe(self):
        self.assertFalse(
            self.payload[
                "protected_scientific_boundaries"
            ][
                "ate_rpe_computation_authorized"
            ]
        )

    def test_26_phase6_cannot_assume_empirical_completion(self):
        self.assertFalse(
            self.payload[
                "next_phase_policy"
            ][
                "phase6_may_assume_empirical_phase5_completion"
            ]
        )

    def test_27_deferred_obligations_present(self):
        self.assertGreaterEqual(
            len(
                self.payload[
                    "deferred_empirical_obligations"
                ]
            ),
            10,
        )

    def test_28_content_digest(self):
        payload = copy.deepcopy(
            self.payload
        )

        stored = payload.pop(
            "content_sha256"
        )

        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode(
            "utf-8"
        )

        self.assertEqual(
            stored,
            sha256(
                canonical
            ).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
