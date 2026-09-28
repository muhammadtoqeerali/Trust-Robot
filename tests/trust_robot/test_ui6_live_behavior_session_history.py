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
    live_route_contract,
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
    "ui6_live_behavior_session_history_contract_v1.json"
)


class DashboardUI6LiveHistoryTests(
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

        cls.history = cls.snapshot[
            "session_history"
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
            "TRUST_ROBOT_UI6_LIVE_BEHAVIOR_SESSION_HISTORY_CONTRACT_V1",
        )

    def test_02_live_endpoint_contract(self):
        self.assertEqual(
            self.contract[
                "live_update"
            ][
                "endpoint"
            ],
            "/api/v1/events",
        )

    def test_03_transport_is_EventSource(self):
        self.assertEqual(
            self.contract[
                "live_update"
            ][
                "frontend_transport"
            ],
            "EventSource",
        )

    def test_04_transport_time_not_sensor_time(self):
        self.assertFalse(
            self.contract[
                "live_update"
            ][
                "sensor_measurement_time"
            ]
        )

    def test_05_session_history_exists(self):
        self.assertIn(
            "session_history",
            self.snapshot,
        )

    def test_06_history_record_count(self):
        self.assertEqual(
            self.history[
                "record_count"
            ],
            2,
        )

    def test_07_real_sensor_session_count_zero(self):
        self.assertEqual(
            self.history[
                "real_sensor_session_count"
            ],
            0,
        )

    def test_08_real_sensor_history_unavailable(self):
        self.assertFalse(
            self.history[
                "real_sensor_session_history_available"
            ]
        )

    def test_09_history_not_real_sensor_history(self):
        self.assertFalse(
            self.history[
                "history_is_real_sensor_history"
            ]
        )

    def test_10_history_creates_no_scientific_evidence(self):
        self.assertFalse(
            self.history[
                "history_creates_new_scientific_evidence"
            ]
        )

    def test_11_first_record_software_qualification(self):
        record = self.history[
            "records"
        ][0]

        self.assertEqual(
            record[
                "kind"
            ],
            "software_qualification",
        )

        self.assertFalse(
            record[
                "synthetic"
            ]
        )

    def test_12_first_record_room_02(self):
        self.assertEqual(
            self.history[
                "records"
            ][0][
                "trajectory_id"
            ],
            "room_02",
        )

    def test_13_first_record_not_real_sensor_session(self):
        self.assertFalse(
            self.history[
                "records"
            ][0][
                "real_sensor_session"
            ]
        )

    def test_14_first_record_time_not_claimed(self):
        record = self.history[
            "records"
        ][0]

        self.assertIsNone(
            record[
                "execution_timestamp"
            ]
        )

        self.assertEqual(
            record[
                "time_basis"
            ],
            "execution_time_not_claimed",
        )

    def test_15_second_record_synthetic(self):
        record = self.history[
            "records"
        ][1]

        self.assertTrue(
            record[
                "synthetic"
            ]
        )

        self.assertEqual(
            record[
                "kind"
            ],
            "synthetic_live_stack",
        )

    def test_16_second_record_not_real_sensor_session(self):
        self.assertFalse(
            self.history[
                "records"
            ][1][
                "real_sensor_session"
            ]
        )

    def test_17_both_history_records_passed(self):
        self.assertTrue(
            all(
                record[
                    "state"
                ] == "passed"
                for record
                in self.history[
                    "records"
                ]
            )
        )

    def test_18_receipt_hashes_present(self):
        self.assertTrue(
            all(
                len(
                    record[
                        "receipt_sha256"
                    ]
                )
                == 64
                for record
                in self.history[
                    "records"
                ]
            )
        )

    def test_19_no_real_network_IO(self):
        self.assertFalse(
            self.snapshot[
                "operations"
            ][
                "real_network_IO_executed"
            ]
        )

    def test_20_no_real_sensor_contact(self):
        self.assertFalse(
            self.snapshot[
                "operations"
            ][
                "real_sensor_contact"
            ]
        )

    def test_21_SE4_still_incomplete(self):
        self.assertFalse(
            self.snapshot[
                "scientific_boundary"
            ][
                "SE4_complete"
            ]
        )

    def test_22_SE5_still_blocked(self):
        self.assertTrue(
            self.snapshot[
                "scientific_boundary"
            ][
                "SE5_entry_blocked"
            ]
        )

    def test_23_HTML_live_status(self):
        self.assertIn(
            'id="live-update-chip"',
            self.html,
        )

        self.assertIn(
            'id="last-update-age"',
            self.html,
        )

    def test_24_HTML_manual_refresh(self):
        self.assertIn(
            'id="refresh-button"',
            self.html,
        )

    def test_25_HTML_session_history(self):
        self.assertIn(
            'id="session-history-list"',
            self.html,
        )

    def test_26_HTML_real_session_count(self):
        self.assertIn(
            'id="real-session-history-count"',
            self.html,
        )

    def test_27_JS_EventSource_endpoint(self):
        self.assertIn(
            'const LIVE_EVENTS_ENDPOINT = "/api/v1/events"',
            self.js,
        )

        self.assertIn(
            "new EventSource(",
            self.js,
        )

    def test_28_JS_manual_refresh(self):
        self.assertIn(
            "bindRefresh",
            self.js,
        )

        self.assertIn(
            '"click"',
            self.js,
        )

    def test_29_JS_live_event_schema_guard(self):
        self.assertIn(
            "TRUST_ROBOT_DASHBOARD_LIVE_EVENT_V1",
            self.js,
        )

    def test_30_JS_transport_time_boundary_guard(self):
        self.assertIn(
            "payload.transport_time_is_sensor_measurement_time",
            self.js,
        )

    def test_31_JS_last_update_age(self):
        self.assertIn(
            "updateLastUpdateAge",
            self.js,
        )

        self.assertIn(
            "Updated ${ageSeconds}s ago",
            self.js,
        )

    def test_32_JS_history_renderer(self):
        self.assertIn(
            "renderSessionHistory",
            self.js,
        )

    def test_33_JS_closes_EventSource(self):
        self.assertIn(
            'window.addEventListener(\n  "beforeunload"',
            self.js,
        )

        self.assertIn(
            "eventSource.close()",
            self.js,
        )

    def test_34_no_write_HTTP_methods(self):
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

    def test_35_no_innerHTML(self):
        self.assertNotIn(
            ".innerHTML",
            self.js,
        )

    def test_36_CSS_live_chip(self):
        self.assertIn(
            ".live-update-chip",
            self.css,
        )

        self.assertIn(
            ".live-update-chip.is-live",
            self.css,
        )

    def test_37_CSS_history(self):
        self.assertIn(
            ".session-history-list",
            self.css,
        )

        self.assertIn(
            ".session-history-item",
            self.css,
        )

    def test_38_javascript_syntax(self):
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


class DashboardUI6ServingTests(
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

    async def test_39_live_route_contract(self):
        self.assertEqual(
            live_route_contract(),
            (
                "GET /api/v1/events",
            ),
        )

    async def test_40_events_endpoint_status(self):
        response = await self.client.get(
            f"{API_PREFIX}/events"
        )

        self.assertEqual(
            response.status,
            200,
        )

    async def test_41_events_content_type(self):
        response = await self.client.get(
            f"{API_PREFIX}/events"
        )

        self.assertTrue(
            response.headers[
                "Content-Type"
            ].startswith(
                "text/event-stream"
            )
        )

    async def test_42_events_payload(self):
        response = await self.client.get(
            f"{API_PREFIX}/events"
        )

        text = await response.text()

        self.assertTrue(
            text.startswith(
                "retry: 5000\n"
            )
        )

        data_line = [
            line
            for line
            in text.splitlines()
            if line.startswith(
                "data: "
            )
        ][0]

        payload = json.loads(
            data_line[
                len(
                    "data: "
                ):
            ]
        )

        self.assertEqual(
            payload[
                "schema"
            ],
            "TRUST_ROBOT_DASHBOARD_LIVE_EVENT_V1",
        )

        self.assertFalse(
            payload[
                "transport_time_is_sensor_measurement_time"
            ]
        )

        self.assertTrue(
            payload[
                "snapshot"
            ][
                "read_only"
            ]
        )

    async def test_43_events_has_transport_timestamp(self):
        response = await self.client.get(
            f"{API_PREFIX}/events"
        )

        text = await response.text()

        data_line = [
            line
            for line
            in text.splitlines()
            if line.startswith(
                "data: "
            )
        ][0]

        payload = json.loads(
            data_line[
                6:
            ]
        )

        self.assertTrue(
            payload[
                "transport_observed_at_utc"
            ].endswith(
                "Z"
            )
        )

    async def test_44_events_no_store(self):
        response = await self.client.get(
            f"{API_PREFIX}/events"
        )

        self.assertEqual(
            response.headers[
                "Cache-Control"
            ],
            "no-store, max-age=0",
        )

    async def test_45_events_post_blocked(self):
        response = await self.client.post(
            f"{API_PREFIX}/events",
            json={
                "write":
                    True,
            },
        )

        self.assertEqual(
            response.status,
            405,
        )

    async def test_46_snapshot_contains_history(self):
        response = await self.client.get(
            f"{API_PREFIX}/snapshot"
        )

        payload = await response.json()

        self.assertEqual(
            payload[
                "session_history"
            ][
                "real_sensor_session_count"
            ],
            0,
        )

        self.assertEqual(
            payload[
                "session_history"
            ][
                "record_count"
            ],
            2,
        )


if __name__ == "__main__":
    unittest.main()
