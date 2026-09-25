from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import ast
import inspect
import json
import unittest

from trust_robot.se4_real_train_runtime_input_binding import (
    SE4RuntimeInputBindingError,
    build_runtime_binding_candidate as build_v1_candidate,
    build_runtime_input_binding_protocol as build_v1_protocol,
)

from trust_robot.se4_real_train_runtime_input_binding_v2 import (
    BINDING_SCHEMA,
    FROZEN_INPUT_SHA256,
    SCHEMA,
    assert_health_supervision_available_v2,
    assert_real_sensor_execution_authorized_v2,
    binding_content_sha256,
    build_runtime_binding_candidate_v2,
    build_runtime_input_binding_protocol_v2,
    protocol_content_sha256,
    validate_runtime_binding_candidate_v2,
    validate_runtime_input_binding_protocol_v2,
)


ROOT = Path(__file__).resolve().parents[2]

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_real_train_runtime_input_binding_v2.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_real_train_runtime_input_binding_v2.json"
)

PARENT_PATHS = {
    "runtime_binding_v1_module":
        ROOT
        / "src/trust_robot/"
        "se4_real_train_runtime_input_binding.py",

    "runtime_binding_v1_config":
        ROOT
        / "configs/trust_robot/"
        "se4_real_train_runtime_input_binding_v1.json",

    "runtime_binding_v1_freeze":
        ROOT
        / "manifests/"
        "trust_robot_se4_real_train_runtime_input_binding_freeze_v1.json",

    "HTTP_executor_module":
        ROOT
        / "src/trust_robot/"
        "se4_http_evidence_executor.py",

    "HTTP_executor_config":
        ROOT
        / "configs/trust_robot/"
        "se4_http_evidence_executor_resolution_v1.json",

    "HTTP_executor_freeze":
        ROOT
        / "manifests/"
        "trust_robot_se4_http_evidence_executor_freeze_v1.json",
}


def file_sha(
    path,
):
    return sha256(
        path.read_bytes()
    ).hexdigest()


