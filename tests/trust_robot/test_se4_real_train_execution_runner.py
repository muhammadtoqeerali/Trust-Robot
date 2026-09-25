from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import ast
import json
import subprocess
import sys
import unittest

from trust_robot.se4_composite_live_session_orchestrator import (
    build_execution_authorization_candidate,
)

from trust_robot.se4_real_train_execution_runner import (
    INPUT_VALIDATION_SCHEMA,
    NETWORK_IO_ACKNOWLEDGEMENT,
    RESOLUTION_SCHEMA,
    SE4RealTrainExecutionRunnerError,
    assert_repository_real_inputs_available,
    build_real_train_execution_runner_resolution,
    execute_real_session_from_files,
    resolution_content_sha256,
    validate_real_execution_inputs_from_files,
    validate_real_train_execution_runner_resolution,
    validation_content_sha256,
)

from trust_robot.se4_real_train_runtime_input_binding_v2 import (
    build_runtime_binding_candidate_v2,
)


ROOT = Path(__file__).resolve().parents[2]

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_real_train_execution_runner.py"
)

RUNNER = (
    ROOT
    / "scripts/trust_robot/"
    "run_se4_real_train_live_session_v1.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_real_train_execution_runner_resolution_v1.json"
)

DEPENDENCIES = {
    ROOT
    / "src/trust_robot/"
    "se4_real_train_runtime_input_binding_v2.py":
        "f00fb0571a9fb4ac1a078a6789941741b68bbf066a7a6f01028f2450bc820212",

    ROOT
    / "manifests/"
    "trust_robot_se4_real_train_runtime_input_binding_v2_freeze_v1.json":
        "81f1d22674a4ca1ef4a8b5c9c4d16e446423eb3e6a76981fa7d6f99b08477388",

    ROOT
    / "src/trust_robot/"
    "se4_composite_live_session_orchestrator.py":
        "ca23e6a2cca37c3af5ebeeae39bfdf6cc4ba4b9669b4a25135e6e15810081b2d",

    ROOT
    / "manifests/"
    "trust_robot_se4_composite_live_session_orchestrator_freeze_v1.json":
        "7ee319bc88c33541923df1d73971a8703af29d177f98a05160a99655a9b51e04",
}


def file_sha(
    path,
):
    return sha256(
        path.read_bytes()
    ).hexdigest()


