from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import ast
import json
import unittest

from trust_robot.se4_supervision_acquisition_mechanism_resolution import (
    FROZEN_INPUT_SHA256,
    HTTP_PATHS,
    RAW_OUTPUT_NAMES,
    SCHEMA,
    SE4SupervisionAcquisitionMechanismResolutionError,
    assert_health_supervision_available,
    assert_live_execution_authorized,
    build_se4_supervision_acquisition_mechanism_resolution,
    content_sha256,
    validate_se4_supervision_acquisition_mechanism_resolution,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_supervision_acquisition_mechanism_resolution_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_supervision_acquisition_mechanism_resolution.py"
)

INPUT_PATHS = {
    "SE4_blocked_frontier_freeze":
        ROOT
        / "manifests/"
        "trust_robot_se4_health_model_training_blocked_frontier_freeze_v1.json",

    "phase5_live_acquisition_plan":
        ROOT
        / "configs/trust_robot/"
        "phase5_live_acquisition_plan_candidate_v1.json",

    "live_acquisition_plan_module":
        ROOT
        / "src/trust_robot/live_acquisition_plan.py",

    "phase5_live_executor_safety":
        ROOT
        / "configs/trust_robot/"
        "phase5_live_executor_safety_candidate_v1.json",

    "live_executor_safety_module":
        ROOT
        / "src/trust_robot/live_executor_safety.py",

    "phase5_acquisition_session_provenance":
        ROOT
        / "configs/trust_robot/"
        "phase5_acquisition_session_provenance_candidate_v1.json",

    "phase5_baseline_nominality_raw_capture":
        ROOT
        / "configs/trust_robot/"
        "phase5_baseline_nominality_raw_capture_candidate_v1.json",
}


def file_sha(path):
    return sha256(
        path.read_bytes()
    ).hexdigest()


