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
    "ui5_evidence_health_workspace_contract_v1.json"
)


class DashboardUI5EvidenceHealthTests(
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

        cls.receipts = cls.snapshot[
            "receipts"
        ]

        cls.health = cls.snapshot[
            "health_supervision"
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
            "TRUST_ROBOT_UI5_EVIDENCE_HEALTH_WORKSPACE_CONTRACT_V1",
        )

    def test_02_receipts_projection_exists(self):
        self.assertIn(
            "receipts",
            self.snapshot,
        )

    def test_03_health_projection_exists(self):
        self.assertIn(
            "health_supervision",
            self.snapshot,
        )

    def test_04_receipt_count(self):
        self.assertEqual(
            self.receipts[
                "receipt_count"
            ],
            2,
        )

    def test_05_run_specific_receipt_count(self):
        self.assertEqual(
            self.receipts[
                "run_specific_receipt_count"
            ],
            2,
        )

    def test_06_real_sensor_receipt_count_zero(self):
        self.assertEqual(
            self.receipts[
                "real_sensor_receipt_count"
            ],
            0,
        )

    def test_07_real_runtime_evidence_unavailable(self):
        self.assertFalse(
            self.receipts[
                "real_sensor_runtime_evidence_available"
            ]
        )

    def test_08_receipt_hash_not_truth_by_itself(self):
        self.assertFalse(
            self.receipts[
                "receipt_hashes_are_scientific_truth_by_themselves"
            ]
        )

    def test_09_qualification_receipt_available(self):
        receipt = self.receipts[
            "registry"
        ][0]

        self.assertEqual(
            receipt[
                "availability"
            ],
            "available",
        )

        self.assertFalse(
            receipt[
                "synthetic"
            ]
        )

        self.assertFalse(
            receipt[
                "real_sensor_evidence"
            ]
        )

    def test_10_qualification_receipt_hashes_present(self):
        receipt = self.receipts[
            "registry"
        ][0]

        self.assertEqual(
            len(
                receipt[
                    "file_sha256"
                ]
            ),
            64,
        )

        self.assertEqual(
            len(
                receipt[
                    "content_sha256"
                ]
            ),
            64,
        )

    def test_11_synthetic_receipt_labeled(self):
        receipt = self.receipts[
            "registry"
        ][1]

        self.assertTrue(
            receipt[
                "synthetic"
            ]
        )

        self.assertEqual(
            receipt[
                "availability"
            ],
            "available_synthetic",
        )

    def test_12_synthetic_receipt_not_real_sensor_evidence(self):
        self.assertFalse(
            self.receipts[
                "registry"
            ][1][
                "real_sensor_evidence"
            ]
        )

    def test_13_synthetic_receipt_not_stability_requirement(self):
        self.assertFalse(
            self.receipts[
                "registry"
            ][1][
                "stability_requirement"
            ]
        )

    def test_14_health_status_blocked(self):
        self.assertEqual(
            self.health[
                "status"
            ],
            "blocked_pending_accepted_health_supervision",
        )

    def test_15_baseline_nominality_zero(self):
        self.assertEqual(
            self.health[
                "accepted_baseline_nominality_source_count"
            ],
            0,
        )

    def test_16_health_supervision_zero(self):
        self.assertEqual(
            self.health[
                "accepted_health_supervision_source_count"
            ],
            0,
        )

    def test_17_real_health_labels_zero(self):
        self.assertEqual(
            self.health[
                "real_health_label_count"
            ],
            0,
        )

    def test_18_no_health_label_generated(self):
        self.assertFalse(
            self.health[
                "health_label_generated"
            ]
        )

    def test_19_interval_binding_unavailable(self):
        self.assertFalse(
            self.health[
                "interval_binding_established"
            ]
        )

    def test_20_measurement_time_unavailable(self):
        self.assertFalse(
            self.health[
                "physical_measurement_time_established"
            ]
        )

    def test_21_SE2_training_blocked(self):
        self.assertTrue(
            self.health[
                "SE2_health_model_training_blocked"
            ]
        )

    def test_22_SE4_training_blocked(self):
        self.assertTrue(
            self.health[
                "SE4_training_execution_blocked"
            ]
        )

    def test_23_SE4_incomplete(self):
        self.assertFalse(
            self.health[
                "SE4_complete"
            ]
        )

    def test_24_SE4_training_unauthorized(self):
        self.assertFalse(
            self.health[
                "SE4_training_authorized"
            ]
        )

    def test_25_SE5_blocked(self):
        self.assertTrue(
            self.health[
                "SE5_entry_blocked"
            ]
        )

    def test_26_training_not_ready(self):
        self.assertFalse(
            self.health[
                "training_ready"
            ]
        )

    def test_27_five_unresolved_blockers(self):
        self.assertEqual(
            self.health[
                "unresolved_blocker_count"
            ],
            5,
        )

        self.assertEqual(
            len(
                self.health[
                    "blockers"
                ]
            ),
            5,
        )

    def test_28_all_blockers_unresolved(self):
        self.assertTrue(
            all(
                blocker[
                    "resolved"
                ] is False
                for blocker
                in self.health[
                    "blockers"
                ]
            )
        )

    def test_29_features_not_labels(self):
        self.assertFalse(
            self.health[
                "feature_values_may_be_used_as_health_labels"
            ]
        )

    def test_30_features_not_predictions(self):
        self.assertFalse(
            self.health[
                "feature_values_may_be_used_as_health_predictions"
            ]
        )

    def test_31_no_health_label_control(self):
        self.assertFalse(
            self.health[
                "dashboard_controls"
            ][
                "create_health_label"
            ]
        )

    def test_32_no_training_authorization_control(self):
        self.assertFalse(
            self.health[
                "dashboard_controls"
            ][
                "authorize_training"
            ]
        )

    def test_33_no_blocker_override(self):
        self.assertFalse(
            self.health[
                "dashboard_controls"
            ][
                "override_blocker"
            ]
        )

    def test_34_HTML_receipt_registry(self):
        self.assertIn(
            'id="receipt-registry"',
            self.html,
        )

    def test_35_HTML_health_blocker_list(self):
        self.assertIn(
            'id="health-blocker-list"',
            self.html,
        )

    def test_36_HTML_explicit_unavailable_evidence(self):
        self.assertIn(
            "Real sensor runtime evidence",
            self.html,
        )

        self.assertIn(
            "Unavailable",
            self.html,
        )

    def test_37_JS_renders_receipts(self):
        self.assertIn(
            "renderReceiptRegistry",
            self.js,
        )

    def test_38_JS_renders_health_blockers(self):
        self.assertIn(
            "renderHealthBlockers",
            self.js,
        )

    def test_39_JS_no_innerHTML(self):
        self.assertNotIn(
            ".innerHTML",
            self.js,
        )

    def test_40_no_write_methods(self):
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

    def test_41_CSS_receipt_registry(self):
        self.assertIn(
            ".receipt-registry",
            self.css,
        )

        self.assertIn(
            ".receipt-card",
            self.css,
        )

    def test_42_CSS_health_workspace(self):
        self.assertIn(
            ".health-readiness-banner",
            self.css,
        )

        self.assertIn(
            ".health-blocker-list",
            self.css,
        )

    def test_43_javascript_syntax(self):
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


class DashboardUI5ServingTests(
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

    async def test_44_receipts_route_contract(self):
        self.assertIn(
            "GET /api/v1/receipts",
            route_contract(),
        )

    async def test_45_health_route_contract(self):
        self.assertIn(
            "GET /api/v1/health-supervision",
            route_contract(),
        )

    async def test_46_receipts_endpoint(self):
        response = await self.client.get(
            f"{API_PREFIX}/receipts"
        )

        self.assertEqual(
            response.status,
            200,
        )

        payload = await response.json()

        self.assertEqual(
            payload[
                "receipt_count"
            ],
            2,
        )

    async def test_47_health_endpoint(self):
        response = await self.client.get(
            f"{API_PREFIX}/health-supervision"
        )

        self.assertEqual(
            response.status,
            200,
        )

        payload = await response.json()

        self.assertFalse(
            payload[
                "training_ready"
            ]
        )

        self.assertEqual(
            payload[
                "real_health_label_count"
            ],
            0,
        )

    async def test_48_receipt_and_health_endpoints_read_only(self):
        receipt_response = await self.client.post(
            f"{API_PREFIX}/receipts",
            json={
                "write":
                    True,
            },
        )

        health_response = await self.client.post(
            f"{API_PREFIX}/health-supervision",
            json={
                "authorize_training":
                    True,
            },
        )

        self.assertEqual(
            receipt_response.status,
            405,
        )

        self.assertEqual(
            health_response.status,
            405,
        )


if __name__ == "__main__":
    unittest.main()
