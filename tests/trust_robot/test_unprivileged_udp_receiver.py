from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path
import ast
import inspect
import json
import socket
import tempfile
import threading
import time
import unittest

from trust_robot.baseline_nominality import (
    BaselineNominalitySplit,
)

from trust_robot.unprivileged_udp_receiver import (
    UnprivilegedUdpReceiverError,
    Vlp32cUnprivilegedUdpReceiverCandidate,
    build_empty_unprivileged_udp_receiver_registry,
    capture_dual_udp_payload_streams,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase5_unprivileged_udp_receiver_candidate_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/unprivileged_udp_receiver.py"
)


def canonical_sha(
    payload,
):
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


def free_udp_port(
):
    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM,
    )

    try:
        sock.bind(
            (
                "127.0.0.1",
                0,
            )
        )

        return sock.getsockname()[
            1
        ]

    finally:
        sock.close()


def candidate(
    root,
    **overrides,
):
    measurement_port = free_udp_port()

    position_port = free_udp_port()

    while (
        position_port
        == measurement_port
    ):
        position_port = free_udp_port()

    values = {
        "acquisition_session_id":
            "SESSION_UDP_TEST",

        "split":
            BaselineNominalitySplit.TRAIN,

        "bind_ipv4":
            "127.0.0.1",

        "measurement_udp_port":
            measurement_port,

        "position_udp_port":
            position_port,

        "capture_duration_seconds":
            1,

        "absolute_output_root":
            str(
                root
            ),
    }

    values.update(
        overrides
    )

    return Vlp32cUnprivilegedUdpReceiverCandidate(
        **values
    )


def read_jsonl(
    path,
):
    return [
        json.loads(
            line
        )
        for line
        in Path(
            path
        ).read_text(
            encoding="utf-8"
        ).splitlines()
        if line
    ]


