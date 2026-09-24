import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_phase11_cross_dataset_compatibility_software_freeze_v1.json"
)


class TestPhase11CrossDatasetCompatibilitySoftwareFreeze(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            MANIFEST.read_text(
                encoding="utf-8"
            )
        )

    def test_01_schema(self):
        self.assertEqual(
            self.payload[
                "schema"
            ],
            "TRUST_ROBOT_PHASE11_CROSS_DATASET_COMPATIBILITY_SOFTWARE_FREEZE_V1",
        )

    def test_02_phase(self):
        self.assertEqual(
            self.payload[
                "checkpoint_semantics"
            ][
                "phase"
            ],
            11,
        )

    def test_03_architecture_implemented(self):
        self.assertTrue(
            self.payload[
                "checkpoint_semantics"
            ][
                "software_architecture_implemented"
            ]
        )

    def test_04_empirical_cross_dataset_incomplete(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "empirical_cross_dataset_evidence_complete"
            ]
        )

    def test_05_euroc_unavailable(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "euroc_evaluation_available"
            ]
        )

    def test_06_tum_vi_unavailable(self):
        self.assertFalse(
            self.payload[
                "checkpoint_semantics"
            ][
                "tum_vi_evaluation_available"
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

    def test_08_m2dgr_primary(self):
        self.assertEqual(
            self.payload[
                "dataset_roles"
            ][
                "M2DGR"
            ][
                "role"
            ],
            "primary_development_benchmark",
        )

    def test_09_euroc_role(self):
        self.assertEqual(
            self.payload[
                "dataset_roles"
            ][
                "EuRoC"
            ][
                "roles"
            ],
            [
                "camera_imu_controlled_testing",
                "different_platform_comparison",
            ],
        )

    def test_10_tum_vi_role(self):
        self.assertEqual(
            self.payload[
                "dataset_roles"
            ][
                "TUM_VI"
            ][
                "roles"
            ],
            [
                "cross_dataset_stress_test",
            ],
        )

    def test_11_secondary_local_readiness_unverified(self):
        self.assertFalse(
            self.payload[
                "dataset_roles"
            ][
                "EuRoC"
            ][
                "local_readiness_verified"
            ]
        )

        self.assertFalse(
            self.payload[
                "dataset_roles"
            ][
                "TUM_VI"
            ][
                "local_readiness_verified"
            ]
        )

    def test_12_secondary_not_selected_or_opened(self):
        for name in (
            "EuRoC",
            "TUM_VI",
        ):
            value = self.payload[
                "dataset_roles"
            ][
                name
            ]

            self.assertFalse(
                value[
                    "evaluation_selected"
                ]
            )

            self.assertFalse(
                value[
                    "data_opened"
                ]
            )

    def test_13_common_modalities(self):
        self.assertEqual(
            self.payload[
                "modality_compatibility_boundary"
            ][
                "proposal_level_common_modalities"
            ],
            [
                "camera",
                "imu",
            ],
        )

    def test_14_overlap_not_verified_compatibility(self):
        self.assertFalse(
            self.payload[
                "modality_compatibility_boundary"
            ][
                "proposal_overlap_is_verified_compatibility"
            ]
        )

    def test_15_no_common_lidar_claim(self):
        self.assertFalse(
            self.payload[
                "modality_compatibility_boundary"
            ][
                "lidar_common_to_declared_nonprimary_datasets"
            ]
        )

    def test_16_reference_unverified(self):
        boundary = self.payload[
            "reference_boundary"
        ]

        self.assertFalse(
            boundary[
                "reference_family_selected"
            ]
        )

        self.assertFalse(
            boundary[
                "reference_compatibility_verified"
            ]
        )

    def test_17_reference_dimensions_restricted(self):
        self.assertTrue(
            self.payload[
                "reference_boundary"
            ][
                "score_only_supported_intervals_and_dimensions"
            ]
        )

    def test_18_adapter_not_implemented(self):
        self.assertFalse(
            self.payload[
                "adapter_time_frame_boundary"
            ][
                "cross_dataset_adapter_implemented"
            ]
        )

    def test_19_raw_timestamp_preservation_required(self):
        self.assertTrue(
            self.payload[
                "adapter_time_frame_boundary"
            ][
                "future_adapter_must_preserve_raw_timestamps"
            ]
        )

    def test_20_timing_and_frames_unverified(self):
        boundary = self.payload[
            "adapter_time_frame_boundary"
        ]

        self.assertFalse(
            boundary[
                "timing_semantics_verified"
            ]
        )

        self.assertFalse(
            boundary[
                "frame_semantics_verified"
            ]
        )

    def test_21_transfer_conditions_separate(self):
        boundary = self.payload[
            "split_transfer_boundary"
        ]

        self.assertTrue(
            boundary[
                "zero_shot_transfer_reported_separately"
            ]
        )

        self.assertTrue(
            boundary[
                "recalibrated_transfer_reported_separately"
            ]
        )

    def test_22_recalibration_and_refits_blocked(self):
        boundary = self.payload[
            "split_transfer_boundary"
        ]

        for key in (
            "cross_dataset_recalibration_authorized",
            "cross_dataset_model_refit_authorized",
            "cross_dataset_threshold_refit_authorized",
            "cross_dataset_calibration_refit_authorized",
        ):
            self.assertFalse(
                boundary[
                    key
                ]
            )

    def test_23_execution_gate_closed(self):
        self.assertEqual(
            set(
                self.payload[
                    "execution_gate"
                ].values()
            ),
            {
                False,
            },
        )

    def test_24_content_digest(self):
        value = copy.deepcopy(
            self.payload
        )

        stored = value.pop(
            "content_sha256"
        )

        canonical = json.dumps(
            value,
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
