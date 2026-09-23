from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path
import ast
import inspect
import json
import unittest

from trust_robot.baseline_nominality import (
    BaselineNominalitySplit,
)

from trust_robot.live_acquisition_plan import (
    LiveAcquisitionPlanError,
    Vlp32cLiveAcquisitionPlanCandidate,
    build_empty_live_acquisition_plan_registry,
)


ROOT = Path(__file__).resolve().parents[2]

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase5_live_acquisition_plan_candidate_v1.json"
)

MODULE = (
    ROOT
    / "src/trust_robot/live_acquisition_plan.py"
)

RUNNER = (
    ROOT
    / "scripts/trust_robot/"
      "plan_phase5_vlp32c_live_acquisition.py"
)


def canonical_sha(payload):
    value = dict(payload)
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
        ).encode("utf-8")
    ).hexdigest()


def plan(**overrides):
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

        "output_directory":
            "/tmp/TRUST_ROBOT_TEST_CAPTURE",
    }

    values.update(
        overrides
    )

    return Vlp32cLiveAcquisitionPlanCandidate(
        **values
    )


class LiveAcquisitionPlanTests(unittest.TestCase):
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

    def test_02_empty_registry_has_no_live_state(self):
        payload = (
            build_empty_live_acquisition_plan_registry()
        )

        self.assertEqual(
            payload[
                "live_plan_instance_count"
            ],
            0,
        )

        self.assertFalse(
            payload[
                "sensor_network_address_selected"
            ]
        )

        self.assertFalse(
            payload[
                "live_execution_authorized"
            ]
        )

    def test_03_valid_plan_is_nonexecuting(self):
        payload = plan().to_dict()

        boundary = payload[
            "execution_boundary"
        ]

        self.assertTrue(
            boundary[
                "argv_plan_only"
            ]
        )

        self.assertFalse(
            boundary[
                "subprocess_executed"
            ]
        )

        self.assertFalse(
            boundary[
                "network_io_performed"
            ]
        )

    def test_04_runtime_parameters_have_no_constructor_defaults(self):
        signature = inspect.signature(
            Vlp32cLiveAcquisitionPlanCandidate
        )

        for name in (
            "acquisition_session_id",
            "split",
            "sensor_ipv4",
            "capture_interface",
            "data_udp_port",
            "telemetry_udp_port",
            "capture_duration_seconds",
            "output_directory",
        ):
            self.assertIs(
                signature.parameters[
                    name
                ].default,
                inspect.Parameter.empty,
            )

    def test_05_plan_is_immutable(self):
        value = plan()

        with self.assertRaises(
            FrozenInstanceError
        ):
            value.sensor_ipv4 = "192.0.2.20"

    def test_06_invalid_ipv4_rejected(self):
        with self.assertRaises(
            LiveAcquisitionPlanError
        ):
            plan(
                sensor_ipv4="not-an-ip"
            )

    def test_07_ipv6_rejected(self):
        with self.assertRaises(
            LiveAcquisitionPlanError
        ):
            plan(
                sensor_ipv4="2001:db8::1"
            )

    def test_08_data_port_lower_bound(self):
        with self.assertRaises(
            LiveAcquisitionPlanError
        ):
            plan(
                data_udp_port=0
            )

    def test_09_data_port_upper_bound(self):
        with self.assertRaises(
            LiveAcquisitionPlanError
        ):
            plan(
                data_udp_port=65536
            )

    def test_10_telemetry_port_bounds(self):
        for value in (
            0,
            65536,
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    LiveAcquisitionPlanError
                ):
                    plan(
                        telemetry_udp_port=value
                    )

    def test_11_duration_must_be_positive_exact_int(self):
        for value in (
            0,
            -1,
            True,
        ):
            with self.subTest(
                value=value
            ):
                with self.assertRaises(
                    LiveAcquisitionPlanError
                ):
                    plan(
                        capture_duration_seconds=value
                    )

    def test_12_interface_required(self):
        with self.assertRaises(
            LiveAcquisitionPlanError
        ):
            plan(
                capture_interface=""
            )

    def test_13_output_directory_required(self):
        with self.assertRaises(
            LiveAcquisitionPlanError
        ):
            plan(
                output_directory=""
            )

    def test_14_confirmation_split_unavailable(self):
        with self.assertRaises(
            LiveAcquisitionPlanError
        ):
            plan(
                split="confirmation_test"
            )

    def test_15_identity_endpoint_exact(self):
        argv = plan().command_argv()[
            "identity_http"
        ]

        self.assertIn(
            "http://192.0.2.10/cgi/info.json",
            argv,
        )

    def test_16_status_endpoint_exact(self):
        argv = plan().command_argv()[
            "status_http"
        ]

        self.assertIn(
            "http://192.0.2.10/cgi/status.json",
            argv,
        )

    def test_17_diagnostic_endpoint_exact(self):
        argv = plan().command_argv()[
            "diagnostic_http"
        ]

        self.assertIn(
            "http://192.0.2.10/cgi/diag.json",
            argv,
        )

    def test_18_http_bodies_and_headers_are_separate(self):
        commands = plan().command_argv()

        identity = commands[
            "identity_http"
        ]

        self.assertIn(
            "/tmp/TRUST_ROBOT_TEST_CAPTURE/info.json",
            identity,
        )

        self.assertIn(
            "/tmp/TRUST_ROBOT_TEST_CAPTURE/info.headers",
            identity,
        )

    def test_19_measurement_packet_capture_uses_explicit_port(self):
        argv = plan().command_argv()[
            "measurement_packet_capture"
        ]

        self.assertIn(
            "host 192.0.2.10 and udp port 12000",
            argv,
        )

        self.assertIn(
            "/tmp/TRUST_ROBOT_TEST_CAPTURE/measurement_packets.pcap",
            argv,
        )

    def test_20_position_packet_capture_uses_explicit_port(self):
        argv = plan().command_argv()[
            "position_packet_capture"
        ]

        self.assertIn(
            "host 192.0.2.10 and udp port 12001",
            argv,
        )

        self.assertIn(
            "/tmp/TRUST_ROBOT_TEST_CAPTURE/position_packets.pcap",
            argv,
        )

    def test_21_packet_capture_is_duration_bounded_candidate(self):
        argv = plan().command_argv()[
            "measurement_packet_capture"
        ]

        self.assertEqual(
            argv[:4],
            [
                "timeout",
                "--signal=INT",
                "10s",
                "tcpdump",
            ],
        )

    def test_22_commands_are_argv_arrays_not_shell_strings(self):
        commands = plan().command_argv()

        self.assertTrue(
            all(
                isinstance(
                    value,
                    list,
                )
                for value
                in commands.values()
            )
        )

        self.assertTrue(
            all(
                all(
                    isinstance(
                        arg,
                        str,
                    )
                    for arg
                    in value
                )
                for value
                in commands.values()
            )
        )

    def test_23_scientific_nonclaims_remain_false(self):
        nonclaims = plan().to_dict()[
            "scientific_nonclaims"
        ]

        self.assertTrue(
            all(
                value is False
                for value
                in nonclaims.values()
            )
        )

    def test_24_plan_is_deterministic(self):
        self.assertEqual(
            plan().to_dict(),
            plan().to_dict(),
        )

    def test_25_module_and_runner_have_no_network_execution_imports(self):
        forbidden_modules = {
            "subprocess",
            "socket",
            "requests",
            "urllib",
            "http",
        }

        for path in (
            MODULE,
            RUNNER,
        ):
            tree = ast.parse(
                path.read_text(
                    encoding="utf-8"
                ),
                filename=str(path),
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

            self.assertTrue(
                forbidden_modules.isdisjoint(
                    imported
                ),
                (
                    path,
                    forbidden_modules
                    & imported,
                ),
            )

    def test_26_no_execute_classifier_acceptance_or_association_api(self):
        for path in (
            MODULE,
            RUNNER,
        ):
            tree = ast.parse(
                path.read_text(
                    encoding="utf-8"
                ),
                filename=str(path),
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
                    forbidden,
                    declarations,
                )


if __name__ == "__main__":
    unittest.main()
