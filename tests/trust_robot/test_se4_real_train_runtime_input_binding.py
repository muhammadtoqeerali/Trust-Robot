from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import ast
import json
import unittest

from trust_robot.se4_real_train_runtime_input_binding import (
    BINDING_SCHEMA,
    FROZEN_INPUT_SHA256,
    SCHEMA,
    SE4RuntimeInputBindingError,
    assert_health_supervision_available,
    assert_real_sensor_execution_authorized,
    binding_content_sha256,
    build_runtime_binding_candidate,
    build_runtime_input_binding_protocol,
    protocol_content_sha256,
    validate_runtime_binding_candidate,
    validate_runtime_input_binding_protocol,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_real_train_runtime_input_binding_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_real_train_runtime_input_binding.py"
)

INPUT_PATHS = {
    "SE4_live_execution_transport_freeze":
        ROOT
        / "manifests/"
        "trust_robot_se4_live_execution_transport_freeze_v1.json",

    "SE4_live_execution_transport_config":
        ROOT
        / "configs/trust_robot/"
        "se4_live_execution_transport_resolution_v1.json",

    "phase5_unprivileged_udp_receiver_config":
        ROOT
        / "configs/trust_robot/"
        "phase5_unprivileged_udp_receiver_candidate_v1.json",

    "unprivileged_udp_receiver_module":
        ROOT
        / "src/trust_robot/"
        "unprivileged_udp_receiver.py",

    "phase5_live_executor_safety":
        ROOT
        / "configs/trust_robot/"
        "phase5_live_executor_safety_candidate_v1.json",

    "live_executor_safety_module":
        ROOT
        / "src/trust_robot/"
        "live_executor_safety.py",

    "phase5_live_acquisition_plan":
        ROOT
        / "configs/trust_robot/"
        "phase5_live_acquisition_plan_candidate_v1.json",

    "live_acquisition_plan_module":
        ROOT
        / "src/trust_robot/"
        "live_acquisition_plan.py",

    "phase5_acquisition_session_provenance":
        ROOT
        / "configs/trust_robot/"
        "phase5_acquisition_session_provenance_candidate_v1.json",
}


def file_sha(path):
    return sha256(
        path.read_bytes()
    ).hexdigest()


def synthetic_binding(
    **changes,
):
    values = {
        "acquisition_session_id":
            "SYNTHETIC_RUNTIME_BINDING_TEST",

        "split":
            "TRAIN",

        "bind_ipv4":
            "192.0.2.10",

        "measurement_udp_port":
            25000,

        "position_udp_port":
            25001,

        "sensor_ipv4":
            "192.0.2.20",

        "capture_duration_seconds":
            10,

        "absolute_output_root":
            "/synthetic/trust_robot/runtime",

        "http_connect_timeout_seconds":
            2,

        "http_total_timeout_seconds":
            5,

        "vlp32c_destination_ipv4":
            "192.0.2.10",

        "vlp32c_measurement_destination_udp_port":
            25000,

        "vlp32c_position_destination_udp_port":
            25001,

        "vlp32c_destination_configuration_verified":
            True,

        "declared_before_execution":
            True,
    }

    values.update(
        changes
    )

    return build_runtime_binding_candidate(
        **values
    )


class SE4RealTrainRuntimeInputBindingTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

    def test_01_protocol_schema(self):
        self.assertEqual(
            self.payload["schema"],
            SCHEMA,
        )

    def test_02_protocol_content_digest(self):
        self.assertEqual(
            self.payload[
                "content_sha256"
            ],
            protocol_content_sha256(
                self.payload
            ),
        )

    def test_03_builder_matches_config(self):
        self.assertEqual(
            self.payload,
            build_runtime_input_binding_protocol(),
        )

    def test_04_stage_remains_SE4_incomplete(self):
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

    def test_05_required_fields_are_explicit(self):
        required = set(
            self.payload[
                "binding_contract"
            ][
                "required_fields"
            ]
        )

        expected = {
            "acquisition_session_id",
            "split",
            "bind_ipv4",
            "measurement_udp_port",
            "position_udp_port",
            "sensor_ipv4",
            "capture_duration_seconds",
            "absolute_output_root",
            "http_connect_timeout_seconds",
            "http_total_timeout_seconds",
            "vlp32c_destination_ipv4",
            "vlp32c_measurement_destination_udp_port",
            "vlp32c_position_destination_udp_port",
            "vlp32c_destination_configuration_verified",
            "declared_before_execution",
        }

        self.assertEqual(
            required,
            expected,
        )

    def test_06_protocol_supplies_no_runtime_defaults(self):
        contract = self.payload[
            "binding_contract"
        ]

        self.assertTrue(
            contract[
                "all_required_fields_have_no_protocol_default"
            ]
        )

        self.assertTrue(
            contract[
                "runtime_values_must_be_externally_supplied"
            ]
        )

    def test_07_current_binding_state_is_empty(self):
        state = self.payload[
            "current_binding_state"
        ]

        self.assertEqual(
            state[
                "real_runtime_binding_count"
            ],
            0,
        )

        self.assertFalse(
            state[
                "real_runtime_values_bound"
            ]
        )

        for key, value in state.items():
            if key in {
                "real_runtime_binding_count",
                "real_runtime_values_bound",
                "vlp32c_destination_configuration_verified",
            }:
                continue

            self.assertIsNone(
                value,
                key,
            )

    def test_08_train_split_only(self):
        self.assertEqual(
            self.payload[
                "binding_contract"
            ][
                "split_must_be_exactly"
            ],
            "TRAIN",
        )

    def test_09_valid_synthetic_binding(self):
        binding = synthetic_binding()

        self.assertEqual(
            binding[
                "schema"
            ],
            BINDING_SCHEMA,
        )

        self.assertEqual(
            binding[
                "split"
            ],
            "TRAIN",
        )

        self.assertIs(
            validate_runtime_binding_candidate(
                binding
            ),
            binding,
        )

    def test_10_binding_digest_is_stable(self):
        binding = synthetic_binding()

        self.assertEqual(
            binding[
                "binding_sha256"
            ],
            binding_content_sha256(
                binding
            ),
        )

        self.assertEqual(
            binding,
            synthetic_binding(),
        )

    def test_11_runtime_binding_is_not_execution_authorization(self):
        binding = synthetic_binding()

        self.assertFalse(
            binding[
                "scientific_boundary"
            ][
                "execution_authorized"
            ]
        )

        self.assertFalse(
            binding[
                "scientific_boundary"
            ][
                "source_acceptance_authorized"
            ]
        )

    def test_12_wrong_split_rejected(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_binding(
                split="VALIDATION"
            )

    def test_13_invalid_bind_ipv4_rejected(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_binding(
                bind_ipv4="not-an-ip"
            )

    def test_14_invalid_sensor_ipv4_rejected(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_binding(
                sensor_ipv4="127.0.0.1"
            )

    def test_15_udp_ports_must_be_distinct(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_binding(
                position_udp_port=25000,
                vlp32c_position_destination_udp_port=25000,
            )

    def test_16_udp_port_bounds_enforced(self):
        for value in (
            0,
            65536,
            True,
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    SE4RuntimeInputBindingError
                ):
                    synthetic_binding(
                        measurement_udp_port=value
                    )

    def test_17_capture_duration_positive_exact_int(self):
        for value in (
            0,
            -1,
            True,
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    SE4RuntimeInputBindingError
                ):
                    synthetic_binding(
                        capture_duration_seconds=value
                    )

    def test_18_output_root_must_be_absolute(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_binding(
                absolute_output_root="relative/runtime"
            )

    def test_19_session_id_must_be_safe(self):
        for value in (
            "",
            "../SESSION",
            "bad/session",
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    SE4RuntimeInputBindingError
                ):
                    synthetic_binding(
                        acquisition_session_id=value
                    )

    def test_20_http_timeout_constraints(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_binding(
                http_connect_timeout_seconds=0
            )

        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_binding(
                http_connect_timeout_seconds=5,
                http_total_timeout_seconds=4,
            )

    def test_21_destination_ports_must_match_receiver_ports(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_binding(
                vlp32c_measurement_destination_udp_port=26000
            )

        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_binding(
                vlp32c_position_destination_udp_port=26001
            )

    def test_22_specific_bind_requires_matching_destination_ipv4(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_binding(
                vlp32c_destination_ipv4="192.0.2.11"
            )

    def test_23_unspecified_bind_allows_concrete_destination(self):
        binding = synthetic_binding(
            bind_ipv4="0.0.0.0",
            vlp32c_destination_ipv4="192.0.2.10",
        )

        self.assertEqual(
            binding[
                "UDP_receiver_binding"
            ][
                "bind_ipv4"
            ],
            "0.0.0.0",
        )

        validate_runtime_binding_candidate(
            binding
        )

    def test_24_destination_configuration_requires_explicit_verification(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_binding(
                vlp32c_destination_configuration_verified=False
            )

    def test_25_binding_must_be_declared_before_execution(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_binding(
                declared_before_execution=False
            )

    def test_26_binding_creates_no_health_or_interval_semantics(self):
        science = synthetic_binding()[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "health_label_generation_authorized"
            ]
        )

        self.assertFalse(
            science[
                "interval_binding_established"
            ]
        )

        self.assertFalse(
            science[
                "physical_measurement_time_established"
            ]
        )

        self.assertEqual(
            science[
                "real_health_label_count"
            ],
            0,
        )

    def test_27_frozen_input_hashes_exact(self):
        for key, path in INPUT_PATHS.items():
            self.assertEqual(
                file_sha(
                    path
                ),
                FROZEN_INPUT_SHA256[
                    key
                ],
            )

    def test_28_protocol_validator_accepts_exact_config(self):
        self.assertIs(
            validate_runtime_input_binding_protocol(
                self.payload
            ),
            self.payload,
        )

    def test_29_protocol_validator_rejects_fake_runtime_binding(self):
        changed = deepcopy(
            self.payload
        )

        changed[
            "current_binding_state"
        ][
            "bind_ipv4"
        ] = "192.0.2.10"

        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            validate_runtime_input_binding_protocol(
                changed
            )

    def test_30_protocol_validator_rejects_fake_authorization(self):
        changed = deepcopy(
            self.payload
        )

        changed[
            "transition_policy"
        ][
            "real_sensor_execution_authorized"
        ] = True

        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            validate_runtime_input_binding_protocol(
                changed
            )

    def test_31_resolution_module_has_no_network_execution_imports(self):
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
                    for alias
                    in node.names
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
                    in imported
                ),
                (
                    forbidden,
                    imported,
                ),
            )

    def test_32_no_execute_accept_label_train_api(self):
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
            "execute",
            "run",
            "capture",
            "accept_source",
            "assign_health_label",
            "train",
            "fit",
            "predict",
        ):
            self.assertNotIn(
                forbidden,
                names,
            )

    def test_33_real_sensor_execution_remains_blocked(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            assert_real_sensor_execution_authorized(
                self.payload
            )

    def test_34_health_supervision_remains_blocked(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            assert_health_supervision_available(
                self.payload
            )


if __name__ == "__main__":
    unittest.main()
