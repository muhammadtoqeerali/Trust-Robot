from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path
import ast
import inspect
import json
import struct
import tempfile
import unittest

from trust_robot.baseline_nominality import (
    BaselineNominalitySplit,
)

from trust_robot.live_executor_safety import (
    LiveExecutorSafetyError,
    Vlp32cLiveExecutorSafetyPlanCandidate,
    build_empty_live_executor_safety_registry,
    build_pcap_finalization_receipt,
    publish_same_directory_partial_file,
    reserve_fresh_session_directory,
    validate_classic_pcap_file,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase5_live_executor_safety_candidate_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/live_executor_safety.py"
)


def canonical_sha(payload):
    value = dict(
        payload
    )

    value.pop(
        "content_sha256",
        None,
    )

    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def safety_plan(**overrides):
    values = {
        "acquisition_session_id":
            "SESSION_001",

        "split":
            BaselineNominalitySplit.TRAIN,

        "sensor_ipv4":
            "192.0.2.10",

        "capture_interface":
            "eth-test",

        "data_udp_port":
            12000,

        "telemetry_udp_port":
            12001,

        "capture_duration_seconds":
            10,

        "absolute_output_root":
            "/tmp/TRUST_ROBOT_EXECUTOR_TEST",

        "http_connect_timeout_seconds":
            2,

        "http_total_timeout_seconds":
            5,

        "capture_shutdown_grace_seconds":
            3,
    }

    values.update(
        overrides
    )

    return Vlp32cLiveExecutorSafetyPlanCandidate(
        **values
    )


def pcap_bytes(
    *,
    packet_payloads=(
        b"abc",
    ),
    endian="<",
    nanosecond=False,
):
    if endian == "<":
        magic = (
            b"\x4d\x3c\xb2\xa1"
            if nanosecond
            else b"\xd4\xc3\xb2\xa1"
        )
    else:
        magic = (
            b"\xa1\xb2\x3c\x4d"
            if nanosecond
            else b"\xa1\xb2\xc3\xd4"
        )

    global_header = (
        magic
        + struct.pack(
            endian + "HHiIII",
            2,
            4,
            0,
            0,
            65535,
            1,
        )
    )

    records = []

    for index, payload in enumerate(
        packet_payloads,
        start=1,
    ):
        records.append(
            struct.pack(
                endian + "IIII",
                index,
                0,
                len(
                    payload
                ),
                len(
                    payload
                ),
            )
            + payload
        )

    return (
        global_header
        + b"".join(
            records
        )
    )


