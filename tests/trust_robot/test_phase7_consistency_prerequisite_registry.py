import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]

MANIFEST = (
    ROOT
    / "manifests"
    / "trust_robot_phase7_consistency_prerequisite_registry_v1.json"
)


class TestPhase7ConsistencyPrerequisiteRegistry(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE7_CONSISTENCY_PREREQUISITE_REGISTRY_V1",
        )

    def test_02_family_count(self):
        self.assertEqual(
            self.payload[
                "family_count"
            ],
            6,
        )

    def test_03_exact_family_order(self):
        self.assertEqual(
            [
                item["family"]
                for item in self.payload[
                    "families"
                ]
            ],
            [
                "visual_motion_vs_lidar_motion",
                "inertial_propagation_vs_exteroceptive_odometry",
                "temporal_pose_continuity",
                "kinematic_proprioceptive_motion",
                "platform_motion_bounds",
                "residual_histories",
            ],
        )

    def test_04_all_execution_blocked(self):
        self.assertTrue(
            all(
                item[
                    "execution_ready"
                ] is False
                for item in self.payload[
                    "families"
                ]
            )
        )

    def test_05_no_numeric_measure_selected(self):
        self.assertTrue(
            all(
                item[
                    "numeric_measure_selected"
                ] is False
                for item in self.payload[
                    "families"
                ]
            )
        )

    def test_06_zero_execution_ready_count(self):
        self.assertEqual(
            self.payload[
                "global_readiness"
            ][
                "execution_ready_family_count"
            ],
            0,
        )

    def test_07_zero_numeric_measure_count(self):
        self.assertEqual(
            self.payload[
                "global_readiness"
            ][
                "numeric_measure_selected_family_count"
            ],
            0,
        )

    def test_08_source_attribution_blocked(self):
        self.assertFalse(
            self.payload[
                "global_readiness"
            ][
                "source_attribution_authorized"
            ]
        )

    def test_09_sync_unselected(self):
        self.assertFalse(
            self.payload[
                "protocol_blockers"
            ][
                "synchronization_selected"
            ]
        )

    def test_10_tolerance_unselected(self):
        self.assertFalse(
            self.payload[
                "protocol_blockers"
            ][
                "temporal_tolerance_selected"
            ]
        )

    def test_11_offset_unselected(self):
        self.assertFalse(
            self.payload[
                "protocol_blockers"
            ][
                "time_offset_selected"
            ]
        )

    def test_12_interpolation_unselected(self):
        self.assertFalse(
            self.payload[
                "protocol_blockers"
            ][
                "interpolation_selected"
            ]
        )

    def test_13_alignment_unauthorized(self):
        self.assertFalse(
            self.payload[
                "protocol_blockers"
            ][
                "alignment_execution_authorized"
            ]
        )

    def test_14_visual_frontend_absent(self):
        self.assertFalse(
            self.payload[
                "phase5_diagnostic_blockers"
            ][
                "visual_frontend_diagnostics_implemented"
            ]
        )

    def test_15_imu_preintegration_absent(self):
        self.assertFalse(
            self.payload[
                "phase5_diagnostic_blockers"
            ][
                "imu_preintegration_diagnostics_implemented"
            ]
        )

    def test_16_camera_residual_history_absent(self):
        self.assertFalse(
            self.payload[
                "phase5_diagnostic_blockers"
            ][
                "camera_residual_history_implemented"
            ]
        )

    def test_17_imu_residual_history_absent(self):
        self.assertFalse(
            self.payload[
                "phase5_diagnostic_blockers"
            ][
                "imu_residual_history_implemented"
            ]
        )

    def test_18_candidate_matches_not_prerequisites(self):
        self.assertTrue(
            self.payload[
                "interpretation_notes"
            ][
                "candidate_repository_match_is_not_validated_prerequisite"
            ]
        )

    def test_19_proprioception_requires_verification(self):
        self.assertTrue(
            self.payload[
                "interpretation_notes"
            ][
                "candidate_proprioceptive_mentions_are_not_verified_robot_streams"
            ]
        )

    def test_20_motion_bounds_not_trusted(self):
        self.assertTrue(
            self.payload[
                "interpretation_notes"
            ][
                "candidate_motion_bound_mentions_are_not_trusted_numeric_bounds"
            ]
        )

    def test_21_lidar_detection_note(self):
        self.assertTrue(
            self.payload[
                "interpretation_notes"
            ][
                "lidar_source_string_detection_false_does_not_invalidate_phase2_lidar_baseline"
            ]
        )

    def test_22_no_adapter_implemented(self):
        decision = self.payload[
            "implementation_decision"
        ]

        for key, value in decision.items():
            if key == "decision":
                continue

            self.assertFalse(
                value
            )

    def test_23_no_phase8_or_phase9(self):
        boundary = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            boundary[
                "phase8_factor_conditioning_implemented"
            ]
        )

        self.assertFalse(
            boundary[
                "phase9_suppression_recovery_status_implemented"
            ]
        )

    def test_24_no_validation_or_confirmation(self):
        boundary = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            boundary[
                "validation_data_opened"
            ]
        )

        self.assertFalse(
            boundary[
                "confirmation_data_used"
            ]
        )

    def test_25_no_ate_rpe_or_score(self):
        boundary = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            boundary[
                "ate_rpe_computed"
            ]
        )

        self.assertFalse(
            boundary[
                "final_score_computed"
            ]
        )

    def test_26_content_digest(self):
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
