from copy import deepcopy
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import json
import shutil
import unittest

from trust_robot.se4_http_evidence_executor import (
    ENDPOINTS,
    EXECUTION_SCOPE_LOOPBACK,
    EXECUTION_SCOPE_REAL_SENSOR,
    FROZEN_INPUT_SHA256,
    SCHEMA,
    SE4HTTPEvidenceExecutorError,
    assert_health_supervision_available,
    assert_repository_real_sensor_execution_authorized,
    build_http_evidence_executor_resolution,
    content_sha256,
    execute_one_shot_http_evidence_read,
    validate_http_evidence_executor_resolution,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
    "se4_http_evidence_executor_resolution_v1.json"
)

INPUT_PATHS = {
    "SE4_runtime_binding_freeze":
        ROOT
        / "manifests/"
        "trust_robot_se4_real_train_runtime_input_binding_freeze_v1.json",

    "SE4_runtime_binding_config":
        ROOT
        / "configs/trust_robot/"
        "se4_real_train_runtime_input_binding_v1.json",

    "phase5_live_acquisition_plan":
        ROOT
        / "configs/trust_robot/"
        "phase5_live_acquisition_plan_candidate_v1.json",

    "live_acquisition_plan_module":
        ROOT
        / "src/trust_robot/"
        "live_acquisition_plan.py",

    "phase5_live_executor_safety":
        ROOT
        / "configs/trust_robot/"
        "phase5_live_executor_safety_candidate_v1.json",

    "live_executor_safety_module":
        ROOT
        / "src/trust_robot/"
        "live_executor_safety.py",

    "phase5_acquisition_session_provenance":
        ROOT
        / "configs/trust_robot/"
        "phase5_acquisition_session_provenance_candidate_v1.json",

    "acquisition_session_provenance_module":
        ROOT
        / "src/trust_robot/"
        "acquisition_session_provenance.py",
}


def file_sha(path):
    return sha256(
        path.read_bytes()
    ).hexdigest()


class Handler(
    BaseHTTPRequestHandler
):
    payloads = {
        "/cgi/info.json":
            b'{"serial":"LOOPBACK_TEST_SERIAL"}\n',

        "/cgi/status.json":
            b'{"motor":"loopback-test"}\n',

        "/cgi/diag.json":
            b'{"diagnostic":"loopback-test"}\n',
    }

    def do_GET(self):
        body = self.payloads.get(
            self.path
        )

        if body is None:
            self.send_response(
                404
            )
            self.end_headers()
            return

        self.send_response(
            200
        )

        self.send_header(
            "Content-Type",
            "application/json",
        )

        self.send_header(
            "Content-Length",
            str(
                len(
                    body
                )
            ),
        )

        self.send_header(
            "X-Trust-Robot-Test",
            "loopback-only",
        )

        self.end_headers()

        self.wfile.write(
            body
        )

    def log_message(
        self,
        format,
        *args,
    ):
        del format, args


class LoopbackServer:
    def __enter__(
        self
    ):
        self.server = ThreadingHTTPServer(
            (
                "127.0.0.1",
                0,
            ),
            Handler,
        )

        self.thread = Thread(
            target=self.server.serve_forever,
            daemon=True,
        )

        self.thread.start()

        return self

    @property
    def port(
        self
    ):
        return self.server.server_address[
            1
        ]

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        del exc_type, exc, tb

        self.server.shutdown()
        self.server.server_close()
        self.thread.join(
            timeout=5
        )


class SE4HTTPEvidenceExecutorTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        cls.curl = shutil.which(
            "curl"
        )

        if cls.curl is None:
            raise RuntimeError(
                "curl is required for HTTP executor tests"
            )

    def test_01_schema(self):
        self.assertEqual(
            self.payload[
                "schema"
            ],
            SCHEMA,
        )

    def test_02_content_digest(self):
        self.assertEqual(
            self.payload[
                "content_sha256"
            ],
            content_sha256(
                self.payload
            ),
        )

    def test_03_builder_matches_config(self):
        self.assertEqual(
            self.payload,
            build_http_evidence_executor_resolution(),
        )

    def test_04_stage_remains_SE4_incomplete(self):
        stage = self.payload[
            "stage_context"
        ]

        self.assertEqual(
            stage[
                "stage_id"
            ],
            "SE4",
        )

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

    def test_05_http_execution_software_is_implemented(self):
        software = self.payload[
            "HTTP_execution_software"
        ]

        self.assertTrue(
            software[
                "implemented"
            ]
        )

        self.assertEqual(
            software[
                "implementation_transport"
            ],
            "curl_subprocess",
        )

        self.assertFalse(
            software[
                "shell_execution"
            ]
        )

    def test_06_exact_endpoint_allowlist(self):
        self.assertEqual(
            self.payload[
                "endpoints"
            ],
            ENDPOINTS,
        )

    def test_07_one_shot_read_only_contract(self):
        software = self.payload[
            "HTTP_execution_software"
        ]

        self.assertTrue(
            software[
                "read_only_GET_only"
            ]
        )

        self.assertFalse(
            software[
                "redirect_following_enabled"
            ]
        )

        self.assertTrue(
            software[
                "endpoint_allowlist_enforced"
            ]
        )

    def test_08_body_and_headers_separate(self):
        self.assertTrue(
            self.payload[
                "HTTP_execution_software"
            ][
                "body_and_headers_preserved_separately"
            ]
        )

    def test_09_publication_safety_contract(self):
        software = self.payload[
            "HTTP_execution_software"
        ]

        self.assertTrue(
            software[
                "same_directory_partial_files"
            ]
        )

        self.assertFalse(
            software[
                "existing_final_overwrite_allowed"
            ]
        )

        self.assertTrue(
            software[
                "file_fsync_before_publish"
            ]
        )

        self.assertTrue(
            software[
                "directory_fsync_after_publish"
            ]
        )

        self.assertTrue(
            software[
                "pre_post_publish_SHA256_equality_required"
            ]
        )

    def test_10_loopback_verified_real_sensor_not_verified(self):
        state = self.payload[
            "verification_state"
        ]

        self.assertTrue(
            state[
                "loopback_execution_verified"
            ]
        )

        self.assertFalse(
            state[
                "real_sensor_execution_verified"
            ]
        )

    def test_11_zero_real_sensor_execution_state(self):
        state = self.payload[
            "verification_state"
        ]

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

        self.assertEqual(
            state[
                "real_device_identity_receipt_count"
            ],
            0,
        )

        self.assertEqual(
            state[
                "raw_real_sensor_HTTP_artifact_count"
            ],
            0,
        )

    def test_12_real_execution_not_authorized(self):
        auth = self.payload[
            "authorization_boundary"
        ]

        self.assertFalse(
            auth[
                "real_sensor_execution_authorized"
            ]
        )

        self.assertFalse(
            auth[
                "HTTP_implementation_is_execution_authorization"
            ]
        )

    def test_13_runtime_binding_required_for_real_execution(self):
        self.assertTrue(
            self.payload[
                "authorization_boundary"
            ][
                "runtime_binding_required_before_real_sensor_execution"
            ]
        )

    def test_14_http_is_not_health_truth(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "HTTP_response_is_physical_health_truth"
            ]
        )

        self.assertFalse(
            science[
                "HTTP_status_is_health_label"
            ]
        )

        self.assertFalse(
            science[
                "HTTP_diagnostic_is_health_label"
            ]
        )

        self.assertFalse(
            science[
                "HTTP_identity_is_baseline_nominality"
            ]
        )

    def test_15_timeout_not_sensor_timing_tolerance(self):
        self.assertFalse(
            self.payload[
                "scientific_boundary"
            ][
                "HTTP_timeout_is_sensor_timing_tolerance"
            ]
        )

    def test_16_no_interval_binding_or_measurement_time_claim(self):
        science = self.payload[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "HTTP_receive_time_is_physical_measurement_time"
            ]
        )

        self.assertFalse(
            science[
                "HTTP_execution_establishes_interval_binding"
            ]
        )

    def test_17_zero_accepted_sources_and_labels(self):
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

    def test_18_SE4_SE5_validation_confirmation_closed(self):
        transition = self.payload[
            "transition_policy"
        ]

        self.assertTrue(
            transition[
                "HTTP_execution_software_implemented"
            ]
        )

        self.assertFalse(
            transition[
                "real_sensor_execution_authorized"
            ]
        )

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

    def test_19_frozen_input_hashes_exact(self):
        for key, path in INPUT_PATHS.items():
            self.assertEqual(
                file_sha(
                    path
                ),
                FROZEN_INPUT_SHA256[
                    key
                ],
            )

    def test_20_validator_accepts_exact_config(self):
        self.assertIs(
            validate_http_evidence_executor_resolution(
                self.payload
            ),
            self.payload,
        )

    def test_21_validator_rejects_fake_real_authorization(self):
        changed = deepcopy(
            self.payload
        )

        changed[
            "authorization_boundary"
        ][
            "real_sensor_execution_authorized"
        ] = True

        with self.assertRaises(
            SE4HTTPEvidenceExecutorError
        ):
            validate_http_evidence_executor_resolution(
                changed
            )

    def test_22_unknown_evidence_kind_rejected(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(
                SE4HTTPEvidenceExecutorError
            ):
                execute_one_shot_http_evidence_read(
                    evidence_kind=
                        "unknown",
                    sensor_ipv4=
                        "127.0.0.1",
                    session_directory=
                        temp,
                    http_connect_timeout_seconds=
                        1,
                    http_total_timeout_seconds=
                        2,
                    execution_scope=
                        EXECUTION_SCOPE_LOOPBACK,
                    loopback_test_authorized=
                        True,
                    http_port=
                        80,
                    curl_path=
                        self.curl,
                )

    def test_23_loopback_requires_explicit_authorization(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(
                SE4HTTPEvidenceExecutorError
            ):
                execute_one_shot_http_evidence_read(
                    evidence_kind=
                        "identity",
                    sensor_ipv4=
                        "127.0.0.1",
                    session_directory=
                        temp,
                    http_connect_timeout_seconds=
                        1,
                    http_total_timeout_seconds=
                        2,
                    execution_scope=
                        EXECUTION_SCOPE_LOOPBACK,
                    loopback_test_authorized=
                        False,
                    http_port=
                        80,
                    curl_path=
                        self.curl,
                )

    def test_24_real_scope_rejects_loopback(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(
                SE4HTTPEvidenceExecutorError
            ):
                execute_one_shot_http_evidence_read(
                    evidence_kind=
                        "identity",
                    sensor_ipv4=
                        "127.0.0.1",
                    session_directory=
                        temp,
                    http_connect_timeout_seconds=
                        1,
                    http_total_timeout_seconds=
                        2,
                    execution_scope=
                        EXECUTION_SCOPE_REAL_SENSOR,
                    real_sensor_execution_authorized=
                        True,
                    http_port=
                        80,
                    curl_path=
                        self.curl,
                )

    def test_25_real_scope_requires_authorization_before_network(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(
                SE4HTTPEvidenceExecutorError
            ):
                execute_one_shot_http_evidence_read(
                    evidence_kind=
                        "identity",
                    sensor_ipv4=
                        "192.0.2.20",
                    session_directory=
                        temp,
                    http_connect_timeout_seconds=
                        1,
                    http_total_timeout_seconds=
                        2,
                    execution_scope=
                        EXECUTION_SCOPE_REAL_SENSOR,
                    real_sensor_execution_authorized=
                        False,
                    http_port=
                        80,
                    curl_path=
                        self.curl,
                )

    def test_26_timeout_validation_occurs_before_execution(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(
                SE4HTTPEvidenceExecutorError
            ):
                execute_one_shot_http_evidence_read(
                    evidence_kind=
                        "identity",
                    sensor_ipv4=
                        "127.0.0.1",
                    session_directory=
                        temp,
                    http_connect_timeout_seconds=
                        5,
                    http_total_timeout_seconds=
                        4,
                    execution_scope=
                        EXECUTION_SCOPE_LOOPBACK,
                    loopback_test_authorized=
                        True,
                    http_port=
                        80,
                    curl_path=
                        self.curl,
                )

    def test_27_session_directory_must_exist(self):
        with TemporaryDirectory() as temp:
            missing = (
                Path(
                    temp
                )
                / "missing"
            )

            with self.assertRaises(
                SE4HTTPEvidenceExecutorError
            ):
                execute_one_shot_http_evidence_read(
                    evidence_kind=
                        "identity",
                    sensor_ipv4=
                        "127.0.0.1",
                    session_directory=
                        missing,
                    http_connect_timeout_seconds=
                        1,
                    http_total_timeout_seconds=
                        2,
                    execution_scope=
                        EXECUTION_SCOPE_LOOPBACK,
                    loopback_test_authorized=
                        True,
                    http_port=
                        80,
                    curl_path=
                        self.curl,
                )

    def test_28_http_port_requires_explicit_value(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(
                SE4HTTPEvidenceExecutorError
            ):
                execute_one_shot_http_evidence_read(
                    evidence_kind=
                        "identity",
                    sensor_ipv4=
                        "127.0.0.1",
                    session_directory=
                        temp,
                    http_connect_timeout_seconds=
                        1,
                    http_total_timeout_seconds=
                        2,
                    execution_scope=
                        EXECUTION_SCOPE_LOOPBACK,
                    loopback_test_authorized=
                        True,
                    curl_path=
                        self.curl,
                )

    def test_29_identity_loopback_execution(self):
        with LoopbackServer() as server:
            with TemporaryDirectory() as temp:
                receipt = (
                    execute_one_shot_http_evidence_read(
                        evidence_kind=
                            "identity",
                        sensor_ipv4=
                            "127.0.0.1",
                        session_directory=
                            temp,
                        http_connect_timeout_seconds=
                            2,
                        http_total_timeout_seconds=
                            5,
                        execution_scope=
                            EXECUTION_SCOPE_LOOPBACK,
                        loopback_test_authorized=
                            True,
                        http_port=
                            server.port,
                        curl_path=
                            self.curl,
                    )
                )

                root = Path(
                    temp
                )

                self.assertEqual(
                    (
                        root
                        / "info.json"
                    ).read_bytes(),
                    Handler.payloads[
                        "/cgi/info.json"
                    ],
                )

                headers = (
                    root
                    / "info.headers"
                ).read_bytes()

                self.assertIn(
                    b"200",
                    headers,
                )

                self.assertIn(
                    b"X-Trust-Robot-Test: loopback-only",
                    headers,
                )

                self.assertEqual(
                    receipt[
                        "execution_scope"
                    ],
                    EXECUTION_SCOPE_LOOPBACK,
                )

                self.assertTrue(
                    receipt[
                        "loopback_test_authorized"
                    ]
                )

                self.assertFalse(
                    receipt[
                        "real_sensor_execution_authorized"
                    ]
                )

    def test_30_status_loopback_execution(self):
        with LoopbackServer() as server:
            with TemporaryDirectory() as temp:
                receipt = (
                    execute_one_shot_http_evidence_read(
                        evidence_kind=
                            "status",
                        sensor_ipv4=
                            "127.0.0.1",
                        session_directory=
                            temp,
                        http_connect_timeout_seconds=
                            2,
                        http_total_timeout_seconds=
                            5,
                        execution_scope=
                            EXECUTION_SCOPE_LOOPBACK,
                        loopback_test_authorized=
                            True,
                        http_port=
                            server.port,
                        curl_path=
                            self.curl,
                    )
                )

                self.assertEqual(
                    receipt[
                        "endpoint_path"
                    ],
                    "/cgi/status.json",
                )

                self.assertFalse(
                    receipt[
                        "sensor_health_inferred"
                    ]
                )

                self.assertFalse(
                    receipt[
                        "health_label_generated"
                    ]
                )

    def test_31_diagnostic_loopback_execution(self):
        with LoopbackServer() as server:
            with TemporaryDirectory() as temp:
                receipt = (
                    execute_one_shot_http_evidence_read(
                        evidence_kind=
                            "diagnostic",
                        sensor_ipv4=
                            "127.0.0.1",
                        session_directory=
                            temp,
                        http_connect_timeout_seconds=
                            2,
                        http_total_timeout_seconds=
                            5,
                        execution_scope=
                            EXECUTION_SCOPE_LOOPBACK,
                        loopback_test_authorized=
                            True,
                        http_port=
                            server.port,
                        curl_path=
                            self.curl,
                    )
                )

                self.assertEqual(
                    receipt[
                        "endpoint_path"
                    ],
                    "/cgi/diag.json",
                )

                self.assertFalse(
                    receipt[
                        "interval_binding_established"
                    ]
                )

                self.assertFalse(
                    receipt[
                        "physical_measurement_time_established"
                    ]
                )

    def test_32_existing_final_artifact_rejected(self):
        with LoopbackServer() as server:
            with TemporaryDirectory() as temp:
                root = Path(
                    temp
                )

                (
                    root
                    / "info.json"
                ).write_bytes(
                    b"existing"
                )

                with self.assertRaises(
                    SE4HTTPEvidenceExecutorError
                ):
                    execute_one_shot_http_evidence_read(
                        evidence_kind=
                            "identity",
                        sensor_ipv4=
                            "127.0.0.1",
                        session_directory=
                            temp,
                        http_connect_timeout_seconds=
                            2,
                        http_total_timeout_seconds=
                            5,
                        execution_scope=
                            EXECUTION_SCOPE_LOOPBACK,
                        loopback_test_authorized=
                            True,
                        http_port=
                            server.port,
                        curl_path=
                            self.curl,
                    )

                self.assertEqual(
                    (
                        root
                        / "info.json"
                    ).read_bytes(),
                    b"existing",
                )

    def test_33_success_leaves_no_partial_files(self):
        with LoopbackServer() as server:
            with TemporaryDirectory() as temp:
                execute_one_shot_http_evidence_read(
                    evidence_kind=
                        "identity",
                    sensor_ipv4=
                        "127.0.0.1",
                    session_directory=
                        temp,
                    http_connect_timeout_seconds=
                        2,
                    http_total_timeout_seconds=
                        5,
                    execution_scope=
                        EXECUTION_SCOPE_LOOPBACK,
                    loopback_test_authorized=
                        True,
                    http_port=
                        server.port,
                    curl_path=
                        self.curl,
                )

                partials = list(
                    Path(
                        temp
                    ).glob(
                        "*.partial"
                    )
                )

                hidden_partials = list(
                    Path(
                        temp
                    ).glob(
                        ".*.partial"
                    )
                )

                self.assertEqual(
                    partials
                    + hidden_partials,
                    [],
                )

    def test_34_receipt_hashes_published_artifacts(self):
        with LoopbackServer() as server:
            with TemporaryDirectory() as temp:
                receipt = (
                    execute_one_shot_http_evidence_read(
                        evidence_kind=
                            "identity",
                        sensor_ipv4=
                            "127.0.0.1",
                        session_directory=
                            temp,
                        http_connect_timeout_seconds=
                            2,
                        http_total_timeout_seconds=
                            5,
                        execution_scope=
                            EXECUTION_SCOPE_LOOPBACK,
                        loopback_test_authorized=
                            True,
                        http_port=
                            server.port,
                        curl_path=
                            self.curl,
                    )
                )

                root = Path(
                    temp
                )

                self.assertEqual(
                    receipt[
                        "body_sha256"
                    ],
                    file_sha(
                        root
                        / "info.json"
                    ),
                )

                self.assertEqual(
                    receipt[
                        "headers_sha256"
                    ],
                    file_sha(
                        root
                        / "info.headers"
                    ),
                )

    def test_35_receipt_host_times_are_transport_only(self):
        with LoopbackServer() as server:
            with TemporaryDirectory() as temp:
                receipt = (
                    execute_one_shot_http_evidence_read(
                        evidence_kind=
                            "identity",
                        sensor_ipv4=
                            "127.0.0.1",
                        session_directory=
                            temp,
                        http_connect_timeout_seconds=
                            2,
                        http_total_timeout_seconds=
                            5,
                        execution_scope=
                            EXECUTION_SCOPE_LOOPBACK,
                        loopback_test_authorized=
                            True,
                        http_port=
                            server.port,
                        curl_path=
                            self.curl,
                    )
                )

                self.assertTrue(
                    receipt[
                        "host_times_transport_provenance_only"
                    ]
                )

                self.assertFalse(
                    receipt[
                        "physical_measurement_time_established"
                    ]
                )

    def test_36_repository_real_execution_guard_fails_closed(self):
        with self.assertRaises(
            SE4HTTPEvidenceExecutorError
        ):
            assert_repository_real_sensor_execution_authorized(
                self.payload
            )

    def test_37_health_supervision_guard_fails_closed(self):
        with self.assertRaises(
            SE4HTTPEvidenceExecutorError
        ):
            assert_health_supervision_available(
                self.payload
            )


if __name__ == "__main__":
    unittest.main()