class SE4SupervisionAcquisitionMechanismResolutionTests(
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
            self.payload["content_sha256"],
            content_sha256(
                self.payload
            ),
        )

    def test_03_builder_matches_config(self):
        self.assertEqual(
            self.payload,
            build_se4_supervision_acquisition_mechanism_resolution(),
        )

    def test_04_stage_context_remains_blocked(self):
        stage = self.payload[
            "stage_context"
        ]

        self.assertEqual(
            stage["stage_id"],
            "SE4",
        )

        self.assertFalse(
            stage["SE4_complete"]
        )

        self.assertFalse(
            stage[
                "SE4_training_authorized"
            ]
        )

    def test_05_identity_HTTP_mechanism_selected(self):
        value = self.payload[
            "selected_acquisition_mechanisms"
        ][
            "device_identity"
        ]

        self.assertTrue(
            value["selected"]
        )

        self.assertEqual(
            value["request_path"],
            HTTP_PATHS["identity"],
        )

        self.assertEqual(
            value["primary_identity_field"],
            "serial",
        )

    def test_06_status_HTTP_mechanism_selected(self):
        value = self.payload[
            "selected_acquisition_mechanisms"
        ][
            "sensor_status"
        ]

        self.assertTrue(
            value["selected"]
        )

        self.assertEqual(
            value["request_path"],
            HTTP_PATHS["status"],
        )

        self.assertFalse(
            value[
                "establishes_health_label"
            ]
        )

    def test_07_diagnostic_HTTP_mechanism_selected(self):
        value = self.payload[
            "selected_acquisition_mechanisms"
        ][
            "sensor_diagnostic"
        ]

        self.assertTrue(
            value["selected"]
        )

        self.assertEqual(
            value["request_path"],
            HTTP_PATHS["diagnostic"],
        )

        self.assertFalse(
            value[
                "establishes_health_label"
            ]
        )

    def test_08_measurement_udp_capture_selected(self):
        value = self.payload[
            "selected_acquisition_mechanisms"
        ][
            "measurement_packets"
        ]

        self.assertTrue(
            value["selected"]
        )

        self.assertEqual(
            value["preservation"],
            "classic_pcap",
        )

        self.assertFalse(
            value["port_value_selected"]
        )

        self.assertFalse(
            value[
                "capture_interface_selected"
            ]
        )

    def test_09_position_udp_capture_selected(self):
        value = self.payload[
            "selected_acquisition_mechanisms"
        ][
            "position_packets"
        ]

        self.assertTrue(
            value["selected"]
        )

        self.assertEqual(
            value["preservation"],
            "classic_pcap",
        )

        self.assertFalse(
            value["port_value_selected"]
        )

    def test_10_raw_output_names_exact(self):
        self.assertEqual(
            self.payload[
                "raw_output_contract"
            ],
            RAW_OUTPUT_NAMES,
        )

    def test_11_no_runtime_defaults(self):
        values = self.payload[
            "required_future_runtime_parameters"
        ]

        self.assertTrue(
            all(
                value
                == "required_no_default"
                or value
                == "required_must_be_TRAIN"
                for value
                in values.values()
            )
        )

    def test_12_real_environment_values_unselected(self):
        values = self.payload[
            "explicitly_unselected_runtime_values"
        ]

        self.assertTrue(
            all(
                value is None
                for value
                in values.values()
            )
        )

    def test_13_split_is_train_only(self):
        self.assertEqual(
            self.payload[
                "required_future_runtime_parameters"
            ][
                "split"
            ],
            "required_must_be_TRAIN",
        )

    def test_14_executor_output_safety_bound(self):
        safety = self.payload[
            "executor_safety_binding"
        ]

        self.assertTrue(
            safety[
                "absolute_output_root_required"
            ]
        )

        self.assertTrue(
            safety[
                "fresh_session_directory_required"
            ]
        )

        self.assertFalse(
            safety[
                "existing_final_artifact_overwrite_allowed"
            ]
        )

        self.assertTrue(
            safety[
                "pre_and_post_publish_sha256_must_match"
            ]
        )

    def test_15_pcap_finalization_receipts_required(self):
        safety = self.payload[
            "executor_safety_binding"
        ]

        self.assertTrue(
            safety[
                "pcap_structural_validation_required"
            ]
        )

        self.assertTrue(
            safety[
                "process_terminal_state_receipt_required"
            ]
        )

        self.assertTrue(
            safety[
                "sigint_request_receipt_required"
            ]
        )

        self.assertTrue(
            safety[
                "kill_after_grace_receipt_required"
            ]
        )

    def test_16_session_provenance_required(self):
        provenance = self.payload[
            "provenance_requirements"
        ]

        self.assertTrue(
            provenance[
                "acquisition_session_identity_required"
            ]
        )

        self.assertTrue(
            provenance[
                "device_serial_identity_required"
            ]
        )

        self.assertTrue(
            provenance[
                "raw_info_response_required"
            ]
        )

        self.assertTrue(
            provenance[
                "prospective_no_intervention_declaration_required"
            ]
        )

    def test_17_host_time_transport_only(self):
        self.assertTrue(
            self.payload[
                "provenance_requirements"
            ][
                "host_times_transport_provenance_only"
            ]
        )

        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "physical_measurement_time_selected"
            ]
        )

    def test_18_no_interval_binding_claim(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "interval_binding_established"
            ]
        )

        self.assertIsNone(
            self.payload[
                "explicitly_unselected_runtime_values"
            ][
                "physical_interval_binding_mechanism"
            ]
        )

    def test_19_no_network_execution(self):
        boundary = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            boundary[
                "network_IO_executed"
            ]
        )

        self.assertFalse(
            boundary[
                "subprocess_executed"
            ]
        )

        self.assertFalse(
            boundary[
                "live_sensor_probe_executed"
            ]
        )

    def test_20_zero_real_artifacts_and_receipts(self):
        boundary = self.payload[
            "scientific_boundary"
        ]

        self.assertEqual(
            boundary[
                "raw_capture_artifact_count"
            ],
            0,
        )

        self.assertEqual(
            boundary[
                "device_identity_receipt_count"
            ],
            0,
        )

    def test_21_no_source_acceptance_or_labels(self):
        boundary = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            boundary[
                "baseline_nominality_source_accepted"
            ]
        )

        self.assertFalse(
            boundary[
                "health_supervision_source_accepted"
            ]
        )

        self.assertEqual(
            boundary[
                "real_health_label_count"
            ],
            0,
        )

    def test_22_training_still_blocked(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "classifier_training_authorized"
            ]
        )

        self.assertFalse(
            self.payload[
                "transition_policy"
            ][
                "SE4_training_authorized"
            ]
        )

    def test_23_live_execution_still_blocked(self):
        self.assertFalse(
            self.payload[
                "transition_policy"
            ][
                "live_execution_authorized"
            ]
        )

        with self.assertRaises(
            SE4SupervisionAcquisitionMechanismResolutionError
        ):
            assert_live_execution_authorized(
                self.payload
            )

    def test_24_health_supervision_still_unavailable(self):
        with self.assertRaises(
            SE4SupervisionAcquisitionMechanismResolutionError
        ):
            assert_health_supervision_available(
                self.payload
            )

    def test_25_SE5_validation_confirmation_closed(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertFalse(
            transition[
                "SE5_may_proceed"
            ]
        )

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

    def test_26_input_hashes_exact(self):
        for key, path in INPUT_PATHS.items():
            self.assertEqual(
                file_sha(path),
                FROZEN_INPUT_SHA256[key],
            )

    def test_27_validator_accepts_exact_payload(self):
        self.assertIs(
            validate_se4_supervision_acquisition_mechanism_resolution(
                self.payload
            ),
            self.payload,
        )

    def test_28_validator_rejects_fake_sensor_address(self):
        changed = deepcopy(
            self.payload
        )

        changed[
            "explicitly_unselected_runtime_values"
        ][
            "sensor_ipv4"
        ] = "192.0.2.10"

        with self.assertRaises(
            SE4SupervisionAcquisitionMechanismResolutionError
        ):
            validate_se4_supervision_acquisition_mechanism_resolution(
                changed
            )

    def test_29_validator_rejects_fake_execution_authorization(self):
        changed = deepcopy(
            self.payload
        )

        changed[
            "transition_policy"
        ][
            "live_execution_authorized"
        ] = True

        with self.assertRaises(
            SE4SupervisionAcquisitionMechanismResolutionError
        ):
            validate_se4_supervision_acquisition_mechanism_resolution(
                changed
            )

    def test_30_no_network_or_subprocess_imports(self):
        tree = ast.parse(
            MODULE.read_text(
                encoding="utf-8"
            ),
            filename=str(MODULE),
        )

        modules = []

        for node in ast.walk(tree):
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
            "socket",
            "subprocess",
            "requests",
            "urllib",
            "http.client",
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

    def test_31_no_execute_accept_or_label_API(self):
        tree = ast.parse(
            MODULE.read_text(
                encoding="utf-8"
            ),
            filename=str(MODULE),
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
            "execute",
            "run_capture",
            "accept_source",
            "accept_supervision_source",
            "assign_health_label",
            "train",
            "fit",
            "predict",
        ):
            self.assertNotIn(
                forbidden,
                names,
            )


if __name__ == "__main__":
    unittest.main()
