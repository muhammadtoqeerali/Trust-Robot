from pathlib import Path
import ast
import json
import unittest


ROOT = Path(
    __file__
).resolve().parents[2]

APP = (
    ROOT
    / "app.py"
)

REQUIREMENTS = (
    ROOT
    / "requirements.txt"
)

SNAPSHOT = (
    ROOT
    / "deploy/vercel/dashboard_snapshot_v1.json"
)

CONTRACT = (
    ROOT
    / "configs/trust_robot/"
    "ui8_vercel_deployment_adapter_contract_v1.json"
)

JS = (
    ROOT
    / "src/trust_robot/dashboard_web/app.js"
)


class DashboardUI8VercelAdapterTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.app_text = APP.read_text(
            encoding="utf-8"
        )

        cls.requirements = REQUIREMENTS.read_text(
            encoding="utf-8"
        )

        cls.snapshot_text = SNAPSHOT.read_text(
            encoding="utf-8"
        )

        cls.snapshot = json.loads(
            cls.snapshot_text
        )

        cls.contract = json.loads(
            CONTRACT.read_text(
                encoding="utf-8"
            )
        )

        cls.js = JS.read_text(
            encoding="utf-8"
        )

    def test_01_contract_schema(self):
        self.assertEqual(
            self.contract[
                "schema"
            ],
            "TRUST_ROBOT_UI8_VERCEL_DEPLOYMENT_ADAPTER_CONTRACT_V1",
        )

    def test_02_platform_vercel(self):
        self.assertEqual(
            self.contract[
                "deployment"
            ][
                "platform"
            ],
            "vercel",
        )

    def test_03_entrypoint_app_py(self):
        self.assertEqual(
            self.contract[
                "deployment"
            ][
                "entrypoint"
            ],
            "app.py",
        )

    def test_04_framework_fastapi(self):
        self.assertEqual(
            self.contract[
                "api"
            ][
                "framework"
            ],
            "FastAPI",
        )

    def test_05_same_origin(self):
        self.assertTrue(
            self.contract[
                "api"
            ][
                "same_origin"
            ]
        )

    def test_06_no_write_routes(self):
        self.assertEqual(
            self.contract[
                "api"
            ][
                "write_routes"
            ],
            0,
        )

    def test_07_dataset_not_required_runtime(self):
        self.assertFalse(
            self.contract[
                "deployment"
            ][
                "local_dataset_required_at_runtime"
            ]
        )

    def test_08_git_not_required_runtime(self):
        self.assertFalse(
            self.contract[
                "deployment"
            ][
                "git_repository_required_at_runtime"
            ]
        )

    def test_09_sensor_network_not_required_runtime(self):
        self.assertFalse(
            self.contract[
                "deployment"
            ][
                "real_sensor_network_required_at_runtime"
            ]
        )

    def test_10_snapshot_read_only(self):
        self.assertTrue(
            self.snapshot[
                "read_only"
            ]
        )

    def test_11_snapshot_software_only(self):
        self.assertEqual(
            self.snapshot[
                "overview"
            ][
                "mode"
            ],
            "software_only",
        )

    def test_12_partition_counts(self):
        self.assertEqual(
            self.snapshot[
                "dataset"
            ][
                "counts"
            ],
            {
                "CONFIRMATION":
                    7,

                "TRAIN":
                    22,

                "VALIDATION":
                    7,
            },
        )

    def test_13_validation_closed(self):
        self.assertFalse(
            self.snapshot[
                "dataset"
            ][
                "validation_open"
            ]
        )

    def test_14_confirmation_closed(self):
        self.assertFalse(
            self.snapshot[
                "dataset"
            ][
                "confirmation_open"
            ]
        )

    def test_15_real_sensor_contact_false(self):
        self.assertFalse(
            self.snapshot[
                "operations"
            ][
                "real_sensor_contact"
            ]
        )

    def test_16_real_network_IO_false(self):
        self.assertFalse(
            self.snapshot[
                "operations"
            ][
                "real_network_IO_executed"
            ]
        )

    def test_17_real_session_count_zero(self):
        self.assertEqual(
            self.snapshot[
                "session_history"
            ][
                "real_sensor_session_count"
            ],
            0,
        )

    def test_18_SE4_incomplete(self):
        self.assertFalse(
            self.snapshot[
                "scientific_boundary"
            ][
                "SE4_complete"
            ]
        )

    def test_19_SE5_blocked(self):
        self.assertTrue(
            self.snapshot[
                "scientific_boundary"
            ][
                "SE5_entry_blocked"
            ]
        )

    def test_20_ATE_RPE_unavailable(self):
        self.assertFalse(
            self.snapshot[
                "scientific_boundary"
            ][
                "ATE_RPE_computed"
            ]
        )

    def test_21_snapshot_has_no_mnt_path(self):
        self.assertNotIn(
            "/mnt/",
            self.snapshot_text,
        )

    def test_22_snapshot_has_no_home_path(self):
        self.assertNotIn(
            "/home/",
            self.snapshot_text,
        )

    def test_23_snapshot_runtime_dataset_false(self):
        self.assertFalse(
            self.snapshot[
                "deployment"
            ][
                "dataset_required_at_runtime"
            ]
        )

    def test_24_snapshot_runtime_git_false(self):
        self.assertFalse(
            self.snapshot[
                "deployment"
            ][
                "git_repository_required_at_runtime"
            ]
        )

    def test_25_snapshot_runtime_sensor_false(self):
        self.assertFalse(
            self.snapshot[
                "deployment"
            ][
                "real_sensor_network_required"
            ]
        )

    def test_26_tree_unavailable_in_deployment_snapshot(self):
        self.assertIsNone(
            self.snapshot[
                "repository"
            ][
                "tree"
            ]
        )

    def test_27_worktree_unavailable_in_deployment_snapshot(self):
        self.assertIsNone(
            self.snapshot[
                "repository"
            ][
                "worktree_clean"
            ]
        )

    def test_28_fastapi_dependency(self):
        self.assertEqual(
            self.requirements.strip(),
            "fastapi>=0.141.1,<1.0.0",
        )

    def test_29_app_python_syntax(self):
        ast.parse(
            self.app_text,
            filename=str(
                APP
            ),
        )

    def test_30_app_exposes_fastapi_app(self):
        self.assertIn(
            "app = FastAPI(",
            self.app_text,
        )

    def test_31_docs_disabled(self):
        self.assertIn(
            "docs_url=None",
            self.app_text,
        )

        self.assertIn(
            "openapi_url=None",
            self.app_text,
        )

    def test_32_root_route_exists(self):
        self.assertIn(
            '@app.get(\n    "/",',
            self.app_text,
        )

    def test_33_snapshot_route_exists(self):
        self.assertIn(
            'f"{API_PREFIX}/snapshot"',
            self.app_text,
        )

    def test_34_events_route_exists(self):
        self.assertIn(
            'f"{API_PREFIX}/events"',
            self.app_text,
        )

    def test_35_static_mount_exists(self):
        self.assertIn(
            'app.mount(\n    "/assets"',
            self.app_text,
        )

        self.assertIn(
            "StaticFiles(",
            self.app_text,
        )

    def test_36_vercel_git_environment_overlay(self):
        self.assertIn(
            '"VERCEL_GIT_COMMIT_SHA"',
            self.app_text,
        )

        self.assertIn(
            '"VERCEL_GIT_COMMIT_REF"',
            self.app_text,
        )

    def test_37_no_aiohttp_in_vercel_entrypoint(self):
        self.assertNotIn(
            "aiohttp",
            self.app_text,
        )

    def test_38_transport_time_not_sensor_time(self):
        self.assertIn(
            '"transport_time_is_sensor_measurement_time":\n            False',
            self.app_text,
        )

    def test_39_frontend_handles_unavailable_tree(self):
        self.assertIn(
            'repository.tree ?? "Unavailable"',
            self.js,
        )

    def test_40_frontend_handles_unavailable_worktree(self):
        self.assertIn(
            'repository.worktree_clean === true',
            self.js,
        )

        self.assertIn(
            ': "Unavailable"',
            self.js,
        )


if __name__ == "__main__":
    unittest.main()
