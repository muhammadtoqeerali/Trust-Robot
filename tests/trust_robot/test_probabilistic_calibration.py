import copy
import json
from pathlib import Path
import unittest

from trust_robot.probabilistic_calibration import (
    CURRENT_CALIBRATION_GATE,
    CalibrationKind,
    CalibrationLifecycle,
    CalibrationMechanism,
    ProbabilisticCalibrationError,
    assert_calibrated_output_authorized,
    assert_calibration_execution_authorized,
    validate_contract_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs"
    / "trust_robot"
    / "phase6_probabilistic_calibration_contract_candidate_v1.json"
)


class TestProbabilisticCalibrationContract(unittest.TestCase):

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
            "TRUST_ROBOT_PHASE6_PROBABILISTIC_CALIBRATION_CONTRACT_V1",
        )

    def test_02_lifecycle(self):
        self.assertEqual(
            self.payload["lifecycle_status"],
            CalibrationLifecycle
            .CONTRACT_IMPLEMENTED_INPUTS_UNAVAILABLE
            .value,
        )

    def test_03_kind(self):
        self.assertEqual(
            self.payload[
                "calibration_scope"
            ]["kind"],
            CalibrationKind
            .MODALITY_HEALTH_PROBABILITY
            .value,
        )

    def test_04_temperature_scaling(self):
        self.assertEqual(
            self.payload[
                "proposal_mechanism_contract"
            ]["mechanism"],
            CalibrationMechanism
            .TEMPERATURE_SCALING
            .value,
        )

    def test_05_proposal_mechanism_declared(self):
        self.assertTrue(
            self.payload[
                "proposal_mechanism_contract"
            ][
                "proposal_mechanism_declared"
            ]
        )

    def test_06_method_not_selected_from_validation_outcomes(self):
        self.assertFalse(
            self.payload[
                "proposal_mechanism_contract"
            ][
                "mechanism_selected_from_validation_outcomes"
            ]
        )

    def test_07_no_candidate_method_comparison(self):
        self.assertFalse(
            self.payload[
                "proposal_mechanism_contract"
            ][
                "candidate_method_comparison_performed"
            ]
        )

    def test_08_input_representation_unselected(self):
        self.assertEqual(
            self.payload[
                "proposal_mechanism_contract"
            ][
                "input_representation"
            ],
            "unselected",
        )

    def test_09_objective_unselected(self):
        self.assertEqual(
            self.payload[
                "proposal_mechanism_contract"
            ][
                "optimization_objective"
            ],
            "unselected",
        )

    def test_10_no_calibration_quality_metrics(self):
        self.assertEqual(
            self.payload[
                "proposal_mechanism_contract"
            ][
                "calibration_quality_metrics"
            ],
            [],
        )

    def test_11_temperature_scope_unselected(self):
        self.assertEqual(
            self.payload[
                "proposal_mechanism_contract"
            ][
                "temperature_scope"
            ],
            "unselected",
        )

    def test_12_temperature_parameter_none(self):
        self.assertIsNone(
            self.payload[
                "proposal_mechanism_contract"
            ][
                "temperature_parameter"
            ]
        )

    def test_13_temperature_not_selected(self):
        self.assertFalse(
            self.payload[
                "proposal_mechanism_contract"
            ][
                "temperature_parameter_selected"
            ]
        )

    def test_14_no_fit(self):
        self.assertFalse(
            self.payload[
                "proposal_mechanism_contract"
            ][
                "parameter_fit_performed"
            ]
        )

    def test_15_validation_partition(self):
        self.assertEqual(
            self.payload[
                "selection_partition"
            ]["partition"],
            "validation_calibration",
        )

    def test_16_validation_count(self):
        self.assertEqual(
            self.payload[
                "selection_partition"
            ]["trajectory_count"],
            7,
        )

    def test_17_validation_partition_frozen(self):
        self.assertTrue(
            self.payload[
                "selection_partition"
            ]["partition_frozen"]
        )

    def test_18_validation_only(self):
        self.assertTrue(
            self.payload[
                "selection_partition"
            ][
                "validation_only_selection_required"
            ]
        )

    def test_19_validation_bags_not_authorized_yet(self):
        self.assertFalse(
            self.payload[
                "selection_partition"
            ][
                "bags_open_authorized_in_current_state"
            ]
        )

    def test_20_physical_fact_not_created_by_validation(self):
        self.assertTrue(
            self.payload[
                "selection_partition"
            ][
                "physical_fact_cannot_be_created_by_validation_selection"
            ]
        )

    def test_21_confirmation_closed(self):
        self.assertTrue(
            self.payload[
                "confirmation_boundary"
            ]["closed"]
        )

    def test_22_confirmation_cannot_select_temperature(self):
        self.assertFalse(
            self.payload[
                "confirmation_boundary"
            ][
                "may_select_temperature_parameter"
            ]
        )

    def test_23_phase5_empirical_model_incomplete(self):
        self.assertFalse(
            CURRENT_CALIBRATION_GATE
            .phase5_empirical_health_model_complete
        )

    def test_24_no_trained_model(self):
        self.assertFalse(
            CURRENT_CALIBRATION_GATE
            .trained_health_model_available
        )

    def test_25_no_uncalibrated_outputs(self):
        self.assertFalse(
            CURRENT_CALIBRATION_GATE
            .uncalibrated_health_model_outputs_available
        )

    def test_26_no_admissible_labels(self):
        self.assertFalse(
            CURRENT_CALIBRATION_GATE
            .admissible_health_labels_available
        )

    def test_27_no_validation_inputs(self):
        self.assertFalse(
            CURRENT_CALIBRATION_GATE
            .validation_calibration_inputs_available
        )

    def test_28_execution_not_authorized(self):
        self.assertFalse(
            CURRENT_CALIBRATION_GATE
            .calibration_execution_authorized
        )

    def test_29_calibrated_output_not_authorized(self):
        self.assertFalse(
            CURRENT_CALIBRATION_GATE
            .calibrated_output_authorized
        )

    def test_30_execution_guard_raises(self):
        with self.assertRaises(
            ProbabilisticCalibrationError
        ):
            assert_calibration_execution_authorized()

    def test_31_output_guard_raises(self):
        with self.assertRaises(
            ProbabilisticCalibrationError
        ):
            assert_calibrated_output_authorized()

    def test_32_health_threshold_unselected(self):
        self.assertFalse(
            self.payload[
                "operating_point_separation"
            ][
                "health_threshold_selected"
            ]
        )

    def test_33_health_threshold_none(self):
        self.assertIsNone(
            self.payload[
                "operating_point_separation"
            ][
                "health_threshold"
            ]
        )

    def test_34_suppression_threshold_unselected(self):
        self.assertFalse(
            self.payload[
                "operating_point_separation"
            ][
                "suppression_threshold_selected"
            ]
        )

    def test_35_no_reference_data(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "reference_data_used"
            ]
        )

    def test_36_no_ate_rpe(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "ate_rpe_computation_authorized"
            ]
        )

    def test_37_sensor_geometry_not_modified(self):
        self.assertFalse(
            self.payload[
                "calibration_scope"
            ][
                "sensor_geometry_calibration"
            ]
        )

    def test_38_manifest_validates(self):
        validate_contract_manifest(
            self.payload
        )

    def test_39_temperature_injection_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "proposal_mechanism_contract"
        ][
            "temperature_parameter"
        ] = 1.0

        modified[
            "proposal_mechanism_contract"
        ][
            "temperature_parameter_selected"
        ] = True

        with self.assertRaises(
            ProbabilisticCalibrationError
        ):
            validate_contract_manifest(
                modified
            )

    def test_40_confirmation_unlock_rejected(self):
        modified = copy.deepcopy(
            self.payload
        )

        modified[
            "confirmation_boundary"
        ][
            "selection_authorized"
        ] = True

        with self.assertRaises(
            ProbabilisticCalibrationError
        ):
            validate_contract_manifest(
                modified
            )


if __name__ == "__main__":
    unittest.main()
