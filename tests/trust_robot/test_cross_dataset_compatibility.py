import copy
import json
from pathlib import Path
import unittest

from trust_robot.cross_dataset_compatibility import (
    CURRENT_PHASE11_GATE,
    CrossDatasetCompatibilityContractError,
    Phase11Lifecycle,
    assert_cross_dataset_evaluation_authorized,
    assert_cross_dataset_recalibration_authorized,
    assert_secondary_dataset_data_open_authorized,
    declared_nonprimary_datasets,
    proposal_level_common_modalities,
    validate_contract_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase11_cross_dataset_compatibility_contract_candidate_v1.json"
)


class TestCrossDatasetCompatibilityContract(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE11_CROSS_DATASET_COMPATIBILITY_CONTRACT_V1",
        )

    def test_02_lifecycle(self):
        self.assertEqual(
            self.payload["lifecycle_status"],
            Phase11Lifecycle
            .CONTRACT_IMPLEMENTED_LOCAL_READINESS_UNVERIFIED
            .value,
        )

    def test_03_phase(self):
        self.assertEqual(
            self.payload["phase_scope"]["phase"],
            11,
        )

    def test_04_scope(self):
        self.assertEqual(
            self.payload["phase_scope"]["name"],
            "cross_dataset_evaluation",
        )

    def test_05_evidence_role(self):
        self.assertEqual(
            self.payload["phase_scope"]["evidence_role"],
            "generalization_stress_evidence",
        )

    def test_06_role_not_readiness(self):
        self.assertFalse(
            self.payload[
                "dataset_role_separation"
            ][
                "proposal_level_role_equals_local_readiness"
            ]
        )

    def test_07_role_not_authorization(self):
        self.assertFalse(
            self.payload[
                "dataset_role_separation"
            ][
                "proposal_level_role_equals_evaluation_authorization"
            ]
        )

    def test_08_primary_m2dgr(self):
        self.assertEqual(
            self.payload[
                "primary_dataset"
            ][
                "dataset_id"
            ],
            "M2DGR",
        )

    def test_09_primary_local_path_present(self):
        self.assertTrue(
            self.payload[
                "primary_dataset"
            ][
                "local_path_present"
            ]
        )

    def test_10_declared_nonprimary_exact(self):
        self.assertEqual(
            declared_nonprimary_datasets(),
            (
                "EuRoC",
                "TUM_VI",
            ),
        )

    def test_11_euroc_role(self):
        self.assertEqual(
            self.payload[
                "declared_nonprimary_datasets"
            ][
                "EuRoC"
            ][
                "project_role"
            ],
            [
                "camera_imu_controlled_testing",
                "different_platform_comparison",
            ],
        )

    def test_12_euroc_not_locally_ready(self):
        euroc = self.payload[
            "declared_nonprimary_datasets"
        ][
            "EuRoC"
        ]

        self.assertEqual(
            euroc[
                "local_readiness"
            ],
            "unverified",
        )

        self.assertFalse(
            euroc[
                "local_path_present"
            ]
        )

    def test_13_euroc_not_selected(self):
        self.assertFalse(
            self.payload[
                "declared_nonprimary_datasets"
            ][
                "EuRoC"
            ][
                "evaluation_selected"
            ]
        )

    def test_14_tum_role(self):
        self.assertEqual(
            self.payload[
                "declared_nonprimary_datasets"
            ][
                "TUM_VI"
            ][
                "project_role"
            ],
            [
                "cross_dataset_stress_test",
            ],
        )

    def test_15_tum_cross_dataset_explicit(self):
        self.assertTrue(
            self.payload[
                "declared_nonprimary_datasets"
            ][
                "TUM_VI"
            ][
                "explicit_cross_dataset_stress_role"
            ]
        )

    def test_16_tum_not_locally_ready(self):
        tum = self.payload[
            "declared_nonprimary_datasets"
        ][
            "TUM_VI"
        ]

        self.assertEqual(
            tum[
                "local_readiness"
            ],
            "unverified",
        )

        self.assertFalse(
            tum[
                "local_path_present"
            ]
        )

    def test_17_tum_not_selected(self):
        self.assertFalse(
            self.payload[
                "declared_nonprimary_datasets"
            ][
                "TUM_VI"
            ][
                "evaluation_selected"
            ]
        )

    def test_18_common_modalities(self):
        self.assertEqual(
            proposal_level_common_modalities(),
            (
                "camera",
                "imu",
            ),
        )

    def test_19_overlap_not_verified_compatibility(self):
        overlap = self.payload[
            "proposal_level_modality_overlap"
        ]

        self.assertFalse(
            overlap[
                "common_modalities_are_verified_cross_dataset_compatibility"
            ]
        )

        self.assertFalse(
            overlap[
                "modality_compatibility_verified"
            ]
        )

    def test_20_no_lidar_common_coverage(self):
        self.assertFalse(
            self.payload[
                "proposal_level_modality_overlap"
            ][
                "lidar_common_to_declared_nonprimary_datasets"
            ]
        )

    def test_21_reference_family_unselected(self):
        self.assertFalse(
            self.payload[
                "reference_compatibility_boundary"
            ][
                "reference_family_selected"
            ]
        )

    def test_22_reference_compatibility_unverified(self):
        self.assertFalse(
            self.payload[
                "reference_compatibility_boundary"
            ][
                "reference_compatibility_verified"
            ]
        )

    def test_23_supported_reference_dimensions_only(self):
        self.assertTrue(
            self.payload[
                "reference_compatibility_boundary"
            ][
                "score_only_supported_intervals_and_dimensions"
            ]
        )

    def test_24_no_euroc_leica_rotation(self):
        self.assertFalse(
            self.payload[
                "reference_compatibility_boundary"
            ][
                "eu_ro_c_leica_rotation_may_be_treated_as_ground_truth"
            ]
        )

    def test_25_no_tum_partial_as_full_reference(self):
        self.assertFalse(
            self.payload[
                "reference_compatibility_boundary"
            ][
                "tum_vi_partial_reference_may_be_treated_as_full_trajectory_reference"
            ]
        )

    def test_26_adapter_not_implemented(self):
        self.assertFalse(
            self.payload[
                "adapter_and_time_boundary"
            ][
                "cross_dataset_adapter_implemented"
            ]
        )

    def test_27_raw_timestamp_preservation_required(self):
        self.assertTrue(
            self.payload[
                "adapter_and_time_boundary"
            ][
                "future_adapter_must_preserve_raw_timestamps"
            ]
        )

    def test_28_no_time_assumptions(self):
        boundary = self.payload[
            "adapter_and_time_boundary"
        ]

        self.assertFalse(
            boundary[
                "unknown_time_offset_may_be_assumed"
            ]
        )

        self.assertFalse(
            boundary[
                "unknown_clock_conversion_may_be_assumed"
            ]
        )

        self.assertFalse(
            boundary[
                "interpolation_may_be_assumed"
            ]
        )

    def test_29_timing_and_frames_unverified(self):
        boundary = self.payload[
            "adapter_and_time_boundary"
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

    def test_30_alignment_association_interpolation_unselected(self):
        boundary = self.payload[
            "adapter_and_time_boundary"
        ]

        self.assertFalse(
            boundary[
                "alignment_selected"
            ]
        )

        self.assertFalse(
            boundary[
                "association_selected"
            ]
        )

        self.assertFalse(
            boundary[
                "interpolation_selected"
            ]
        )

    def test_31_secondary_split_unselected(self):
        self.assertFalse(
            self.payload[
                "split_and_transfer_boundary"
            ][
                "secondary_dataset_split_selected"
            ]
        )

    def test_32_zero_shot_recalibrated_separate(self):
        boundary = self.payload[
            "split_and_transfer_boundary"
        ]

        self.assertTrue(
            boundary[
                "zero_shot_transfer_defined_as_separate_reported_condition"
            ]
        )

        self.assertTrue(
            boundary[
                "recalibrated_transfer_defined_as_separate_reported_condition"
            ]
        )

    def test_33_recalibration_anti_leakage_rule(self):
        boundary = self.payload[
            "split_and_transfer_boundary"
        ]

        self.assertTrue(
            boundary[
                "recalibration_if_later_allowed_requires_calibration_only_subset"
            ]
        )

        self.assertTrue(
            boundary[
                "recalibration_subset_must_be_disjoint_from_final_cross_dataset_testing"
            ]
        )

    def test_34_refits_not_authorized(self):
        boundary = self.payload[
            "split_and_transfer_boundary"
        ]

        self.assertFalse(
            boundary[
                "cross_dataset_model_refit_authorized"
            ]
        )

        self.assertFalse(
            boundary[
                "cross_dataset_threshold_refit_authorized"
            ]
        )

        self.assertFalse(
            boundary[
                "cross_dataset_calibration_refit_authorized"
            ]
        )

    def test_35_data_open_guard_raises(self):
        with self.assertRaises(
            CrossDatasetCompatibilityContractError
        ):
            assert_secondary_dataset_data_open_authorized()

    def test_36_recalibration_guard_raises(self):
        with self.assertRaises(
            CrossDatasetCompatibilityContractError
        ):
            assert_cross_dataset_recalibration_authorized()

    def test_37_evaluation_guard_raises(self):
        with self.assertRaises(
            CrossDatasetCompatibilityContractError
        ):
            assert_cross_dataset_evaluation_authorized()

    def test_38_execution_gate_closed(self):
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

    def test_39_manifest_validates(self):
        validate_contract_manifest(
            self.payload
        )

    def test_40_readiness_promotion_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "declared_nonprimary_datasets"
        ][
            "TUM_VI"
        ][
            "local_readiness"
        ] = "verified"

        modified[
            "declared_nonprimary_datasets"
        ][
            "TUM_VI"
        ][
            "local_path_present"
        ] = True

        with self.assertRaises(
            CrossDatasetCompatibilityContractError
        ):
            validate_contract_manifest(
                modified
            )


if __name__ == "__main__":
    unittest.main()
