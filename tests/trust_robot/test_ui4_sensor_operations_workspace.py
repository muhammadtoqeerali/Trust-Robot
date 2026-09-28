from pathlib import Path
import json
import subprocess
import unittest

from aiohttp.test_utils import (
    TestClient,
    TestServer,
)

from trust_robot.dashboard_api import (
    API_PREFIX,
    create_dashboard_app,
    route_contract,
)

from trust_robot.dashboard_state import (
    build_dashboard_snapshot,
    validate_dashboard_snapshot,
)


ROOT = Path(
    __file__
).resolve().parents[2]

INDEX = (
    ROOT
    / "src/trust_robot/dashboard_web/index.html"
)

CSS = (
    ROOT
    / "src/trust_robot/dashboard_web/styles.css"
)

JS = (
    ROOT
    / "src/trust_robot/dashboard_web/app.js"
)

CONTRACT = (
    ROOT
    / "configs/trust_robot/"
    "ui4_sensor_operations_workspace_contract_v1.json"
)


class DashboardUI4OperationsTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.snapshot = build_dashboard_snapshot(
            ROOT
        )

        validate_dashboard_snapshot(
            cls.snapshot
        )

        cls.operations = cls.snapshot[
            "operations"
        ]

        cls.contract = json.loads(
            CONTRACT.read_text(
                encoding="utf-8"
            )
        )

        cls.html = INDEX.read_text(
            encoding="utf-8"
        )

        cls.css = CSS.read_text(
            encoding="utf-8"
        )

        cls.js = JS.read_text(
            encoding="utf-8"
        )

    def test_01_contract_schema(self):
        self.assertEqual(
            self.contract[
                "schema"
            ],
            "TRUST_ROBOT_UI4_SENSOR_OPERATIONS_WORKSPACE_CONTRACT_V1",
        )

    def test_02_operations_projection_exists(self):
        self.assertIn(
            "operations",
            self.snapshot,
        )

    def test_03_mode_software_only(self):
        self.assertEqual(
            self.operations[
                "mode"
            ],
            "software_only",
        )

    def test_04_real_runtime_not_activated(self):
        self.assertFalse(
            self.operations[
                "live_real_runtime_activated"
            ]
        )

    def test_05_binding_field_count(self):
        self.assertEqual(
            self.operations[
                "runtime_binding"
            ][
                "required_field_count"
            ],
            16,
        )

    def test_06_binding_field_names_exact(self):
        self.assertEqual(
            self.operations[
                "runtime_binding"
            ][
                "required_fields"
            ],
            [
                "acquisition_session_id",
                "split",
                "bind_ipv4",
                "measurement_udp_port",
                "position_udp_port",
                "sensor_ipv4",
                "capture_duration_seconds",
                "http_port",
                "absolute_output_root",
                "http_connect_timeout_seconds",
                "http_total_timeout_seconds",
                "vlp32c_destination_ipv4",
                "vlp32c_measurement_destination_udp_port",
                "vlp32c_position_destination_udp_port",
                "vlp32c_destination_configuration_verified",
                "declared_before_execution",
            ],
        )

    def test_07_real_bound_field_count_zero(self):
        self.assertEqual(
            self.operations[
                "runtime_binding"
            ][
                "real_bound_field_count"
            ],
            0,
        )

    def test_08_real_binding_values_unavailable(self):
        self.assertFalse(
            self.operations[
                "runtime_binding"
            ][
                "values_available"
            ]
        )

    def test_09_real_session_not_started(self):
        self.assertFalse(
            self.operations[
                "session"
            ][
                "real_session_started"
            ]
        )

    def test_10_real_session_id_unavailable(self):
        self.assertIsNone(
            self.operations[
                "session"
            ][
                "real_session_id"
            ]
        )

    def test_11_measurement_channel(self):
        channel = self.operations[
            "channels"
        ][0]

        self.assertEqual(
            channel[
                "id"
            ],
            "measurement_udp",
        )

        self.assertEqual(
            channel[
                "protocol"
            ],
            "UDP",
        )

    def test_12_position_channel(self):
        self.assertEqual(
            self.operations[
                "channels"
            ][1][
                "id"
            ],
            "position_udp",
        )

    def test_13_identity_path(self):
        self.assertEqual(
            self.operations[
                "channels"
            ][2][
                "path"
            ],
            "/cgi/info.json",
        )

    def test_14_status_path(self):
        self.assertEqual(
            self.operations[
                "channels"
            ][3][
                "path"
            ],
            "/cgi/status.json",
        )

    def test_15_diagnostic_path(self):
        self.assertEqual(
            self.operations[
                "channels"
            ][4][
                "path"
            ],
            "/cgi/diag.json",
        )

    def test_16_all_channels_not_executed(self):
        for channel in self.operations[
            "channels"
        ]:
            self.assertEqual(
                channel[
                    "execution_state"
                ],
                "not_executed",
            )

    def test_17_all_real_endpoints_unavailable(self):
        for channel in self.operations[
            "channels"
        ]:
            self.assertFalse(
                channel[
                    "real_endpoint_available"
                ]
            )

    def test_18_execution_authorization_count_zero(self):
        self.assertEqual(
            self.operations[
                "authorization"
            ][
                "real_execution_authorization_count"
            ],
            0,
        )

    def test_19_grounded_authorization_count_zero(self):
        self.assertEqual(
            self.operations[
                "authorization"
            ][
                "grounded_authorization_record_count"
            ],
            0,
        )

    def test_20_synthetic_qualification_passed(self):
        self.assertTrue(
            self.operations[
                "synthetic_qualification"
            ][
                "qualified"
            ]
        )

    def test_21_synthetic_execution_order(self):
        self.assertEqual(
            self.operations[
                "synthetic_qualification"
            ][
                "execution_order"
            ],
            [
                "UDP",
                "HTTP:identity",
                "HTTP:status",
                "HTTP:diagnostic",
            ],
        )

    def test_22_synthetic_receipts_exist(self):
        synthetic = self.operations[
            "synthetic_qualification"
        ]

        self.assertTrue(
            synthetic[
                "UDP_receipt_produced"
            ]
        )

        self.assertTrue(
            synthetic[
                "identity_receipt_produced"
            ]
        )

        self.assertTrue(
            synthetic[
                "status_receipt_produced"
            ]
        )

        self.assertTrue(
            synthetic[
                "diagnostic_receipt_produced"
            ]
        )

        self.assertTrue(
            synthetic[
                "composite_receipt_produced"
            ]
        )

    def test_23_synthetic_is_not_real_evidence(self):
        self.assertFalse(
            self.operations[
                "synthetic_qualification"
            ][
                "real_sensor_evidence"
            ]
        )

    def test_24_no_real_network_IO(self):
        self.assertFalse(
            self.operations[
                "real_network_IO_executed"
            ]
        )

    def test_25_no_real_sensor_contact(self):
        self.assertFalse(
            self.operations[
                "real_sensor_contact"
            ]
        )

    def test_26_lifecycle_count(self):
        self.assertEqual(
            len(
                self.operations[
                    "lifecycle"
                ]
            ),
            7,
        )

    def test_27_lifecycle_waits_for_binding(self):
        self.assertEqual(
            self.operations[
                "lifecycle"
            ][0][
                "state"
            ],
            "waiting",
        )

    def test_28_no_real_execution_control(self):
        self.assertFalse(
            self.operations[
                "controls"
            ][
                "execute_real_sensor"
            ]
        )

    def test_29_no_authorization_control(self):
        self.assertFalse(
            self.operations[
                "controls"
            ][
                "create_authorization"
            ]
        )

    def test_30_no_health_label_control(self):
        self.assertFalse(
            self.operations[
                "controls"
            ][
                "create_health_label"
            ]
        )

    def test_31_HTML_binding_grid(self):
        self.assertIn(
            'id="binding-field-grid"',
            self.html,
        )

    def test_32_HTML_channel_table(self):
        self.assertIn(
            'id="operations-channel-body"',
            self.html,
        )

    def test_33_HTML_lifecycle(self):
        self.assertIn(
            'id="operations-lifecycle"',
            self.html,
        )

    def test_34_JS_renders_channels(self):
        self.assertIn(
            "renderOperationsChannels",
            self.js,
        )

    def test_35_JS_renders_lifecycle(self):
        self.assertIn(
            "renderOperationsLifecycle",
            self.js,
        )

    def test_36_CSS_channel_workspace(self):
        self.assertIn(
            ".operations-readiness-grid",
            self.css,
        )

        self.assertIn(
            ".operations-lifecycle",
            self.css,
        )

    def test_37_no_real_execution_UI_phrase(self):
        self.assertNotIn(
            "Start Real Acquisition",
            self.html,
        )

    def test_38_Javascript_has_no_write_methods(self):
        for method in (
            'method: "POST"',
            'method: "PUT"',
            'method: "PATCH"',
            'method: "DELETE"',
        ):
            self.assertNotIn(
                method,
                self.js,
            )

    def test_39_ATE_RPE_truth_display(self):
        self.assertIn(
            'science.ATE_RPE_computed ? "Computed" : "Unavailable"',
            self.js,
        )

    def test_40_javascript_syntax(self):
        result = subprocess.run(
            [
                "node",
                "--check",
                str(
                    JS
                ),
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=result.stderr,
        )


class DashboardUI4ServingTests(
    unittest.IsolatedAsyncioTestCase
):
    async def asyncSetUp(
        self,
    ):
        app = create_dashboard_app(
            ROOT
        )

        self.server = TestServer(
            app,
            host="127.0.0.1",
            port=0,
        )

        self.client = TestClient(
            self.server
        )

        await self.client.start_server()

    async def asyncTearDown(
        self,
    ):
        await self.client.close()

    async def test_41_operations_route_contract(self):
        self.assertIn(
            "GET /api/v1/operations",
            route_contract(),
        )

    async def test_42_operations_endpoint(self):
        response = await self.client.get(
            f"{API_PREFIX}/operations"
        )

        self.assertEqual(
            response.status,
            200,
        )

        payload = await response.json()

        self.assertEqual(
            payload[
                "runtime_binding"
            ][
                "required_field_count"
            ],
            16,
        )

    async def test_43_operations_endpoint_is_read_only(self):
        response = await self.client.post(
            f"{API_PREFIX}/operations",
            json={
                "execute":
                    True,
            },
        )

        self.assertEqual(
            response.status,
            405,
        )

    async def test_44_snapshot_preserves_scientific_boundary(self):
        response = await self.client.get(
            f"{API_PREFIX}/snapshot"
        )

        payload = await response.json()

        self.assertFalse(
            payload[
                "operations"
            ][
                "real_sensor_connected"
            ]
        )

        self.assertFalse(
            payload[
                "scientific_boundary"
            ][
                "SE4_complete"
            ]
        )

        self.assertTrue(
            payload[
                "scientific_boundary"
            ][
                "SE5_entry_blocked"
            ]
        )


if __name__ == "__main__":
    unittest.main()