def synthetic_v2(
    **changes,
):
    values = {
        "acquisition_session_id":
            "SYNTHETIC_V2_RUNTIME_BINDING",

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

        "http_port":
            8080,

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

    return build_runtime_binding_candidate_v2(
        **values
    )


class SE4RealTrainRuntimeInputBindingV2Tests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

    def test_01_schema(self):
        self.assertEqual(
            self.payload[
                "schema"
            ],
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
            build_runtime_input_binding_protocol_v2(),
        )

    def test_04_parent_V1_preserved(self):
        parent = self.payload[
            "parent_contract"
        ]

        self.assertTrue(
            parent[
                "V1_preserved_unchanged"
            ]
        )

    def test_05_parent_hashes_exact(self):
        for key, path in PARENT_PATHS.items():
            self.assertEqual(
                file_sha(
                    path
                ),
                FROZEN_INPUT_SHA256[
                    key
                ],
            )

    def test_06_required_field_count_is_16(self):
        self.assertEqual(
            self.payload[
                "binding_contract"
            ][
                "required_field_count"
            ],
            16,
        )

    def test_07_only_required_field_delta_is_http_port(self):
        v1 = set(
            build_v1_protocol()[
                "binding_contract"
            ][
                "required_fields"
            ]
        )

        v2 = set(
            self.payload[
                "binding_contract"
            ][
                "required_fields"
            ]
        )

        self.assertEqual(
            v2 - v1,
            {
                "http_port",
            },
        )

        self.assertEqual(
            v1 - v2,
            set(),
        )

    def test_08_no_protocol_defaults(self):
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

        self.assertFalse(
            contract[
                "protocol_supplies_physical_HTTP_port_default"
            ]
        )

    def test_09_http_port_required(self):
        self.assertIn(
            "http_port",
            self.payload[
                "binding_contract"
            ][
                "required_fields"
            ],
        )

        self.assertTrue(
            self.payload[
                "binding_contract"
            ][
                "explicit_HTTP_port_required"
            ]
        )

    def test_10_current_real_binding_count_zero(self):
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

    def test_11_current_http_port_is_none(self):
        self.assertIsNone(
            self.payload[
                "current_binding_state"
            ][
                "http_port"
            ]
        )

    def test_12_valid_synthetic_v2_candidate(self):
        binding = synthetic_v2()

        self.assertEqual(
            binding[
                "schema"
            ],
            BINDING_SCHEMA,
        )

        self.assertIs(
            validate_runtime_binding_candidate_v2(
                binding
            ),
            binding,
        )

    def test_13_http_port_is_bound_in_candidate(self):
        binding = synthetic_v2(
            http_port=8088
        )

        self.assertEqual(
            binding[
                "HTTP_binding"
            ][
                "http_port"
            ],
            8088,
        )

    def test_14_binding_digest_is_stable(self):
        binding = synthetic_v2()

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
            synthetic_v2(),
        )

    def test_15_http_port_zero_rejected(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_v2(
                http_port=0
            )

    def test_16_http_port_above_65535_rejected(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_v2(
                http_port=65536
            )

    def test_17_http_port_bool_rejected(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_v2(
                http_port=True
            )

    def test_18_wrong_split_rejected(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            synthetic_v2(
                split="VALIDATION"
            )

    def test_19_V1_candidate_is_not_V2_candidate(self):
        v1 = build_v1_candidate(
            acquisition_session_id=
                "SYNTHETIC_V1",

            split=
                "TRAIN",

            bind_ipv4=
                "192.0.2.10",

            measurement_udp_port=
                25000,

            position_udp_port=
                25001,

            sensor_ipv4=
                "192.0.2.20",

            capture_duration_seconds=
                10,

            absolute_output_root=
                "/synthetic/trust_robot/runtime",

            http_connect_timeout_seconds=
                2,

            http_total_timeout_seconds=
                5,

            vlp32c_destination_ipv4=
                "192.0.2.10",

            vlp32c_measurement_destination_udp_port=
                25000,

            vlp32c_position_destination_udp_port=
                25001,

            vlp32c_destination_configuration_verified=
                True,

            declared_before_execution=
                True,
        )

        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            validate_runtime_binding_candidate_v2(
                v1
            )

    def test_20_validator_accepts_exact_candidate(self):
        binding = synthetic_v2()

        self.assertEqual(
            validate_runtime_binding_candidate_v2(
                binding
            ),
            binding,
        )

    def test_21_tampered_candidate_rejected(self):
        changed = deepcopy(
            synthetic_v2()
        )

        changed[
            "HTTP_binding"
        ][
            "http_port"
        ] = 8081

        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            validate_runtime_binding_candidate_v2(
                changed
            )

    def test_22_binding_is_not_execution_authorization(self):
        binding = synthetic_v2()

        self.assertFalse(
            binding[
                "scientific_boundary"
            ][
                "execution_authorized"
            ]
        )

    def test_23_binding_creates_no_health_labels(self):
        science = synthetic_v2()[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "health_label_generation_authorized"
            ]
        )

        self.assertEqual(
            science[
                "real_health_label_count"
            ],
            0,
        )

    def test_24_protocol_execution_remains_unauthorized(self):
        self.assertFalse(
            self.payload[
                "transition_policy"
            ][
                "real_sensor_execution_authorized"
            ]
        )

    def test_25_SE4_remains_incomplete(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertFalse(
            transition[
                "SE4_complete"
            ]
        )

        self.assertFalse(
            transition[
                "SE4_training_authorized"
            ]
        )

        self.assertFalse(
            transition[
                "SE5_may_proceed"
            ]
        )

    def test_26_validation_confirmation_closed(self):
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

    def test_27_HTTP_cross_contract_gap_resolved(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertTrue(
            transition[
                "HTTP_port_cross_contract_gap_resolved"
            ]
        )

        self.assertTrue(
            transition[
                "HTTP_execution_software_implemented"
            ]
        )

    def test_28_no_network_execution_imports(self):
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
            "urllib",
            "requests",
            "http.client",
        ):
            self.assertFalse(
                any(
                    forbidden
                    in value.lower()
                    for value in imported
                ),
                (
                    forbidden,
                    imported,
                ),
            )

    def test_29_no_execute_train_predict_API(self):
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
            "train",
            "fit",
            "predict",
            "accept_source",
            "assign_health_label",
        ):
            self.assertNotIn(
                forbidden,
                names,
            )

    def test_30_all_V1_required_fields_preserved(self):
        v1_fields = set(
            build_v1_protocol()[
                "binding_contract"
            ][
                "required_fields"
            ]
        )

        v2_fields = set(
            self.payload[
                "binding_contract"
            ][
                "required_fields"
            ]
        )

        self.assertTrue(
            v1_fields.issubset(
                v2_fields
            )
        )

    def test_31_http_port_argument_has_no_default(self):
        parameter = inspect.signature(
            build_runtime_binding_candidate_v2
        ).parameters[
            "http_port"
        ]

        self.assertIs(
            parameter.default,
            inspect.Parameter.empty,
        )

    def test_32_real_execution_guard_fails_closed(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            assert_real_sensor_execution_authorized_v2(
                self.payload
            )

    def test_33_health_supervision_guard_fails_closed(self):
        with self.assertRaises(
            SE4RuntimeInputBindingError
        ):
            assert_health_supervision_available_v2(
                self.payload
            )


if __name__ == "__main__":
    unittest.main()
