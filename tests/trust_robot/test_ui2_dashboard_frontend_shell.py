from pathlib import Path
import ast
import json
import subprocess
import sys
import unittest

from aiohttp.test_utils import (
    TestClient,
    TestServer,
)

from trust_robot.dashboard_api import (
    API_PREFIX,
    create_dashboard_app,
    frontend_route_contract,
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

API = (
    ROOT
    / "src/trust_robot/dashboard_api.py"
)

CONTRACT = (
    ROOT
    / "configs/trust_robot/"
    "ui2_dashboard_frontend_shell_contract_v1.json"
)


class DashboardFrontendArtifactTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.html = INDEX.read_text(
            encoding="utf-8"
        )

        cls.css = CSS.read_text(
            encoding="utf-8"
        )

        cls.js = JS.read_text(
            encoding="utf-8"
        )

        cls.api = API.read_text(
            encoding="utf-8"
        )

        cls.contract = json.loads(
            CONTRACT.read_text(
                encoding="utf-8"
            )
        )

    def test_01_contract_schema(self):
        self.assertEqual(
            self.contract[
                "schema"
            ],
            "TRUST_ROBOT_UI2_DASHBOARD_FRONTEND_SHELL_CONTRACT_V1",
        )

    def test_02_no_external_CDNs(self):
        self.assertFalse(
            self.contract[
                "architecture"
            ][
                "external_CDNs"
            ]
        )

        self.assertNotIn(
            "https://",
            self.html,
        )

        self.assertNotIn(
            "http://",
            self.html,
        )

    def test_03_same_origin_API(self):
        self.assertIn(
            '"/api/v1/snapshot"',
            self.js,
        )

        self.assertNotIn(
            "fetch(\"http",
            self.js,
        )

    def test_04_html_language_and_viewport(self):
        self.assertIn(
            '<html lang="en">',
            self.html,
        )

        self.assertIn(
            'name="viewport"',
            self.html,
        )

    def test_05_skip_link(self):
        self.assertIn(
            'class="skip-link"',
            self.html,
        )

        self.assertIn(
            'href="#main-content"',
            self.html,
        )

    def test_06_semantic_navigation(self):
        self.assertIn(
            '<nav class="nav-list"',
            self.html,
        )

        for view in (
            "overview",
            "dataset",
            "features",
            "operations",
            "evidence",
            "health",
        ):
            self.assertIn(
                f'data-view="{view}"',
                self.html,
            )

    def test_07_all_view_panels_exist(self):
        for view in (
            "overview",
            "dataset",
            "features",
            "operations",
            "evidence",
            "health",
        ):
            self.assertIn(
                f'data-panel="{view}"',
                self.html,
            )

    def test_08_synthetic_state_labeled(self):
        self.assertIn(
            'badge--synthetic',
            self.html,
        )

        self.assertIn(
            "Synthetic",
            self.html,
        )

    def test_09_no_real_execution_control_text(self):
        prohibited = (
            "Execute Real",
            "Start Real Acquisition",
            "Authorize Real Sensor",
            "Create Health Label",
        )

        for phrase in prohibited:
            self.assertNotIn(
                phrase,
                self.html,
            )

    def test_10_no_forms(self):
        self.assertNotIn(
            "<form",
            self.html.lower(),
        )

    def test_11_reduced_motion_support(self):
        self.assertIn(
            "@media (prefers-reduced-motion: reduce)",
            self.css,
        )

    def test_12_medium_breakpoint(self):
        self.assertIn(
            "@media (max-width: 1100px)",
            self.css,
        )

    def test_13_compact_breakpoint(self):
        self.assertIn(
            "@media (max-width: 760px)",
            self.css,
        )

    def test_14_mobile_navigation(self):
        self.assertIn(
            "mobile-menu-button",
            self.html,
        )

        self.assertIn(
            "nav-open",
            self.js,
        )

    def test_15_API_failure_has_no_fabricated_fallback(self):
        self.assertIn(
            "No fallback scientific values were invented.",
            self.js,
        )

    def test_16_fetch_is_GET_only(self):
        self.assertIn(
            'method: "GET"',
            self.js,
        )

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

    def test_17_read_only_API_assertion(self):
        self.assertIn(
            "snapshot.read_only !== true",
            self.js,
        )

    def test_18_safe_DOM_rendering(self):
        self.assertNotIn(
            ".innerHTML",
            self.js,
        )

        self.assertIn(
            ".textContent",
            self.js,
        )

    def test_19_javascript_syntax(self):
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

    def test_20_AppKey_migration(self):
        self.assertIn(
            "web.AppKey(",
            self.api,
        )

        self.assertNotIn(
            'app[\n        "repo_root"\n    ]',
            self.api,
        )


class DashboardFrontendServingTests(
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

    async def test_21_frontend_route_contract(self):
        self.assertEqual(
            frontend_route_contract(),
            (
                "GET /",
                "GET /assets/styles.css",
                "GET /assets/app.js",
            ),
        )

    async def test_22_index_served(self):
        response = await self.client.get(
            "/"
        )

        self.assertEqual(
            response.status,
            200,
        )

        text = await response.text()

        self.assertIn(
            "TRUST-ROBOT Operations",
            text,
        )

    async def test_23_index_content_type(self):
        response = await self.client.get(
            "/"
        )

        self.assertTrue(
            response.headers[
                "Content-Type"
            ].startswith(
                "text/html"
            )
        )

    async def test_24_styles_served(self):
        response = await self.client.get(
            "/assets/styles.css"
        )

        self.assertEqual(
            response.status,
            200,
        )

        self.assertTrue(
            response.headers[
                "Content-Type"
            ].startswith(
                "text/css"
            )
        )

    async def test_25_javascript_served(self):
        response = await self.client.get(
            "/assets/app.js"
        )

        self.assertEqual(
            response.status,
            200,
        )

        content_type = response.headers[
            "Content-Type"
        ]

        self.assertTrue(
            "javascript"
            in content_type
        )

    async def test_26_security_no_store(self):
        response = await self.client.get(
            "/"
        )

        self.assertEqual(
            response.headers[
                "Cache-Control"
            ],
            "no-store, max-age=0",
        )

    async def test_27_security_content_type_options(self):
        response = await self.client.get(
            "/"
        )

        self.assertEqual(
            response.headers[
                "X-Content-Type-Options"
            ],
            "nosniff",
        )

    async def test_28_security_frame_options(self):
        response = await self.client.get(
            "/"
        )

        self.assertEqual(
            response.headers[
                "X-Frame-Options"
            ],
            "DENY",
        )

    async def test_29_security_CSP(self):
        response = await self.client.get(
            "/"
        )

        csp = response.headers[
            "Content-Security-Policy"
        ]

        self.assertIn(
            "default-src 'self'",
            csp,
        )

        self.assertIn(
            "connect-src 'self'",
            csp,
        )

        self.assertIn(
            "form-action 'none'",
            csp,
        )

    async def test_30_API_still_served(self):
        response = await self.client.get(
            f"{API_PREFIX}/snapshot"
        )

        self.assertEqual(
            response.status,
            200,
        )

        payload = await response.json()

        self.assertTrue(
            payload[
                "read_only"
            ]
        )

    async def test_31_API_post_still_blocked(self):
        response = await self.client.post(
            f"{API_PREFIX}/snapshot",
            json={
                "write":
                    True,
            },
        )

        self.assertEqual(
            response.status,
            405,
        )

    async def test_32_missing_asset_404(self):
        response = await self.client.get(
            "/assets/not-a-real-dashboard-file.js"
        )

        self.assertEqual(
            response.status,
            404,
        )


if __name__ == "__main__":
    unittest.main()