def write_fixture_set(
    root,
):
    root = Path(
        root
    )

    output_root = (
        root
        / "capture"
    )

    output_root.mkdir()

    binding = build_runtime_binding_candidate_v2(
        acquisition_session_id=
            "SYNTHETIC_FILE_RUNNER",

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
            1,

        absolute_output_root=
            str(
                output_root
            ),

        http_port=
            8080,

        http_connect_timeout_seconds=
            1,

        http_total_timeout_seconds=
            2,

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

    record_path = (
        root
        / "authorization_record.txt"
    )

    record_path.write_text(
        "synthetic authorization record for software-only tests\n",
        encoding="utf-8",
    )

    record_sha = file_sha(
        record_path
    )

    authorization = build_execution_authorization_candidate(
        authorization_id=
            "SYNTHETIC_FILE_RUNNER_AUTH",

        binding_sha256=
            binding[
                "binding_sha256"
            ],

        authorization_record_sha256=
            record_sha,

        authorized_for_real_sensor_execution=
            True,

        declared_before_execution=
            True,
    )

    binding_path = (
        root
        / "binding.json"
    )

    authorization_path = (
        root
        / "authorization.json"
    )

    binding_path.write_text(
        json.dumps(
            binding,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    authorization_path.write_text(
        json.dumps(
            authorization,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "binding":
            binding,

        "authorization":
            authorization,

        "binding_path":
            binding_path,

        "authorization_path":
            authorization_path,

        "record_path":
            record_path,

        "output_root":
            output_root,
    }


class SE4RealTrainExecutionRunnerTests(
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

    def test_01_resolution_schema(self):
        self.assertEqual(
            self.payload[
                "schema"
            ],
            RESOLUTION_SCHEMA,
        )

    def test_02_resolution_digest(self):
        self.assertEqual(
            self.payload[
                "content_sha256"
            ],
            resolution_content_sha256(
                self.payload
            ),
        )

    def test_03_resolution_builder_matches_config(self):
        self.assertEqual(
            self.payload,
            build_real_train_execution_runner_resolution(),
        )

    def test_04_resolution_validator_accepts_config(self):
        self.assertIs(
            validate_real_train_execution_runner_resolution(
                self.payload
            ),
            self.payload,
        )

    def test_05_dependency_hashes_exact(self):
        for path, expected in DEPENDENCIES.items():
            self.assertEqual(
                file_sha(
                    path
                ),
                expected,
            )

    def test_06_required_three_external_files(self):
        self.assertEqual(
            self.payload[
                "input_contract"
            ][
                "required_external_files"
            ],
            [
                "runtime_binding_file",
                "execution_authorization_file",
                "authorization_record_file",
            ],
        )

    def test_07_runner_manufactures_no_runtime_values(self):
        self.assertFalse(
            self.payload[
                "input_contract"
            ][
                "runner_manufactures_runtime_values"
            ]
        )

    def test_08_runner_manufactures_no_authorization(self):
        self.assertFalse(
            self.payload[
                "input_contract"
            ][
                "runner_manufactures_execution_authorization"
            ]
        )

    def test_09_default_validation_only(self):
        self.assertEqual(
            self.payload[
                "execution_gates"
            ][
                "default_mode"
            ],
            "validation_only",
        )

    def test_10_validation_only_no_network(self):
        gates = self.payload[
            "execution_gates"
        ]

        self.assertFalse(
            gates[
                "validation_only_performs_network_IO"
            ]
        )

        self.assertFalse(
            gates[
                "validation_only_contacts_sensor"
            ]
        )

    def test_11_real_switch_required(self):
        self.assertTrue(
            self.payload[
                "execution_gates"
            ][
                "explicit_execute_real_switch_required"
            ]
        )

    def test_12_exact_acknowledgement_frozen(self):
        self.assertEqual(
            self.payload[
                "execution_gates"
            ][
                "network_IO_acknowledgement"
            ],
            NETWORK_IO_ACKNOWLEDGEMENT,
        )

    def test_13_valid_files_validate(self):
        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            result = validate_real_execution_inputs_from_files(
                runtime_binding_file=
                    fixture[
                        "binding_path"
                    ],

                execution_authorization_file=
                    fixture[
                        "authorization_path"
                    ],

                authorization_record_file=
                    fixture[
                        "record_path"
                    ],
            )

            self.assertEqual(
                result[
                    "input_validation"
                ][
                    "schema"
                ],
                INPUT_VALIDATION_SCHEMA,
            )

    def test_14_validation_receipt_digest(self):
        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            receipt = validate_real_execution_inputs_from_files(
                runtime_binding_file=
                    fixture[
                        "binding_path"
                    ],

                execution_authorization_file=
                    fixture[
                        "authorization_path"
                    ],

                authorization_record_file=
                    fixture[
                        "record_path"
                    ],
            )[
                "input_validation"
            ]

            self.assertEqual(
                receipt[
                    "validation_sha256"
                ],
                validation_content_sha256(
                    receipt
                ),
            )

    def test_15_validation_receipt_records_file_hashes(self):
        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            receipt = validate_real_execution_inputs_from_files(
                runtime_binding_file=
                    fixture[
                        "binding_path"
                    ],

                execution_authorization_file=
                    fixture[
                        "authorization_path"
                    ],

                authorization_record_file=
                    fixture[
                        "record_path"
                    ],
            )[
                "input_validation"
            ]

            self.assertEqual(
                receipt[
                    "runtime_binding_file_sha256"
                ],
                file_sha(
                    fixture[
                        "binding_path"
                    ]
                ),
            )

            self.assertEqual(
                receipt[
                    "authorization_record_file_sha256"
                ],
                file_sha(
                    fixture[
                        "record_path"
                    ]
                ),
            )

    def test_16_record_digest_match_true(self):
        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            receipt = validate_real_execution_inputs_from_files(
                runtime_binding_file=
                    fixture[
                        "binding_path"
                    ],

                execution_authorization_file=
                    fixture[
                        "authorization_path"
                    ],

                authorization_record_file=
                    fixture[
                        "record_path"
                    ],
            )[
                "input_validation"
            ]

            self.assertTrue(
                receipt[
                    "authorization_record_digest_matches"
                ]
            )

    def test_17_hash_match_not_proof_of_authority(self):
        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            receipt = validate_real_execution_inputs_from_files(
                runtime_binding_file=
                    fixture[
                        "binding_path"
                    ],

                execution_authorization_file=
                    fixture[
                        "authorization_path"
                    ],

                authorization_record_file=
                    fixture[
                        "record_path"
                    ],
            )[
                "input_validation"
            ]

            self.assertFalse(
                receipt[
                    "authorization_record_digest_proves_authority_or_trust"
                ]
            )

    def test_18_relative_binding_path_rejected(self):
        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            with self.assertRaises(
                SE4RealTrainExecutionRunnerError
            ):
                validate_real_execution_inputs_from_files(
                    runtime_binding_file=
                        "binding.json",

                    execution_authorization_file=
                        fixture[
                            "authorization_path"
                        ],

                    authorization_record_file=
                        fixture[
                            "record_path"
                        ],
                )

    def test_19_missing_binding_file_rejected(self):
        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            with self.assertRaises(
                SE4RealTrainExecutionRunnerError
            ):
                validate_real_execution_inputs_from_files(
                    runtime_binding_file=
                        Path(
                            temp
                        )
                        / "missing.json",

                    execution_authorization_file=
                        fixture[
                            "authorization_path"
                        ],

                    authorization_record_file=
                        fixture[
                            "record_path"
                        ],
                )

    def test_20_non_JSON_binding_rejected(self):
        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            fixture[
                "binding_path"
            ].write_text(
                "not json\n",
                encoding="utf-8",
            )

            with self.assertRaises(
                SE4RealTrainExecutionRunnerError
            ):
                validate_real_execution_inputs_from_files(
                    runtime_binding_file=
                        fixture[
                            "binding_path"
                        ],

                    execution_authorization_file=
                        fixture[
                            "authorization_path"
                        ],

                    authorization_record_file=
                        fixture[
                            "record_path"
                        ],
                )

    def test_21_invalid_binding_rejected(self):
        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            damaged = deepcopy(
                fixture[
                    "binding"
                ]
            )

            damaged[
                "HTTP_binding"
            ][
                "http_port"
            ] = 0

            fixture[
                "binding_path"
            ].write_text(
                json.dumps(
                    damaged
                ),
                encoding="utf-8",
            )

            with self.assertRaises(
                SE4RealTrainExecutionRunnerError
            ):
                validate_real_execution_inputs_from_files(
                    runtime_binding_file=
                        fixture[
                            "binding_path"
                        ],

                    execution_authorization_file=
                        fixture[
                            "authorization_path"
                        ],

                    authorization_record_file=
                        fixture[
                            "record_path"
                        ],
                )

    def test_22_mismatched_authorization_rejected(self):
        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            damaged = deepcopy(
                fixture[
                    "authorization"
                ]
            )

            damaged[
                "binding_sha256"
            ] = "0" * 64

            fixture[
                "authorization_path"
            ].write_text(
                json.dumps(
                    damaged
                ),
                encoding="utf-8",
            )

            with self.assertRaises(
                SE4RealTrainExecutionRunnerError
            ):
                validate_real_execution_inputs_from_files(
                    runtime_binding_file=
                        fixture[
                            "binding_path"
                        ],

                    execution_authorization_file=
                        fixture[
                            "authorization_path"
                        ],

                    authorization_record_file=
                        fixture[
                            "record_path"
                        ],
                )

    def test_23_modified_authorization_record_rejected(self):
        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            fixture[
                "record_path"
            ].write_text(
                "modified\n",
                encoding="utf-8",
            )

            with self.assertRaises(
                SE4RealTrainExecutionRunnerError
            ):
                validate_real_execution_inputs_from_files(
                    runtime_binding_file=
                        fixture[
                            "binding_path"
                        ],

                    execution_authorization_file=
                        fixture[
                            "authorization_path"
                        ],

                    authorization_record_file=
                        fixture[
                            "record_path"
                        ],
                )

    def test_24_same_file_paths_rejected(self):
        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            with self.assertRaises(
                SE4RealTrainExecutionRunnerError
            ):
                validate_real_execution_inputs_from_files(
                    runtime_binding_file=
                        fixture[
                            "binding_path"
                        ],

                    execution_authorization_file=
                        fixture[
                            "binding_path"
                        ],

                    authorization_record_file=
                        fixture[
                            "record_path"
                        ],
                )

    def test_25_symlink_record_rejected(self):
        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            link = (
                Path(
                    temp
                )
                / "record-link"
            )

            link.symlink_to(
                fixture[
                    "record_path"
                ]
            )

            with self.assertRaises(
                SE4RealTrainExecutionRunnerError
            ):
                validate_real_execution_inputs_from_files(
                    runtime_binding_file=
                        fixture[
                            "binding_path"
                        ],

                    execution_authorization_file=
                        fixture[
                            "authorization_path"
                        ],

                    authorization_record_file=
                        link,
                )

    def test_26_execute_false_blocks_before_dispatch(self):
        calls = []

        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            def fake_orchestrator(
                **kwargs,
            ):
                calls.append(
                    kwargs
                )

                return {}

            with self.assertRaises(
                SE4RealTrainExecutionRunnerError
            ):
                execute_real_session_from_files(
                    runtime_binding_file=
                        fixture[
                            "binding_path"
                        ],

                    execution_authorization_file=
                        fixture[
                            "authorization_path"
                        ],

                    authorization_record_file=
                        fixture[
                            "record_path"
                        ],

                    execute_real=
                        False,

                    network_io_acknowledgement=
                        NETWORK_IO_ACKNOWLEDGEMENT,

                    orchestrator_fn=
                        fake_orchestrator,
                )

        self.assertEqual(
            calls,
            [],
        )

    def test_27_wrong_acknowledgement_blocks_dispatch(self):
        calls = []

        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            def fake_orchestrator(
                **kwargs,
            ):
                calls.append(
                    kwargs
                )

                return {}

            with self.assertRaises(
                SE4RealTrainExecutionRunnerError
            ):
                execute_real_session_from_files(
                    runtime_binding_file=
                        fixture[
                            "binding_path"
                        ],

                    execution_authorization_file=
                        fixture[
                            "authorization_path"
                        ],

                    authorization_record_file=
                        fixture[
                            "record_path"
                        ],

                    execute_real=
                        True,

                    network_io_acknowledgement=
                        "wrong",

                    orchestrator_fn=
                        fake_orchestrator,
                )

        self.assertEqual(
            calls,
            [],
        )

    def test_28_valid_gates_dispatch_injected_orchestrator(self):
        calls = []

        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            def fake_orchestrator(
                **kwargs,
            ):
                calls.append(
                    kwargs
                )

                return {
                    "synthetic":
                        True,
                }

            result = execute_real_session_from_files(
                runtime_binding_file=
                    fixture[
                        "binding_path"
                    ],

                execution_authorization_file=
                    fixture[
                        "authorization_path"
                    ],

                authorization_record_file=
                    fixture[
                        "record_path"
                    ],

                execute_real=
                    True,

                network_io_acknowledgement=
                    NETWORK_IO_ACKNOWLEDGEMENT,

                orchestrator_fn=
                    fake_orchestrator,
            )

            self.assertTrue(
                result[
                    "execution_result"
                ][
                    "synthetic"
                ]
            )

        self.assertEqual(
            len(
                calls
            ),
            1,
        )

    def test_29_dispatch_receives_exact_binding(self):
        seen = []

        with TemporaryDirectory() as temp:
            fixture = write_fixture_set(
                temp
            )

            def fake_orchestrator(
                **kwargs,
            ):
                seen.append(
                    kwargs
                )

                return {}

            execute_real_session_from_files(
                runtime_binding_file=
                    fixture[
                        "binding_path"
                    ],

                execution_authorization_file=
                    fixture[
                        "authorization_path"
                    ],

                authorization_record_file=
                    fixture[
                        "record_path"
                    ],

                execute_real=
                    True,

                network_io_acknowledgement=
                    NETWORK_IO_ACKNOWLEDGEMENT,

                orchestrator_fn=
                    fake_orchestrator,
            )

            self.assertEqual(
                seen[
                    0
                ][
                    "runtime_binding"
                ],
                fixture[
                    "binding"
                ],
            )

    def test_30_repository_real_state_zero(self):
        state = self.payload[
            "current_real_state"
        ]

        self.assertEqual(
            state[
                "real_runtime_binding_count"
            ],
            0,
        )

        self.assertEqual(
            state[
                "real_execution_authorization_count"
            ],
            0,
        )

        self.assertEqual(
            state[
                "grounded_authorization_record_count"
            ],
            0,
        )

    def test_31_no_real_network_execution_recorded(self):
        verification = self.payload[
            "verification_state"
        ]

        self.assertFalse(
            verification[
                "real_sensor_network_IO_executed"
            ]
        )

        self.assertFalse(
            verification[
                "real_sensor_contact_executed"
            ]
        )

    def test_32_sources_and_labels_zero(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertEqual(
            science[
                "accepted_baseline_nominality_source_count"
            ],
            0,
        )

        self.assertEqual(
            science[
                "accepted_health_supervision_source_count"
            ],
            0,
        )

        self.assertEqual(
            science[
                "real_health_label_count"
            ],
            0,
        )

    def test_33_SE4_SE5_closed(self):
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

    def test_34_repository_input_guard_fails_closed(self):
        with self.assertRaises(
            SE4RealTrainExecutionRunnerError
        ):
            assert_repository_real_inputs_available(
                self.payload
            )

    def test_35_runner_script_has_no_physical_defaults(self):
        text = RUNNER.read_text(
            encoding="utf-8"
        )

        for forbidden in (
            "157.27.31.126",
            "10.147.18.208",
            "2368",
            "8308",
            "192.168.1.201",
        ):
            self.assertNotIn(
                forbidden,
                text,
            )

    def test_36_runner_script_requires_all_three_files(self):
        text = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "--runtime-binding-file",
            text,
        )

        self.assertIn(
            "--execution-authorization-file",
            text,
        )

        self.assertIn(
            "--authorization-record-file",
            text,
        )

    def test_37_runner_default_path_is_validation_only(self):
        text = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'if not args.execute_real:',
            text,
        )

        self.assertIn(
            '"validation_only"',
            text,
        )

    def test_38_runner_help_executes_no_network(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(
                    RUNNER
                ),
                "--help",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={
                **dict(
                    __import__(
                        "os"
                    ).environ
                ),
                "PYTHONPATH":
                    str(
                        ROOT
                        / "src"
                    ),
            },
        )

        self.assertIn(
            "--execute-real",
            completed.stdout,
        )

    def test_39_module_has_no_host_discovery_code(self):
        text = MODULE.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            'subprocess.run',
            text,
        )

        self.assertNotIn(
            '"ip",',
            text,
        )

        self.assertNotIn(
            "socket.socket",
            text,
        )

    def test_40_no_reference_or_scoring(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "reference_data_used"
            ]
        )

        self.assertFalse(
            science[
                "ATE_RPE_computed"
            ]
        )


if __name__ == "__main__":
    unittest.main()