class UnprivilegedUdpReceiverTests(unittest.TestCase):
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
            build_empty_unprivileged_udp_receiver_registry()
        )

        self.assertTrue(
            payload[
                "loopback_receiver_execution_verified"
            ]
        )

        self.assertFalse(
            payload[
                "real_sensor_receiver_execution_verified"
            ]
        )

        self.assertFalse(
            payload[
                "real_sensor_execution_authorized"
            ]
        )

        self.assertEqual(
            payload[
                "real_health_label_count"
            ],
            0,
        )

    def test_03_required_parameters_have_no_defaults(self):
        signature = inspect.signature(
            Vlp32cUnprivilegedUdpReceiverCandidate
        )

        for name in (
            "acquisition_session_id",
            "split",
            "bind_ipv4",
            "measurement_udp_port",
            "position_udp_port",
            "capture_duration_seconds",
            "absolute_output_root",
        ):
            self.assertIs(
                signature.parameters[
                    name
                ].default,
                inspect.Parameter.empty,
            )

    def test_04_candidate_is_immutable(self):
        with tempfile.TemporaryDirectory() as root:
            value = candidate(
                Path(
                    root
                )
            )

            with self.assertRaises(
                FrozenInstanceError
            ):
                value.bind_ipv4 = "0.0.0.0"

    def test_05_session_id_safe_component_required(self):
        with tempfile.TemporaryDirectory() as root:
            for value in (
                "",
                "../escape",
                "a/b",
            ):
                with self.subTest(
                    value=value
                ):
                    with self.assertRaises(
                        UnprivilegedUdpReceiverError
                    ):
                        candidate(
                            Path(
                                root
                            ),
                            acquisition_session_id=value,
                        )

    def test_06_bind_ipv4_must_be_valid(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(
                UnprivilegedUdpReceiverError
            ):
                candidate(
                    Path(
                        root
                    ),
                    bind_ipv4="not-an-ip",
                )

    def test_07_ipv6_bind_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(
                UnprivilegedUdpReceiverError
            ):
                candidate(
                    Path(
                        root
                    ),
                    bind_ipv4="::1",
                )

    def test_08_measurement_port_bounds(self):
        with tempfile.TemporaryDirectory() as root:
            for port in (
                0,
                65536,
            ):
                with self.subTest(
                    port=port
                ):
                    with self.assertRaises(
                        UnprivilegedUdpReceiverError
                    ):
                        candidate(
                            Path(
                                root
                            ),
                            measurement_udp_port=port,
                        )

    def test_09_position_port_bounds(self):
        with tempfile.TemporaryDirectory() as root:
            for port in (
                0,
                65536,
            ):
                with self.subTest(
                    port=port
                ):
                    with self.assertRaises(
                        UnprivilegedUdpReceiverError
                    ):
                        candidate(
                            Path(
                                root
                            ),
                            position_udp_port=port,
                        )

    def test_10_stream_ports_must_be_distinct(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(
                UnprivilegedUdpReceiverError
            ):
                candidate(
                    Path(
                        root
                    ),
                    measurement_udp_port=25000,
                    position_udp_port=25000,
                )

    def test_11_duration_positive_exact_int(self):
        with tempfile.TemporaryDirectory() as root:
            for value in (
                0,
                -1,
                True,
            ):
                with self.subTest(
                    value=value
                ):
                    with self.assertRaises(
                        UnprivilegedUdpReceiverError
                    ):
                        candidate(
                            Path(
                                root
                            ),
                            capture_duration_seconds=value,
                        )

    def test_12_absolute_output_root_required(self):
        with self.assertRaises(
            UnprivilegedUdpReceiverError
        ):
            Vlp32cUnprivilegedUdpReceiverCandidate(
                acquisition_session_id=
                    "SESSION",

                split=
                    BaselineNominalitySplit.TRAIN,

                bind_ipv4=
                    "127.0.0.1",

                measurement_udp_port=
                    25000,

                position_udp_port=
                    25001,

                capture_duration_seconds=
                    1,

                absolute_output_root=
                    "relative/path",
            )

    def test_13_plan_declares_no_root_sudo_or_raw_capture(self):
        with tempfile.TemporaryDirectory() as root:
            payload = candidate(
                Path(
                    root
                )
            ).to_dict()

            semantics = payload[
                "receiver_semantics"
            ]

            self.assertFalse(
                semantics[
                    "requires_root"
                ]
            )

            self.assertFalse(
                semantics[
                    "requires_sudo"
                ]
            )

            self.assertFalse(
                semantics[
                    "requires_cap_net_raw"
                ]
            )

            self.assertFalse(
                semantics[
                    "passive_interface_sniffing"
                ]
            )

    def test_14_plan_scientific_nonclaims_are_false(self):
        with tempfile.TemporaryDirectory() as root:
            values = candidate(
                Path(
                    root
                )
            ).to_dict()[
                "scientific_nonclaims"
            ]

            self.assertTrue(
                all(
                    item is False
                    for item
                    in values.values()
                )
            )

    def test_15_confirmation_split_unavailable(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(
                UnprivilegedUdpReceiverError
            ):
                candidate(
                    Path(
                        root
                    ),
                    split="confirmation_test",
                )

    def test_16_candidate_is_deterministic(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            value = candidate(
                root_path,
                measurement_udp_port=26000,
                position_udp_port=26001,
            )

            self.assertEqual(
                value.to_dict(),
                value.to_dict(),
            )

    def test_17_integration_dual_stream_exact_payload_capture(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            value = candidate(
                root_path
            )

            measurement_payloads = [
                (
                    b"MEASUREMENT|"
                    + bytes(
                        [
                            index
                        ]
                    )
                    + sha256(
                        str(
                            index
                        ).encode(
                            "ascii"
                        )
                    ).digest()
                )
                for index
                in range(
                    8
                )
            ]

            position_payloads = [
                (
                    b"POSITION|"
                    + bytes(
                        [
                            index
                        ]
                    )
                    + sha256(
                        (
                            "P"
                            + str(
                                index
                            )
                        ).encode(
                            "ascii"
                        )
                    ).digest()
                )
                for index
                in range(
                    8
                )
            ]

            def sender():
                time.sleep(
                    0.20
                )

                sock = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_DGRAM,
                )

                try:
                    for measurement, position in zip(
                        measurement_payloads,
                        position_payloads,
                    ):
                        sock.sendto(
                            measurement,
                            (
                                "127.0.0.1",
                                value.measurement_udp_port,
                            ),
                        )

                        sock.sendto(
                            position,
                            (
                                "127.0.0.1",
                                value.position_udp_port,
                            ),
                        )

                        time.sleep(
                            0.01
                        )

                finally:
                    sock.close()

            thread = threading.Thread(
                target=sender,
                daemon=True,
            )

            thread.start()

            result = capture_dual_udp_payload_streams(
                value
            )

            thread.join(
                timeout=2
            )

            session = Path(
                result[
                    "session_directory"
                ]
            )

            measurement_bytes = (
                session
                / "measurement_payloads.bin"
            ).read_bytes()

            position_bytes = (
                session
                / "position_payloads.bin"
            ).read_bytes()

            self.assertEqual(
                measurement_bytes,
                b"".join(
                    measurement_payloads
                ),
            )

            self.assertEqual(
                position_bytes,
                b"".join(
                    position_payloads
                ),
            )

            receipt = result[
                "capture_receipt"
            ]

            self.assertEqual(
                receipt[
                    "streams"
                ][
                    "measurement"
                ][
                    "datagram_count"
                ],
                8,
            )

            self.assertEqual(
                receipt[
                    "streams"
                ][
                    "position"
                ][
                    "datagram_count"
                ],
                8,
            )

    def test_18_metadata_preserves_boundaries_and_hashes(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            value = candidate(
                root_path
            )

            payloads = [
                b"A" * 11,
                b"B" * 17,
                b"C" * 23,
            ]

            def sender():
                time.sleep(
                    0.20
                )

                sock = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_DGRAM,
                )

                try:
                    for payload in payloads:
                        sock.sendto(
                            payload,
                            (
                                "127.0.0.1",
                                value.measurement_udp_port,
                            ),
                        )

                        sock.sendto(
                            payload,
                            (
                                "127.0.0.1",
                                value.position_udp_port,
                            ),
                        )

                finally:
                    sock.close()

            thread = threading.Thread(
                target=sender,
                daemon=True,
            )

            thread.start()

            result = capture_dual_udp_payload_streams(
                value
            )

            thread.join(
                timeout=2
            )

            session = Path(
                result[
                    "session_directory"
                ]
            )

            archive = (
                session
                / "measurement_payloads.bin"
            ).read_bytes()

            records = read_jsonl(
                session
                / "measurement_datagrams.jsonl"
            )

            reconstructed = []

            for record in records:
                start = record[
                    "payload_offset"
                ]

                end = (
                    start
                    + record[
                        "payload_byte_count"
                    ]
                )

                payload = archive[
                    start:end
                ]

                self.assertEqual(
                    sha256(
                        payload
                    ).hexdigest(),
                    record[
                        "payload_sha256"
                    ],
                )

                reconstructed.append(
                    payload
                )

            self.assertEqual(
                reconstructed,
                payloads,
            )

    def test_19_metadata_marks_host_time_transport_only(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            value = candidate(
                root_path
            )

            def sender():
                time.sleep(
                    0.20
                )

                sock = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_DGRAM,
                )

                try:
                    for port in (
                        value.measurement_udp_port,
                        value.position_udp_port,
                    ):
                        sock.sendto(
                            b"X",
                            (
                                "127.0.0.1",
                                port,
                            ),
                        )

                finally:
                    sock.close()

            thread = threading.Thread(
                target=sender,
                daemon=True,
            )

            thread.start()

            result = capture_dual_udp_payload_streams(
                value
            )

            thread.join(
                timeout=2
            )

            session = Path(
                result[
                    "session_directory"
                ]
            )

            for stream_name in (
                "measurement",
                "position",
            ):
                records = read_jsonl(
                    session
                    / f"{stream_name}_datagrams.jsonl"
                )

                self.assertTrue(
                    records
                )

                for record in records:
                    self.assertTrue(
                        record[
                            "host_receive_times_transport_provenance_only"
                        ]
                    )

                    self.assertFalse(
                        record[
                            "physical_measurement_time_claimed"
                        ]
                    )

                    self.assertFalse(
                        record[
                            "interval_binding_claimed"
                        ]
                    )

                    self.assertFalse(
                        record[
                            "health_label_claimed"
                        ]
                    )

    def test_20_source_endpoint_is_recorded(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            value = candidate(
                root_path
            )

            def sender():
                time.sleep(
                    0.20
                )

                sock = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_DGRAM,
                )

                try:
                    source_port = sock.getsockname()[
                        1
                    ]

                    for port in (
                        value.measurement_udp_port,
                        value.position_udp_port,
                    ):
                        sock.sendto(
                            b"source",
                            (
                                "127.0.0.1",
                                port,
                            ),
                        )

                    return source_port

                finally:
                    sock.close()

            thread = threading.Thread(
                target=sender,
                daemon=True,
            )

            thread.start()

            result = capture_dual_udp_payload_streams(
                value
            )

            thread.join(
                timeout=2
            )

            session = Path(
                result[
                    "session_directory"
                ]
            )

            records = read_jsonl(
                session
                / "measurement_datagrams.jsonl"
            )

            self.assertEqual(
                records[
                    0
                ][
                    "source_ipv4"
                ],
                "127.0.0.1",
            )

            self.assertGreater(
                records[
                    0
                ][
                    "source_udp_port"
                ],
                0,
            )

    def test_21_success_leaves_no_partial_files(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            value = candidate(
                root_path
            )

            def sender():
                time.sleep(
                    0.20
                )

                sock = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_DGRAM,
                )

                try:
                    for port in (
                        value.measurement_udp_port,
                        value.position_udp_port,
                    ):
                        sock.sendto(
                            b"publish",
                            (
                                "127.0.0.1",
                                port,
                            ),
                        )

                finally:
                    sock.close()

            thread = threading.Thread(
                target=sender,
                daemon=True,
            )

            thread.start()

            result = capture_dual_udp_payload_streams(
                value
            )

            thread.join(
                timeout=2
            )

            session = Path(
                result[
                    "session_directory"
                ]
            )

            self.assertEqual(
                list(
                    session.glob(
                        "*.partial"
                    )
                ),
                [],
            )

            self.assertEqual(
                list(
                    session.glob(
                        ".*.partial"
                    )
                ),
                [],
            )

    def test_22_success_receipt_has_stable_publication_hashes(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            value = candidate(
                root_path
            )

            def sender():
                time.sleep(
                    0.20
                )

                sock = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_DGRAM,
                )

                try:
                    for port in (
                        value.measurement_udp_port,
                        value.position_udp_port,
                    ):
                        sock.sendto(
                            b"hash",
                            (
                                "127.0.0.1",
                                port,
                            ),
                        )

                finally:
                    sock.close()

            thread = threading.Thread(
                target=sender,
                daemon=True,
            )

            thread.start()

            result = capture_dual_udp_payload_streams(
                value
            )

            thread.join(
                timeout=2
            )

            receipt = result[
                "capture_receipt"
            ]

            for stream_name in (
                "measurement",
                "position",
            ):
                for kind in (
                    "payload_artifact",
                    "metadata_artifact",
                ):
                    artifact = receipt[
                        "streams"
                    ][
                        stream_name
                    ][
                        kind
                    ]

                    self.assertTrue(
                        artifact[
                            "sha256_stable_across_publish"
                        ]
                    )

                    self.assertEqual(
                        artifact[
                            "prepublish_sha256"
                        ],
                        artifact[
                            "postpublish_sha256"
                        ],
                    )

    def test_23_zero_stream_is_not_published_as_health_state(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            value = candidate(
                root_path
            )

            def sender():
                time.sleep(
                    0.20
                )

                sock = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_DGRAM,
                )

                try:
                    sock.sendto(
                        b"measurement-only",
                        (
                            "127.0.0.1",
                            value.measurement_udp_port,
                        ),
                    )

                finally:
                    sock.close()

            thread = threading.Thread(
                target=sender,
                daemon=True,
            )

            thread.start()

            with self.assertRaises(
                UnprivilegedUdpReceiverError
            ):
                capture_dual_udp_payload_streams(
                    value
                )

            thread.join(
                timeout=2
            )

    def test_24_fresh_session_collision_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(
                root
            )

            (
                root_path
                / "SESSION_UDP_TEST"
            ).mkdir()

            value = candidate(
                root_path
            )

            with self.assertRaises(
                UnprivilegedUdpReceiverError
            ):
                capture_dual_udp_payload_streams(
                    value
                )

    def test_25_nonexistent_output_root_rejected_on_capture(self):
        with tempfile.TemporaryDirectory() as root:
            missing = (
                Path(
                    root
                )
                / "missing"
            )

            value = candidate(
                missing
            )

            with self.assertRaises(
                UnprivilegedUdpReceiverError
            ):
                capture_dual_udp_payload_streams(
                    value
                )

    def test_26_module_does_not_use_raw_packet_capture_or_subprocess(self):
        source = MODULE.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "SOCK_RAW",
            source,
        )

        self.assertNotIn(
            "AF_PACKET",
            source,
        )

        tree = ast.parse(
            source,
            filename=str(
                MODULE
            ),
        )

        imported = set()

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

        for forbidden in (
            "subprocess",
            "requests",
            "urllib",
        ):
            self.assertNotIn(
                forbidden,
                imported,
            )

    def test_27_no_classifier_association_or_acceptance_api(self):
        tree = ast.parse(
            MODULE.read_text(
                encoding="utf-8"
            ),
            filename=str(
                MODULE
            ),
        )

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

        for forbidden in (
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
                forbidden,
                declarations,
            )

    def test_28_source_file_contains_only_udp_datagram_socket_constructor(self):
        source = MODULE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(
                MODULE
            ),
        )

        socket_calls = []

        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            function = node.func

            if (
                isinstance(
                    function,
                    ast.Attribute,
                )
                and function.attr
                == "socket"
                and isinstance(
                    function.value,
                    ast.Name,
                )
                and function.value.id
                == "socket"
            ):
                socket_calls.append(
                    node
                )

        self.assertEqual(
            len(
                socket_calls
            ),
            1,
        )

        call = socket_calls[
            0
        ]

        self.assertGreaterEqual(
            len(
                call.args
            ),
            2,
        )

        family = call.args[
            0
        ]

        socket_type = call.args[
            1
        ]

        self.assertIsInstance(
            family,
            ast.Attribute,
        )

        self.assertIsInstance(
            family.value,
            ast.Name,
        )

        self.assertEqual(
            family.value.id,
            "socket",
        )

        self.assertEqual(
            family.attr,
            "AF_INET",
        )

        self.assertIsInstance(
            socket_type,
            ast.Attribute,
        )

        self.assertIsInstance(
            socket_type.value,
            ast.Name,
        )

        self.assertEqual(
            socket_type.value.id,
            "socket",
        )

        self.assertEqual(
            socket_type.attr,
            "SOCK_DGRAM",
        )

        self.assertNotIn(
            "SOCK_RAW",
            source,
        )

        self.assertNotIn(
            "AF_PACKET",
            source,
        )


if __name__ == "__main__":
    unittest.main()
