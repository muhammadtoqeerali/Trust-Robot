from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import ast
import json
import unittest

from trust_robot.se4_composite_live_session_orchestrator import (
    AUTHORIZATION_SCHEMA,
    COMPOSITE_RECEIPT_NAME,
    FAILURE_RECEIPT_NAME,
    RESOLUTION_SCHEMA,
    SE4CompositeLiveSessionOrchestratorError,
    assert_health_supervision_available,
    assert_repository_real_execution_authorized,
    authorization_content_sha256,
    build_composite_orchestrator_resolution,
    build_execution_authorization_candidate,
    execute_composite_live_session,
    receipt_content_sha256,
    resolution_content_sha256,
    validate_composite_orchestrator_resolution,
    validate_execution_authorization_candidate,
)

from trust_robot.se4_real_train_runtime_input_binding_v2 import (
    build_runtime_binding_candidate_v2,
)


ROOT = Path(__file__).resolve().parents[2]

MODULE = (
    ROOT
    / "src/trust_robot/"
    "se4_composite_live_session_orchestrator.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_composite_live_session_orchestrator_resolution_v1.json"
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
    "se4_http_evidence_executor.py":
        "98d82acca2308aea76537de4a9cc4fa0eb94e8fd9bc4aa9bde048382f5b69dd9",

    ROOT
    / "manifests/"
    "trust_robot_se4_http_evidence_executor_freeze_v1.json":
        "29639601503a8d7c0b9db879939a8960b2f0a69ca10e378fc07f0b031aeadc10",

    ROOT
    / "src/trust_robot/"
    "unprivileged_udp_receiver.py":
        "05e40722e15434b92d0f8aad93e4a6a9aef71a38dcd8d97e8bddc4f5ec3a385d",

    ROOT
    / "src/trust_robot/"
    "live_executor_safety.py":
        "6dcb292355ba17ec8a563b1183e0279b40559ec0467dd8dc9fbba5a2e674e26a",
}


def file_sha(
    path,
):
    return sha256(
        path.read_bytes()
    ).hexdigest()