class LiveExecutorSafetyTests(unittest.TestCase):
    def test_01_config_digest(self):
        payload = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(
            payload[
                "content_sha256"
            ],
            canonical_sha(
                payload
            ),
        )

    def test_02_empty_registry_fail_closed(self):
        payload = (
            build_empty_live_executor_safety_registry()
        )

        self.assertFalse(
            payload[
                "live_execution_authorized"
            ]
        )

        self.assertFalse(
            payload[
                "actual_packet_capture_permission_verified"
            ]
        )

        self.assertEqual(
            payload[
                "real_health_label_count"
            ],
            0,
        )

    def test_03_required_runtime_parameters_have_no_defaults(self):
        signature = inspect.signature(
            Vlp32cLiveExecutorSafetyPlanCandidate
        )

        for name in (
            "acquisition_session_id",
            "split",
            "sensor_ipv4",
            "capture_interface",
            "data_udp_port",
            "telemetry_udp_port",
            "capture_duration_seconds",
            "absolute_output_root",
            "http_connect_timeout_seconds",
            "http_total_timeout_seconds",
            "capture_shutdown_grace_seconds",
        ):
            self.assertIs(
                signature.parameters[
                    name
                ].default,
                inspect.Parameter.empty,
            )

    def test_04_absolute_output_root_required(self):
        with self.assertRaises(
            LiveExecutorSafetyError
        ):
            safety_plan(
                absolute_output_root="relative/path"
            )

    def test_05_session_id_must_be_safe_path_component(self):
        for value in (
            "../escape",
            "a/b",
            "",
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    LiveExecutorSafetyError
                ):
                    safety_plan(
                        acquisition_session_id=value
                    )

    def test_06_invalid_ipv4_rejected(self):
        with self.assertRaises(
            LiveExecutorSafetyError
        ):
            safety_plan(
                sensor_ipv4="bad"
            )

    def test_07_connect_timeout_positive(self):
        with self.assertRaises(
            LiveExecutorSafetyError
        ):
            safety_plan(
                http_connect_timeout_seconds=0
            )

    def test_08_total_timeout_positive(self):
        with self.assertRaises(
            LiveExecutorSafetyError
        ):
            safety_plan(
                http_total_timeout_seconds=0
            )

    def test_09_total_timeout_not_less_than_connect(self):
        with self.assertRaises(
            LiveExecutorSafetyError
        ):
            safety_plan(
                http_connect_timeout_seconds=5,
                http_total_timeout_seconds=4,
            )

    def test_10_shutdown_grace_positive(self):
        with self.assertRaises(
            LiveExecutorSafetyError
        ):
            safety_plan(
                capture_shutdown_grace_seconds=0
            )

    def test_11_plan_is_immutable(self):
        value = safety_plan()

        with self.assertRaises(
            FrozenInstanceError
        ):
            value.sensor_ipv4 = "192.0.2.20"

    def test_12_session_directory_is_derived(self):
        self.assertEqual(
            safety_plan().session_directory,
            "/tmp/TRUST_ROBOT_EXECUTOR_TEST/SESSION_001",
        )

    def test_13_http_targets_are_partial_files(self):
        argv = safety_plan().command_argv()[
            "identity_http"
        ]

        self.assertIn(
            (
                "/tmp/TRUST_ROBOT_EXECUTOR_TEST/"
                "SESSION_001/.info.json.partial"
            ),
            argv,
        )

        self.assertIn(
            (
                "/tmp/TRUST_ROBOT_EXECUTOR_TEST/"
                "SESSION_001/.info.headers.partial"
            ),
            argv,
        )

    def test_14_http_timeouts_are_explicit(self):
        argv = safety_plan().command_argv()[
            "status_http"
        ]

        self.assertIn(
            "--connect-timeout",
            argv,
        )

        self.assertIn(
            "2",
            argv,
        )

        self.assertIn(
            "--max-time",
            argv,
        )

        self.assertIn(
            "5",
            argv,
        )

    def test_15_pcap_targets_are_partial_files(self):
        argv = safety_plan().command_argv()[
            "measurement_packet_capture"
        ]

        self.assertIn(
            (
                "/tmp/TRUST_ROBOT_EXECUTOR_TEST/"
                "SESSION_001/.measurement_packets.pcap.partial"
            ),
            argv,
        )

    def test_16_capture_shutdown_grace_is_explicit(self):
        argv = safety_plan().command_argv()[
            "measurement_packet_capture"
        ]

        self.assertIn(
            "--kill-after=3s",
            argv,
        )

        self.assertEqual(
            argv[
                :4
            ],
            [
                "timeout",
                "--signal=INT",
                "--kill-after=3s",
                "10s",
            ],
        )

    def test_17_publication_targets_share_parent(self):
        targets = safety_plan().publication_targets()

        for value in targets.values():
            temporary = Path(
                value[
                    "temporary"
                ]
            )

            final = Path(
                value[
                    "final"
                ]
            )

            self.assertEqual(
                temporary.parent,
                final.parent,
            )

    def test_18_plan_is_deterministic_and_nonexecuting(self):
        first = safety_plan().to_dict()
        second = safety_plan().to_dict()

        self.assertEqual(
            first,
            second,
        )

        self.assertFalse(
            first[
                "execution_boundary"
            ][
                "network_io_performed"
            ]
        )

        self.assertFalse(
            first[
                "execution_boundary"
            ][
                "subprocess_executed"
            ]
        )

    def test_19_confirmation_split_unavailable(self):
        with self.assertRaises(
            LiveExecutorSafetyError
        ):
            safety_plan(
                split="confirmation_test"
            )

    def test_20_fresh_session_reservation_and_collision_rejection(self):
        with tempfile.TemporaryDirectory() as root:
            first = reserve_fresh_session_directory(
                root,
                "SESSION_A",
            )

            self.assertTrue(
                first.is_dir()
            )

            with self.assertRaises(
                LiveExecutorSafetyError
            ):
                reserve_fresh_session_directory(
                    root,
                    "SESSION_A",
                )

    def test_21_session_reservation_requires_absolute_existing_root(self):
        with self.assertRaises(
            LiveExecutorSafetyError
        ):
            reserve_fresh_session_directory(
                "relative/root",
                "SESSION_A",
            )

    def test_22_atomic_publish_rejects_cross_directory(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            first = (
                root_path
                / "a"
            )

            second = (
                root_path
                / "b"
            )

            first.mkdir()
            second.mkdir()

            temporary = (
                first
                / ".artifact.partial"
            )

            temporary.write_bytes(
                b"abc"
            )

            with self.assertRaises(
                LiveExecutorSafetyError
            ):
                publish_same_directory_partial_file(
                    temporary,
                    second
                    / "artifact",
                )

    def test_23_atomic_publish_rejects_existing_final(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            temporary = (
                root_path
                / ".artifact.partial"
            )

            final = (
                root_path
                / "artifact"
            )

            temporary.write_bytes(
                b"abc"
            )

            final.write_bytes(
                b"existing"
            )

            with self.assertRaises(
                LiveExecutorSafetyError
            ):
                publish_same_directory_partial_file(
                    temporary,
                    final,
                )

    def test_24_atomic_publish_preserves_hash(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            temporary = (
                root_path
                / ".artifact.partial"
            )

            final = (
                root_path
                / "artifact"
            )

            temporary.write_bytes(
                b"TRUST_ROBOT_TEST"
            )

            receipt = (
                publish_same_directory_partial_file(
                    temporary,
                    final,
                )
            )

            self.assertFalse(
                temporary.exists()
            )

            self.assertTrue(
                final.exists()
            )

            self.assertTrue(
                receipt[
                    "sha256_stable_across_publish"
                ]
            )

            self.assertTrue(
                receipt[
                    "directory_fsync_after_publish"
                ]
            )

    def test_25_pcap_validator_accepts_classic_one_packet(self):
        with tempfile.TemporaryDirectory() as root:
            path = (
                Path(
                    root
                )
                / "capture.pcap"
            )

            path.write_bytes(
                pcap_bytes()
            )

            result = validate_classic_pcap_file(
                path
            )

            self.assertTrue(
                result[
                    "recognized_magic"
                ]
            )

            self.assertTrue(
                result[
                    "structurally_complete"
                ]
            )

            self.assertEqual(
                result[
                    "packet_count"
                ],
                1,
            )

            self.assertTrue(
                result[
                    "eligible_for_raw_evidence_publication"
                ]
            )

    def test_26_pcap_validator_supports_endian_and_resolution_variants(self):
        variants = (
            (
                "<",
                False,
            ),
            (
                ">",
                False,
            ),
            (
                "<",
                True,
            ),
            (
                ">",
                True,
            ),
        )

        for endian, nano in variants:
            with self.subTest(
                endian=endian,
                nano=nano,
            ):
                with tempfile.TemporaryDirectory() as root:
                    path = (
                        Path(
                            root
                        )
                        / "capture.pcap"
                    )

                    path.write_bytes(
                        pcap_bytes(
                            endian=endian,
                            nanosecond=nano,
                        )
                    )

                    result = validate_classic_pcap_file(
                        path
                    )

                    self.assertTrue(
                        result[
                            "structurally_complete"
                        ]
                    )

    def test_27_pcap_validator_rejects_truncation_and_empty_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            truncated = (
                root_path
                / "truncated.pcap"
            )

            truncated.write_bytes(
                pcap_bytes()[
                    :-1
                ]
            )

            result = validate_classic_pcap_file(
                truncated
            )

            self.assertFalse(
                result[
                    "structurally_complete"
                ]
            )

            empty = (
                root_path
                / "empty.pcap"
            )

            empty.write_bytes(
                pcap_bytes(
                    packet_payloads=()
                )
            )

            empty_result = validate_classic_pcap_file(
                empty
            )

            self.assertTrue(
                empty_result[
                    "structurally_complete"
                ]
            )

            self.assertEqual(
                empty_result[
                    "packet_count"
                ],
                0,
            )

            self.assertFalse(
                empty_result[
                    "eligible_for_raw_evidence_publication"
                ]
            )

    def test_28_finalization_receipt_and_no_network_classifier_api(self):
        with tempfile.TemporaryDirectory() as root:
            path = (
                Path(
                    root
                )
                / "capture.pcap"
            )

            path.write_bytes(
                pcap_bytes()
            )

            receipt = build_pcap_finalization_receipt(
                path,
                process_return_code=124,
                timeout_expired=True,
                sigint_requested=True,
                kill_after_grace_triggered=False,
            )

            self.assertEqual(
                receipt[
                    "process_return_code"
                ],
                124,
            )

            self.assertFalse(
                receipt[
                    "timeout_124_alone_determines_failure"
                ]
            )

            self.assertFalse(
                receipt[
                    "timeout_124_alone_determines_success"
                ]
            )

            self.assertTrue(
                receipt[
                    "pcap_validation"
                ][
                    "eligible_for_raw_evidence_publication"
                ]
            )

        tree = ast.parse(
            MODULE.read_text(
                encoding="utf-8"
            ),
            filename=str(
                MODULE
            ),
        )

        imported = set()

        declarations = {
            node.name.lower()
            for node in ast.walk(
                tree
            )
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                ast.Import,
            ):
                for alias in node.names:
                    imported.add(
                        alias.name.split(
                            "."
                        )[0]
                    )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):
                if node.module:
                    imported.add(
                        node.module.split(
                            "."
                        )[0]
                    )

        for forbidden_module in (
            "subprocess",
            "socket",
            "requests",
            "urllib",
            "http",
        ):
            self.assertNotIn(
                forbidden_module,
                imported,
            )

        for forbidden_api in (
            "execute",
            "run_capture",
            "probe",
            "classify",
            "predict",
            "fit",
            "train",
            "associate",
            "interpolate",
            "accept_source",
            "assign_health",
        ):
            self.assertNotIn(
                forbidden_api,
                declarations,
            )


if __name__ == "__main__":
    unittest.main()
