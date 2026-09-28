from pathlib import Path
import json
import subprocess
import unittest


ROOT = Path(
    __file__
).resolve().parents[2]

CONTRACT = (
    ROOT
    / "configs/trust_robot/"
    "ui7_browser_qualification_contract_v1.json"
)

RUNNER = (
    ROOT
    / "scripts/trust_robot/"
    "run_ui7_dashboard_browser_qualification_v1.cjs"
)

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


class DashboardUI7BrowserQualificationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.contract = json.loads(
            CONTRACT.read_text(
                encoding="utf-8"
            )
        )

        cls.runner = RUNNER.read_text(
            encoding="utf-8"
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
            "TRUST_ROBOT_UI7_BROWSER_QUALIFICATION_CONTRACT_V1",
        )

    def test_02_browser_dependency_external(self):
        self.assertFalse(
            self.contract[
                "browser_runtime"
            ][
                "repository_dependency_added"
            ]
        )

    def test_03_browser_tool_playwright(self):
        self.assertEqual(
            self.contract[
                "browser_runtime"
            ][
                "tool"
            ],
            "Playwright Chromium",
        )

    def test_04_six_views(self):
        self.assertEqual(
            self.contract[
                "views"
            ],
            [
                "overview",
                "dataset",
                "features",
                "operations",
                "evidence",
                "health",
            ],
        )

    def test_05_desktop_viewport(self):
        self.assertEqual(
            self.contract[
                "desktop"
            ][
                "width"
            ],
            1440,
        )

        self.assertEqual(
            self.contract[
                "desktop"
            ][
                "height"
            ],
            900,
        )

    def test_06_mobile_viewport(self):
        self.assertEqual(
            self.contract[
                "mobile"
            ][
                "width"
            ],
            390,
        )

        self.assertEqual(
            self.contract[
                "mobile"
            ][
                "height"
            ],
            844,
        )

    def test_07_desktop_overflow_forbidden(self):
        self.assertFalse(
            self.contract[
                "desktop"
            ][
                "horizontal_page_overflow_allowed"
            ]
        )

    def test_08_mobile_overflow_forbidden(self):
        self.assertFalse(
            self.contract[
                "mobile"
            ][
                "horizontal_page_overflow_allowed"
            ]
        )

    def test_09_manual_refresh_required(self):
        self.assertTrue(
            self.contract[
                "live_behavior"
            ][
                "manual_refresh_qualified"
            ]
        )

    def test_10_SSE_required(self):
        self.assertTrue(
            self.contract[
                "live_behavior"
            ][
                "SSE_request_qualified"
            ]
        )

    def test_11_transport_time_not_sensor_time(self):
        self.assertFalse(
            self.contract[
                "live_behavior"
            ][
                "transport_timestamp_may_be_sensor_measurement_time"
            ]
        )

    def test_12_no_fallback_values(self):
        self.assertFalse(
            self.contract[
                "error_behavior"
            ][
                "fabricated_fallback_values_allowed"
            ]
        )

    def test_13_snapshot_failure_visible(self):
        self.assertTrue(
            self.contract[
                "error_behavior"
            ][
                "snapshot_failure_visible"
            ]
        )

    def test_14_security_CSP(self):
        self.assertTrue(
            self.contract[
                "security"
            ][
                "content_security_policy_required"
            ]
        )

    def test_15_security_no_store(self):
        self.assertTrue(
            self.contract[
                "security"
            ][
                "no_store_required"
            ]
        )

    def test_16_security_nosniff(self):
        self.assertTrue(
            self.contract[
                "security"
            ][
                "nosniff_required"
            ]
        )

    def test_17_security_frame_denial(self):
        self.assertTrue(
            self.contract[
                "security"
            ][
                "frame_denial_required"
            ]
        )

    def test_18_validation_closed(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "validation_open"
            ]
        )

    def test_19_confirmation_closed(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "confirmation_open"
            ]
        )

    def test_20_ATE_RPE_unavailable(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "ATE_RPE_available"
            ]
        )

    def test_21_real_sensor_contact_false(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "real_sensor_contact"
            ]
        )

    def test_22_real_session_count_zero(self):
        self.assertEqual(
            self.contract[
                "scientific_boundary"
            ][
                "real_sensor_session_count"
            ],
            0,
        )

    def test_23_SE4_incomplete(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "SE4_complete"
            ]
        )

    def test_24_SE5_blocked(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "SE5_may_proceed"
            ]
        )

    def test_25_skip_link_present(self):
        self.assertIn(
            'class="skip-link"',
            self.html,
        )

    def test_26_mobile_menu_present(self):
        self.assertIn(
            'id="mobile-menu-button"',
            self.html,
        )

    def test_27_refresh_button_present(self):
        self.assertIn(
            'id="refresh-button"',
            self.html,
        )

    def test_28_live_update_present(self):
        self.assertIn(
            'id="live-update-chip"',
            self.html,
        )

        self.assertIn(
            "new EventSource(",
            self.js,
        )

    def test_29_fail_closed_alert_copy(self):
        self.assertIn(
            "No fallback scientific values were invented.",
            self.js,
        )

    def test_30_responsive_breakpoints(self):
        self.assertIn(
            "@media (max-width: 1100px)",
            self.css,
        )

        self.assertIn(
            "@media (max-width: 760px)",
            self.css,
        )

    def test_31_browser_runner_syntax(self):
        result = subprocess.run(
            [
                "node",
                "--check",
                str(
                    RUNNER
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

    def test_32_browser_runner_has_error_interception(self):
        self.assertIn(
            '"**/api/v1/snapshot"',
            self.runner,
        )

        self.assertIn(
            '"**/api/v1/events"',
            self.runner,
        )


if __name__ == "__main__":
    unittest.main()