def binding(
    output_root,
    *,
    session_id="SYNTHETIC_COMPOSITE_SESSION",
):
    return build_runtime_binding_candidate_v2(
        acquisition_session_id=
            session_id,

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


def authorization(
    candidate,
    *,
    authorized=True,
    before=True,
):
    return build_execution_authorization_candidate(
        authorization_id=
            "SYNTHETIC_EXECUTION_AUTHORIZATION",

        binding_sha256=
            candidate[
                "binding_sha256"
            ],

        authorization_record_sha256=
            "a" * 64,

        authorized_for_real_sensor_execution=
            authorized,

        declared_before_execution=
            before,
    )


def fake_udp_factory(
    calls,
):
    def fake_udp(
        candidate,
    ):
        calls.append(
            "UDP"
        )

        session = (
            Path(
                candidate.absolute_output_root
            )
            / candidate.acquisition_session_id
        )

        session.mkdir(
            parents=False,
            exist_ok=False,
        )

        receipt = {
            "schema":
                "SYNTHETIC_UDP_RECEIPT",

            "acquisition_session_id":
                candidate.acquisition_session_id,

            "scientific_nonclaims": {
                "health_label_assigned":
                    False,

                "interval_binding_established":
                    False,
            },
        }

        capture = (
            session
            / "capture_receipt.json"
        )

        capture.write_text(
            json.dumps(
                receipt,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        return {
            "session_directory":
                str(
                    session
                ),

            "capture_receipt":
                receipt,

            "capture_receipt_publication": {
                "final_path":
                    str(
                        capture
                    ),
            },
        }

    return fake_udp


def fake_http_factory(
    calls,
    *,
    fail_kind=None,
):
    def fake_http(
        **kwargs,
    ):
        kind = kwargs[
            "evidence_kind"
        ]

        calls.append(
            "HTTP:"
            + kind
        )

        if kind == fail_kind:
            raise RuntimeError(
                "synthetic HTTP failure"
            )

        session = Path(
            kwargs[
                "session_directory"
            ]
        )

        body_names = {
            "identity":
                "info.json",

            "status":
                "status.json",

            "diagnostic":
                "diagnostic.json",
        }

        header_names = {
            "identity":
                "info.headers",

            "status":
                "status.headers",

            "diagnostic":
                "diagnostic.headers",
        }

        body = (
            session
            / body_names[
                kind
            ]
        )

        header = (
            session
            / header_names[
                kind
            ]
        )

        body.write_text(
            "{}\n",
            encoding="utf-8",
        )

        header.write_text(
            "HTTP/1.1 200 OK\r\n\r\n",
            encoding="utf-8",
        )

        return {
            "schema":
                "SYNTHETIC_HTTP_RECEIPT",

            "evidence_kind":
                kind,

            "execution_scope":
                kwargs[
                    "execution_scope"
                ],

            "sensor_ipv4":
                kwargs[
                    "sensor_ipv4"
                ],

            "http_port":
                kwargs[
                    "http_port"
                ],

            "real_sensor_execution_authorized":
                kwargs[
                    "real_sensor_execution_authorized"
                ],

            "health_label_generated":
                False,

            "interval_binding_established":
                False,
        }

    return fake_http


class SE4CompositeLiveSessionOrchestratorTests(
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
            RESOLUTION_SCHEMA,
        )

    def test_02_content_digest(self):
        self.assertEqual(
            self.payload[
                "content_sha256"
            ],
            resolution_content_sha256(
                self.payload
            ),
        )

    def test_03_builder_matches_config(self):
        self.assertEqual(
            self.payload,
            build_composite_orchestrator_resolution(),
        )

    def test_04_validator_accepts_config(self):
        self.assertIs(
            validate_composite_orchestrator_resolution(
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

    def test_06_stage_remains_incomplete(self):
        stage = self.payload[
            "stage_context"
        ]

        self.assertFalse(
            stage[
                "SE4_complete"
            ]
        )

        self.assertFalse(
            stage[
                "SE4_training_authorized"
            ]
        )

    def test_07_exact_HTTP_order(self):
        self.assertEqual(
            self.payload[
                "composition_contract"
            ][
                "HTTP_order"
            ],
            [
                "identity",
                "status",
                "diagnostic",
            ],
        )

    def test_08_concurrency_not_required(self):
        self.assertFalse(
            self.payload[
                "composition_contract"
            ][
                "HTTP_UDP_concurrency_required"
            ]
        )

    def test_09_UDP_owns_session_creation(self):
        contract = self.payload[
            "composition_contract"
        ]

        self.assertTrue(
            contract[
                "UDP_receiver_owns_session_directory_creation"
            ]
        )

        self.assertTrue(
            contract[
                "HTTP_executor_requires_returned_existing_session_directory"
            ]
        )

    def test_10_preflight_before_UDP_required(self):
        filesystem = self.payload[
            "filesystem_contract"
        ]

        self.assertTrue(
            filesystem[
                "absolute_output_root_must_exist_before_UDP_invocation"
            ]
        )

        self.assertTrue(
            filesystem[
                "expected_session_directory_must_not_exist_before_UDP_invocation"
            ]
        )

    def test_11_authorization_format_selected_but_zero_real(self):
        auth = self.payload[
            "authorization_contract"
        ]

        self.assertEqual(
            auth[
                "schema"
            ],
            AUTHORIZATION_SCHEMA,
        )

        self.assertEqual(
            auth[
                "repository_real_authorization_artifact_count"
            ],
            0,
        )

        self.assertFalse(
            auth[
                "real_sensor_execution_authorized"
            ]
        )

    def test_12_authorization_candidate_digest(self):
        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            auth = authorization(
                candidate
            )

            self.assertEqual(
                auth[
                    "authorization_sha256"
                ],
                authorization_content_sha256(
                    auth
                ),
            )

    def test_13_authorization_is_bound_to_binding(self):
        with TemporaryDirectory() as first:
            with TemporaryDirectory() as second:
                one = binding(
                    first,
                    session_id="ONE",
                )

                two = binding(
                    second,
                    session_id="TWO",
                )

                auth = authorization(
                    one
                )

                with self.assertRaises(
                    SE4CompositeLiveSessionOrchestratorError
                ):
                    validate_execution_authorization_candidate(
                        auth,
                        expected_binding_sha256=
                            two[
                                "binding_sha256"
                            ],
                    )

    def test_14_false_authorization_rejected(self):
        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            auth = authorization(
                candidate,
                authorized=False,
            )

            with self.assertRaises(
                SE4CompositeLiveSessionOrchestratorError
            ):
                validate_execution_authorization_candidate(
                    auth,
                    expected_binding_sha256=
                        candidate[
                            "binding_sha256"
                        ],
                )

    def test_15_late_authorization_rejected(self):
        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            auth = authorization(
                candidate,
                before=False,
            )

            with self.assertRaises(
                SE4CompositeLiveSessionOrchestratorError
            ):
                validate_execution_authorization_candidate(
                    auth,
                    expected_binding_sha256=
                        candidate[
                            "binding_sha256"
                        ],
                )

    def test_16_invalid_binding_prevents_component_invocation(self):
        calls = []

        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            auth = authorization(
                candidate
            )

            candidate[
                "HTTP_binding"
            ][
                "http_port"
            ] = 0

            with self.assertRaises(
                SE4CompositeLiveSessionOrchestratorError
            ):
                execute_composite_live_session(
                    runtime_binding=
                        candidate,

                    execution_authorization=
                        auth,

                    udp_capture_fn=
                        fake_udp_factory(
                            calls
                        ),

                    http_read_fn=
                        fake_http_factory(
                            calls
                        ),
                )

        self.assertEqual(
            calls,
            [],
        )

    def test_17_unauthorized_session_prevents_UDP(self):
        calls = []

        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            auth = authorization(
                candidate,
                authorized=False,
            )

            with self.assertRaises(
                SE4CompositeLiveSessionOrchestratorError
            ):
                execute_composite_live_session(
                    runtime_binding=
                        candidate,

                    execution_authorization=
                        auth,

                    udp_capture_fn=
                        fake_udp_factory(
                            calls
                        ),

                    http_read_fn=
                        fake_http_factory(
                            calls
                        ),
                )

        self.assertEqual(
            calls,
            [],
        )

    def test_18_missing_output_root_prevents_UDP(self):
        calls = []

        with TemporaryDirectory() as temp:
            missing = (
                Path(
                    temp
                )
                / "missing"
            )

            candidate = binding(
                missing
            )

            auth = authorization(
                candidate
            )

            with self.assertRaises(
                SE4CompositeLiveSessionOrchestratorError
            ):
                execute_composite_live_session(
                    runtime_binding=
                        candidate,

                    execution_authorization=
                        auth,

                    udp_capture_fn=
                        fake_udp_factory(
                            calls
                        ),

                    http_read_fn=
                        fake_http_factory(
                            calls
                        ),
                )

        self.assertEqual(
            calls,
            [],
        )

    def test_19_existing_session_prevents_UDP(self):
        calls = []

        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            (
                Path(
                    temp
                )
                / candidate[
                    "acquisition_session_id"
                ]
            ).mkdir()

            auth = authorization(
                candidate
            )

            with self.assertRaises(
                SE4CompositeLiveSessionOrchestratorError
            ):
                execute_composite_live_session(
                    runtime_binding=
                        candidate,

                    execution_authorization=
                        auth,

                    udp_capture_fn=
                        fake_udp_factory(
                            calls
                        ),

                    http_read_fn=
                        fake_http_factory(
                            calls
                        ),
                )

        self.assertEqual(
            calls,
            [],
        )

    def test_20_successful_injected_order(self):
        calls = []

        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            result = execute_composite_live_session(
                runtime_binding=
                    candidate,

                execution_authorization=
                    authorization(
                        candidate
                    ),

                udp_capture_fn=
                    fake_udp_factory(
                        calls
                    ),

                http_read_fn=
                    fake_http_factory(
                        calls
                    ),
            )

            self.assertEqual(
                calls,
                [
                    "UDP",
                    "HTTP:identity",
                    "HTTP:status",
                    "HTTP:diagnostic",
                ],
            )

            self.assertTrue(
                Path(
                    result[
                        "session_directory"
                    ]
                ).is_dir()
            )

    def test_21_composite_receipt_published(self):
        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            result = execute_composite_live_session(
                runtime_binding=
                    candidate,

                execution_authorization=
                    authorization(
                        candidate
                    ),

                udp_capture_fn=
                    fake_udp_factory(
                        []
                    ),

                http_read_fn=
                    fake_http_factory(
                        []
                    ),
            )

            path = (
                Path(
                    result[
                        "session_directory"
                    ]
                )
                / COMPOSITE_RECEIPT_NAME
            )

            self.assertTrue(
                path.is_file()
            )

    def test_22_receipt_digest_is_canonical(self):
        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            result = execute_composite_live_session(
                runtime_binding=
                    candidate,

                execution_authorization=
                    authorization(
                        candidate
                    ),

                udp_capture_fn=
                    fake_udp_factory(
                        []
                    ),

                http_read_fn=
                    fake_http_factory(
                        []
                    ),
            )

            receipt = result[
                "composite_session_receipt"
            ]

            self.assertEqual(
                receipt[
                    "receipt_sha256"
                ],
                receipt_content_sha256(
                    receipt
                ),
            )

    def test_23_receipt_binds_runtime_binding(self):
        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            auth = authorization(
                candidate
            )

            result = execute_composite_live_session(
                runtime_binding=
                    candidate,

                execution_authorization=
                    auth,

                udp_capture_fn=
                    fake_udp_factory(
                        []
                    ),

                http_read_fn=
                    fake_http_factory(
                        []
                    ),
            )

            receipt = result[
                "composite_session_receipt"
            ]

            self.assertEqual(
                receipt[
                    "binding_sha256"
                ],
                candidate[
                    "binding_sha256"
                ],
            )

            self.assertEqual(
                receipt[
                    "execution_authorization_sha256"
                ],
                auth[
                    "authorization_sha256"
                ],
            )

    def test_24_receipt_scientific_nonclaims(self):
        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            result = execute_composite_live_session(
                runtime_binding=
                    candidate,

                execution_authorization=
                    authorization(
                        candidate
                    ),

                udp_capture_fn=
                    fake_udp_factory(
                        []
                    ),

                http_read_fn=
                    fake_http_factory(
                        []
                    ),
            )

            science = result[
                "composite_session_receipt"
            ][
                "scientific_nonclaims"
            ]

            for value in science.values():
                self.assertFalse(
                    value
                )

    def test_25_HTTP_receives_exact_binding_values(self):
        seen = []

        def fake_http(
            **kwargs,
        ):
            seen.append(
                dict(
                    kwargs
                )
            )

            return {
                "evidence_kind":
                    kwargs[
                        "evidence_kind"
                    ],
            }

        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            execute_composite_live_session(
                runtime_binding=
                    candidate,

                execution_authorization=
                    authorization(
                        candidate
                    ),

                udp_capture_fn=
                    fake_udp_factory(
                        []
                    ),

                http_read_fn=
                    fake_http,
            )

        self.assertEqual(
            len(
                seen
            ),
            3,
        )

        for kwargs in seen:
            self.assertEqual(
                kwargs[
                    "sensor_ipv4"
                ],
                "192.0.2.20",
            )

            self.assertEqual(
                kwargs[
                    "http_port"
                ],
                8080,
            )

            self.assertEqual(
                kwargs[
                    "http_connect_timeout_seconds"
                ],
                1,
            )

            self.assertEqual(
                kwargs[
                    "http_total_timeout_seconds"
                ],
                2,
            )

            self.assertTrue(
                kwargs[
                    "real_sensor_execution_authorized"
                ]
            )

            self.assertFalse(
                kwargs[
                    "loopback_test_authorized"
                ]
            )

    def test_26_UDP_candidate_receives_exact_binding_values(self):
        seen = []

        def fake_udp(
            candidate,
        ):
            seen.append(
                candidate
            )

            return fake_udp_factory(
                []
            )(
                candidate
            )

        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            execute_composite_live_session(
                runtime_binding=
                    candidate,

                execution_authorization=
                    authorization(
                        candidate
                    ),

                udp_capture_fn=
                    fake_udp,

                http_read_fn=
                    fake_http_factory(
                        []
                    ),
            )

        self.assertEqual(
            len(
                seen
            ),
            1,
        )

        actual = seen[
            0
        ]

        self.assertEqual(
            actual.bind_ipv4,
            "192.0.2.10",
        )

        self.assertEqual(
            actual.measurement_udp_port,
            25000,
        )

        self.assertEqual(
            actual.position_udp_port,
            25001,
        )

    def test_27_wrong_UDP_session_directory_rejected(self):
        calls = []

        def wrong_udp(
            candidate,
        ):
            calls.append(
                "UDP"
            )

            wrong = (
                Path(
                    candidate.absolute_output_root
                )
                / "WRONG"
            )

            wrong.mkdir()

            return {
                "session_directory":
                    str(
                        wrong
                    ),

                "capture_receipt":
                    {},

                "capture_receipt_publication":
                    {},
            }

        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            with self.assertRaises(
                SE4CompositeLiveSessionOrchestratorError
            ):
                execute_composite_live_session(
                    runtime_binding=
                        candidate,

                    execution_authorization=
                        authorization(
                            candidate
                        ),

                    udp_capture_fn=
                        wrong_udp,

                    http_read_fn=
                        fake_http_factory(
                            calls
                        ),
                )

        self.assertEqual(
            calls,
            [
                "UDP",
            ],
        )

    def test_28_HTTP_failure_publishes_failure_receipt(self):
        calls = []

        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            with self.assertRaises(
                RuntimeError
            ):
                execute_composite_live_session(
                    runtime_binding=
                        candidate,

                    execution_authorization=
                        authorization(
                            candidate
                        ),

                    udp_capture_fn=
                        fake_udp_factory(
                            calls
                        ),

                    http_read_fn=
                        fake_http_factory(
                            calls,
                            fail_kind="status",
                        ),
                )

            session = (
                Path(
                    temp
                )
                / candidate[
                    "acquisition_session_id"
                ]
            )

            self.assertTrue(
                (
                    session
                    / FAILURE_RECEIPT_NAME
                ).is_file()
            )

            self.assertFalse(
                (
                    session
                    / COMPOSITE_RECEIPT_NAME
                ).exists()
            )

        self.assertEqual(
            calls,
            [
                "UDP",
                "HTTP:identity",
                "HTTP:status",
            ],
        )

    def test_29_failure_receipt_records_phase(self):
        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            with self.assertRaises(
                RuntimeError
            ):
                execute_composite_live_session(
                    runtime_binding=
                        candidate,

                    execution_authorization=
                        authorization(
                            candidate
                        ),

                    udp_capture_fn=
                        fake_udp_factory(
                            []
                        ),

                    http_read_fn=
                        fake_http_factory(
                            [],
                            fail_kind="diagnostic",
                        ),
                )

            failure = json.loads(
                (
                    Path(
                        temp
                    )
                    / candidate[
                        "acquisition_session_id"
                    ]
                    / FAILURE_RECEIPT_NAME
                ).read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                failure[
                    "failed_phase"
                ],
                "execute_diagnostic_HTTP",
            )

            self.assertFalse(
                failure[
                    "source_acceptance_authorized"
                ]
            )

            self.assertFalse(
                failure[
                    "health_label_generation_authorized"
                ]
            )

    def test_30_no_failure_receipt_before_session_exists(self):
        with TemporaryDirectory() as temp:
            candidate = binding(
                temp
            )

            def fail_udp(
                candidate,
            ):
                del candidate

                raise RuntimeError(
                    "synthetic UDP failure"
                )

            with self.assertRaises(
                RuntimeError
            ):
                execute_composite_live_session(
                    runtime_binding=
                        candidate,

                    execution_authorization=
                        authorization(
                            candidate
                        ),

                    udp_capture_fn=
                        fail_udp,

                    http_read_fn=
                        fake_http_factory(
                            []
                        ),
                )

            self.assertFalse(
                (
                    Path(
                        temp
                    )
                    / candidate[
                        "acquisition_session_id"
                    ]
                ).exists()
            )

    def test_31_real_state_remains_zero(self):
        state = self.payload[
            "current_real_state"
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

        self.assertEqual(
            state[
                "real_execution_authorization_count"
            ],
            0,
        )

        self.assertFalse(
            state[
                "real_sensor_execution_authorized"
            ]
        )

    def test_32_real_verification_remains_false(self):
        state = self.payload[
            "verification_state"
        ]

        self.assertTrue(
            state[
                "component_injection_orchestration_verified"
            ]
        )

        self.assertFalse(
            state[
                "real_sensor_execution_verified"
            ]
        )

        self.assertFalse(
            state[
                "real_sensor_network_IO_executed"
            ]
        )

        self.assertFalse(
            state[
                "real_sensor_contact_executed"
            ]
        )

    def test_33_zero_sources_and_labels(self):
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

    def test_34_interval_binding_remains_false(self):
        science = self.payload[
            "scientific_boundary"
        ]

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

    def test_35_SE4_SE5_remain_closed(self):
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

    def test_36_validation_confirmation_closed(self):
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

    def test_37_repository_execution_guard_fails_closed(self):
        with self.assertRaises(
            SE4CompositeLiveSessionOrchestratorError
        ):
            assert_repository_real_execution_authorized(
                self.payload
            )

    def test_38_health_supervision_guard_fails_closed(self):
        with self.assertRaises(
            SE4CompositeLiveSessionOrchestratorError
        ):
            assert_health_supervision_available(
                self.payload
            )

    def test_39_no_reference_scoring(self):
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

    def test_40_no_silent_loopback_real_binding_bypass(self):
        tree = ast.parse(
            MODULE.read_text(
                encoding="utf-8"
            ),
            filename=str(
                MODULE
            ),
        )

        text = MODULE.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "127.0.0.1",
            text,
        )

        self.assertNotIn(
            "loopback_test_authorized=True",
            text,
        )

        self.assertTrue(
            any(
                isinstance(
                    node,
                    ast.FunctionDef,
                )
                and node.name
                == "execute_composite_live_session"
                for node
                in tree.body
            )
        )


if __name__ == "__main__":
    unittest.main()
