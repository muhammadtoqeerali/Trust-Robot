from pathlib import Path
import json
import unittest


ROOT = Path(
    __file__
).resolve().parents[2]

VERCEL_JSON = (
    ROOT
    / "vercel.json"
)

CONTRACT = (
    ROOT
    / "configs/trust_robot/"
    "ui9_vercel_preview_qualification_contract_v1.json"
)

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


class DashboardUI9VercelPreviewTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ):
        cls.vercel = json.loads(
            VERCEL_JSON.read_text(
                encoding="utf-8"
            )
        )

        cls.contract = json.loads(
            CONTRACT.read_text(
                encoding="utf-8"
            )
        )

        cls.app_text = APP.read_text(
            encoding="utf-8"
        )

        cls.requirements = REQUIREMENTS.read_text(
            encoding="utf-8"
        )

        cls.snapshot = json.loads(
            SNAPSHOT.read_text(
                encoding="utf-8"
            )
        )

    def test_01_contract_schema(self):
        self.assertEqual(
            self.contract[
                "schema"
            ],
            "TRUST_ROBOT_UI9_VERCEL_PREVIEW_QUALIFICATION_CONTRACT_V1",
        )

    def test_02_vercel_schema(self):
        self.assertEqual(
            self.vercel[
                "$schema"
            ],
            "https://openapi.vercel.sh/vercel.json",
        )

    def test_03_framework_fastapi(self):
        self.assertEqual(
            self.vercel[
                "framework"
            ],
            "fastapi",
        )

    def test_04_build_command_cleared(self):
        self.assertIsNone(
            self.vercel[
                "buildCommand"
            ]
        )

    def test_05_dev_command_cleared(self):
        self.assertIsNone(
            self.vercel[
                "devCommand"
            ]
        )

    def test_06_install_command_cleared(self):
        self.assertIsNone(
            self.vercel[
                "installCommand"
            ]
        )

    def test_07_output_directory_cleared(self):
        self.assertIsNone(
            self.vercel[
                "outputDirectory"
            ]
        )

    def test_08_existing_project_only(self):
        self.assertFalse(
            self.contract[
                "deployment"
            ][
                "new_vercel_project_created"
            ]
        )

    def test_09_project_name(self):
        self.assertEqual(
            self.contract[
                "deployment"
            ][
                "existing_vercel_project"
            ],
            "trust-robot",
        )

    def test_10_preview_before_production(self):
        self.assertTrue(
            self.contract[
                "deployment"
            ][
                "preview_before_production"
            ]
        )

    def test_11_repository_root(self):
        self.assertTrue(
            self.contract[
                "deployment"
            ][
                "repository_root"
            ]
        )

    def test_12_previous_preset_other(self):
        self.assertEqual(
            self.contract[
                "failure_recovery"
            ][
                "previous_project_framework_preset"
            ],
            "other",
        )

    def test_13_framework_pin_required(self):
        self.assertTrue(
            self.contract[
                "failure_recovery"
            ][
                "source_controlled_framework_pin_required"
            ]
        )

    def test_14_app_exists(self):
        self.assertIn(
            "app = FastAPI(",
            self.app_text,
        )

    def test_15_fastapi_dependency(self):
        self.assertIn(
            "fastapi",
            self.requirements,
        )

    def test_16_snapshot_read_only(self):
        self.assertTrue(
            self.snapshot[
                "read_only"
            ]
        )

    def test_17_snapshot_software_only(self):
        self.assertEqual(
            self.snapshot[
                "overview"
            ][
                "mode"
            ],
            "software_only",
        )

    def test_18_dataset_not_runtime_required(self):
        self.assertFalse(
            self.contract[
                "runtime"
            ][
                "local_dataset_required"
            ]
        )

    def test_19_git_not_runtime_required(self):
        self.assertFalse(
            self.contract[
                "runtime"
            ][
                "git_repository_required"
            ]
        )

    def test_20_sensor_network_not_runtime_required(self):
        self.assertFalse(
            self.contract[
                "runtime"
            ][
                "real_sensor_network_required"
            ]
        )

    def test_21_server_state_not_writable(self):
        self.assertFalse(
            self.contract[
                "runtime"
            ][
                "server_writable_state"
            ]
        )

    def test_22_real_session_zero(self):
        self.assertEqual(
            self.contract[
                "scientific_boundary"
            ][
                "real_sensor_session_count"
            ],
            0,
        )

    def test_23_real_sensor_contact_false(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "real_sensor_contact"
            ]
        )

    def test_24_real_network_false(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "real_sensor_network_IO"
            ]
        )

    def test_25_health_labels_zero(self):
        self.assertEqual(
            self.contract[
                "scientific_boundary"
            ][
                "real_health_label_count"
            ],
            0,
        )

    def test_26_health_training_not_ready(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "health_training_ready"
            ]
        )

    def test_27_validation_closed(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "validation_open"
            ]
        )

    def test_28_confirmation_closed(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "confirmation_open"
            ]
        )

    def test_29_ATE_RPE_unavailable(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "ATE_RPE_available"
            ]
        )

    def test_30_SE4_incomplete(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "SE4_complete"
            ]
        )

    def test_31_SE5_blocked(self):
        self.assertFalse(
            self.contract[
                "scientific_boundary"
            ][
                "SE5_may_proceed"
            ]
        )

    def test_32_all_online_checks_required(self):
        self.assertTrue(
            all(
                self.contract[
                    "verification"
                ].values()
            )
        )


if __name__ == "__main__":
    unittest.main()
