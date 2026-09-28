from hashlib import sha256
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
    route_contract,
)

from trust_robot.dashboard_state import (
    API_VERSION,
    DashboardStateError,
    FRONTEND_PROGRAM_ID,
    SNAPSHOT_SCHEMA,
    build_dashboard_snapshot,
    content_sha256,
    validate_dashboard_snapshot,
)


ROOT = Path(
    __file__
).resolve().parents[2]

CONTRACT = (
    ROOT
    / "configs/trust_robot/"
    "ui1_dashboard_read_only_api_contract_v1.json"
)

RUNNER = (
    ROOT
    / "scripts/trust_robot/"
    "run_ui1_dashboard_api_v1.py"
)


class DashboardStateTests(
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

        cls.contract = json.loads(
            CONTRACT.read_text(
                encoding="utf-8"
            )
        )

    def test_01_schema(self):
        self.assertEqual(
            self.snapshot[
                "schema"
            ],
            SNAPSHOT_SCHEMA,
        )

    def test_02_api_version(self):
        self.assertEqual(
            self.snapshot[
                "api_version"
            ],
            API_VERSION,
        )

    def test_03_program_id(self):
        self.assertEqual(
            self.snapshot[
                "frontend_program_id"
            ],
            FRONTEND_PROGRAM_ID,
        )

    def test_04_read_only(self):
        self.assertTrue(
            self.snapshot[
                "read_only"
            ]
        )

    def test_05_content_digest(self):
        self.assertEqual(
            self.snapshot[
                "content_sha256"
            ],
            content_sha256(
                self.snapshot
            ),
        )

    def test_06_software_qualification_passed(self):
        self.assertEqual(
            self.snapshot[
                "overview"
            ][
                "software_level_end_to_end_qualification"
            ],
            "passed",
        )

    def test_07_mode_software_only(self):
        self.assertEqual(
            self.snapshot[
                "overview"
            ][
                "mode"
            ],
            "software_only",
        )

    def test_08_representative_trajectory(self):
        self.assertEqual(
            self.snapshot[
                "overview"
            ][
                "representative_real_data_trajectory"
            ],
            "room_02",
        )

    def test_09_four_real_streams(self):
        self.assertEqual(
            self.snapshot[
                "overview"
            ][
                "real_stream_count"
            ],
            4,
        )

    def test_10_replay_count(self):
        self.assertEqual(
            self.snapshot[
                "overview"
            ][
                "bounded_replay_message_count"
            ],
            45,
        )

    def test_11_replay_digest(self):
        self.assertEqual(
            self.snapshot[
                "overview"
            ][
                "bounded_replay_digest_sha256"
            ],
            "68cda190573e34204567407a7783b7ba028696f9d21d10e72a149c7508e2904e",
        )

    def test_12_split_counts(self):
        self.assertEqual(
            self.snapshot[
                "dataset"
            ][
                "counts"
            ],
            {
                "TRAIN":
                    22,

                "VALIDATION":
                    7,

                "CONFIRMATION":
                    7,
            },
        )

    def test_13_validation_confirmation_closed(self):
        dataset = self.snapshot[
            "dataset"
        ]

        self.assertFalse(
            dataset[
                "validation_open"
            ]
        )

        self.assertFalse(
            dataset[
                "confirmation_open"
            ]
        )

    def test_14_features_are_real_train_evidence(self):
        self.assertEqual(
            self.snapshot[
                "features"
            ][
                "evidence_class"
            ],
            "real_M2DGR_TRAIN_software_evidence",
        )

    def test_15_features_are_not_labels(self):
        features = self.snapshot[
            "features"
        ]

        self.assertFalse(
            features[
                "feature_values_are_health_labels"
            ]
        )

        self.assertFalse(
            features[
                "feature_values_are_health_predictions"
            ]
        )

    def test_16_camera_feature_present(self):
        camera = self.snapshot[
            "features"
        ][
            "camera"
        ]

        self.assertEqual(
            camera[
                "feature_names"
            ],
            [
                "gray_mean_intensity_8bit",
                "gray_std_intensity_8bit",
                "gray_mean_abs_neighbor_difference_8bit",
            ],
        )

    def test_17_both_imu_feature_groups_present(self):
        features = self.snapshot[
            "features"
        ]

        self.assertEqual(
            features[
                "d435i_imu"
            ][
                "feature_names"
            ],
            [
                "angular_speed_norm_rad_s",
                "linear_acceleration_norm_m_s2",
            ],
        )

        self.assertEqual(
            features[
                "handsfree_imu"
            ][
                "feature_names"
            ],
            [
                "angular_speed_norm_rad_s",
                "linear_acceleration_norm_m_s2",
            ],
        )

    def test_18_velodyne_evidence_present(self):
        self.assertEqual(
            self.snapshot[
                "features"
            ][
                "velodyne"
            ][
                "serialized_payload_bytes"
            ],
            1121202,
        )

    def test_19_acquisition_is_not_executed(self):
        acquisition = self.snapshot[
            "acquisition"
        ]

        self.assertEqual(
            acquisition[
                "real_sensor_connection_state"
            ],
            "not_executed",
        )

        self.assertFalse(
            acquisition[
                "real_sensor_connected"
            ]
        )

    def test_20_synthetic_live_stack_qualified(self):
        synthetic = self.snapshot[
            "acquisition"
        ][
            "synthetic_live_stack"
        ]

        self.assertTrue(
            synthetic[
                "qualified"
            ]
        )

        self.assertEqual(
            synthetic[
                "execution_order"
            ],
            [
                "UDP",
                "HTTP:identity",
                "HTTP:status",
                "HTTP:diagnostic",
            ],
        )

        self.assertFalse(
            synthetic[
                "real_sensor_evidence"
            ]
        )

    def test_21_no_acquisition_controls(self):
        acquisition = self.snapshot[
            "acquisition"
        ]

        self.assertFalse(
            acquisition[
                "real_execution_controls_exposed"
            ]
        )

        self.assertFalse(
            acquisition[
                "sensor_configuration_controls_exposed"
            ]
        )

        self.assertFalse(
            acquisition[
                "authorization_controls_exposed"
            ]
        )

    def test_22_scientific_counts_zero(self):
        science = self.snapshot[
            "scientific_boundary"
        ]

        self.assertEqual(
            science[
                "real_runtime_binding_count"
            ],
            0,
        )

        self.assertEqual(
            science[
                "real_execution_authorization_count"
            ],
            0,
        )

        self.assertEqual(
            science[
                "grounded_authorization_record_count"
            ],
            0,
        )

        self.assertEqual(
            science[
                "accepted_health_supervision_source_count"
            ],
            0,
        )

        self.assertEqual(
            science[
                "real_health_label_count"
            ],
            0,
        )

    def test_23_SE4_SE5_blocked(self):
        science = self.snapshot[
            "scientific_boundary"
        ]

        self.assertFalse(
            science[
                "SE4_complete"
            ]
        )

        self.assertTrue(
            science[
                "SE4_training_execution_blocked"
            ]
        )

        self.assertTrue(
            science[
                "SE5_entry_blocked"
            ]
        )

    def test_24_no_scientific_override(self):
        self.assertFalse(
            self.snapshot[
                "scientific_boundary"
            ][
                "dashboard_may_override_boundary"
            ]
        )

    def test_25_legacy_dashboard_boundary_preserved(self):
        frozen = self.snapshot[
            "dashboard_policy"
        ][
            "frozen_legacy_boundary"
        ]

        self.assertTrue(
            frozen[
                "dashboard_may_display_only_real_or_explicitly_unavailable_values"
            ]
        )

        self.assertFalse(
            frozen[
                "dashboard_may_modify_frozen_thresholds_or_calibration"
            ]
        )

        self.assertFalse(
            frozen[
                "dashboard_may_select_scientific_parameters"
            ]
        )

    def test_26_current_scope_does_not_claim_live_runtime(self):
        scope = self.snapshot[
            "dashboard_policy"
        ][
            "current_UI_program_scope"
        ]

        self.assertTrue(
            scope[
                "software_only_evidence_shell"
            ]
        )

        self.assertFalse(
            scope[
                "live_runtime_activation"
            ]
        )

        self.assertFalse(
            scope[
                "claims_real_runtime_dashboard"
            ]
        )

    def test_27_all_source_paths_relative(self):
        for record in self.snapshot[
            "evidence"
        ][
            "sources"
        ]:
            self.assertFalse(
                Path(
                    record[
                        "path"
                    ]
                ).is_absolute()
            )

    def test_28_no_runtime_sensor_evidence(self):
        evidence = self.snapshot[
            "evidence"
        ]

        self.assertFalse(
            evidence[
                "runtime_sensor_evidence_available"
            ]
        )

        self.assertFalse(
            evidence[
                "accepted_health_supervision_available"
            ]
        )

    def test_29_prohibited_capabilities_false(self):
        capabilities = self.snapshot[
            "capabilities"
        ]

        for name in (
            "execute_real_sensor_acquisition",
            "create_execution_authorization",
            "create_health_labels",
            "open_validation",
            "open_confirmation",
            "run_ATE_RPE",
            "modify_scientific_parameters",
        ):
            self.assertFalse(
                capabilities[
                    name
                ]
            )

    def test_30_contract_schema(self):
        self.assertEqual(
            self.contract[
                "schema"
            ],
            "TRUST_ROBOT_UI1_DASHBOARD_READ_ONLY_API_CONTRACT_V1",
        )

    def test_31_contract_is_read_only(self):
        self.assertTrue(
            self.contract[
                "api"
            ][
                "read_only"
            ]
        )

    def test_32_contract_loopback_only(self):
        network = self.contract[
            "network_policy"
        ]

        self.assertEqual(
            network[
                "UI1_default_bind_host"
            ],
            "127.0.0.1",
        )

        self.assertFalse(
            network[
                "UI1_non_loopback_bind_allowed"
            ]
        )

        self.assertFalse(
            network[
                "real_sensor_network_IO_allowed"
            ]
        )

    def test_33_runner_rejects_non_loopback(self):
        result = subprocess.run(
            [
                sys.executable,
                str(
                    RUNNER
                ),
                "--repo-root",
                str(
                    ROOT
                ),
                "--host",
                "0.0.0.0",
                "--port",
                "8765",
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertNotEqual(
            result.returncode,
            0,
        )

        self.assertIn(
            "loopback-only",
            result.stderr,
        )

    def test_34_route_contract_exact(self):
        self.assertEqual(
            route_contract(),
            (
                "GET /api/v1/health",
                "GET /api/v1/snapshot",
                "GET /api/v1/overview",
                "GET /api/v1/repository",
                "GET /api/v1/dataset",
                "GET /api/v1/replay",
                "GET /api/v1/features",
                "GET /api/v1/acquisition",
                "GET /api/v1/operations",
                "GET /api/v1/receipts",
                "GET /api/v1/health-supervision",
                "GET /api/v1/scientific-boundary",
                "GET /api/v1/dashboard-policy",
                "GET /api/v1/evidence",
                "GET /api/v1/capabilities",
            ),
        )

    def test_35_runner_has_no_sensor_execution_switch(self):
        tree = ast.parse(
            RUNNER.read_text(
                encoding="utf-8"
            ),
            filename=str(
                RUNNER
            ),
        )

        text = RUNNER.read_text(
            encoding="utf-8"
        )

        self.assertNotIn(
            "--execute-real",
            text,
        )

        self.assertNotIn(
            "execute_real_session_from_files",
            text,
        )

        self.assertIsInstance(
            tree,
            ast.Module,
        )


    def test_46_frozen_split_vocabulary_projection(self):
        split_path = (
            ROOT
            / "manifests/"
            "m2dgr_trajectory_manifest_v1_split_freeze_v1.json"
        )

        payload = json.loads(
            split_path.read_text(
                encoding="utf-8"
            )
        )

        counts = {}

        for record in payload[
            "records"
        ]:
            split = record[
                "split"
            ]

            counts[
                split
            ] = (
                counts.get(
                    split,
                    0,
                )
                + 1
            )

        self.assertEqual(
            counts,
            {
                "train":
                    22,

                "validation_calibration":
                    7,

                "confirmation_test":
                    7,
            },
        )

        self.assertEqual(
            self.snapshot[
                "dataset"
            ][
                "counts"
            ],
            {
                "TRAIN":
                    22,

                "VALIDATION":
                    7,

                "CONFIRMATION":
                    7,
            },
        )

        self.assertFalse(
            self.snapshot[
                "dataset"
            ][
                "validation_open"
            ]
        )

        self.assertFalse(
            self.snapshot[
                "dataset"
            ][
                "confirmation_open"
            ]
        )


class DashboardAPITests(
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

    async def test_36_health_endpoint(self):
        response = await self.client.get(
            f"{API_PREFIX}/health"
        )

        self.assertEqual(
            response.status,
            200,
        )

        payload = await response.json()

        self.assertEqual(
            payload[
                "status"
            ],
            "ok",
        )

        self.assertTrue(
            payload[
                "read_only"
            ]
        )

        self.assertFalse(
            payload[
                "real_sensor_execution_available"
            ]
        )

    async def test_37_snapshot_endpoint(self):
        response = await self.client.get(
            f"{API_PREFIX}/snapshot"
        )

        self.assertEqual(
            response.status,
            200,
        )

        payload = await response.json()

        self.assertEqual(
            payload[
                "schema"
            ],
            SNAPSHOT_SCHEMA,
        )

    async def test_38_overview_endpoint(self):
        response = await self.client.get(
            f"{API_PREFIX}/overview"
        )

        self.assertEqual(
            response.status,
            200,
        )

        payload = await response.json()

        self.assertEqual(
            payload[
                "system_name"
            ],
            "TRUST-ROBOT",
        )

    async def test_39_dataset_endpoint(self):
        response = await self.client.get(
            f"{API_PREFIX}/dataset"
        )

        payload = await response.json()

        self.assertEqual(
            payload[
                "counts"
            ][
                "TRAIN"
            ],
            22,
        )

    async def test_40_features_endpoint(self):
        response = await self.client.get(
            f"{API_PREFIX}/features"
        )

        payload = await response.json()

        self.assertIn(
            "camera",
            payload,
        )

        self.assertIn(
            "d435i_imu",
            payload,
        )

        self.assertIn(
            "handsfree_imu",
            payload,
        )

        self.assertIn(
            "velodyne",
            payload,
        )

    async def test_41_acquisition_endpoint_fail_closed(self):
        response = await self.client.get(
            f"{API_PREFIX}/acquisition"
        )

        payload = await response.json()

        self.assertFalse(
            payload[
                "real_sensor_connected"
            ]
        )

        self.assertFalse(
            payload[
                "real_execution_controls_exposed"
            ]
        )

    async def test_42_scientific_boundary_endpoint(self):
        response = await self.client.get(
            f"{API_PREFIX}/scientific-boundary"
        )

        payload = await response.json()

        self.assertFalse(
            payload[
                "SE4_complete"
            ]
        )

        self.assertTrue(
            payload[
                "SE5_entry_blocked"
            ]
        )

    async def test_43_evidence_endpoint(self):
        response = await self.client.get(
            f"{API_PREFIX}/evidence"
        )

        payload = await response.json()

        self.assertTrue(
            payload[
                "all_values_traceable_to_repository_evidence"
            ]
        )

    async def test_44_post_snapshot_not_available(self):
        response = await self.client.post(
            f"{API_PREFIX}/snapshot",
            json={
                "attempt":
                    "write"
            },
        )

        self.assertEqual(
            response.status,
            405,
        )

    async def test_45_no_store_header(self):
        response = await self.client.get(
            f"{API_PREFIX}/overview"
        )

        self.assertEqual(
            response.headers[
                "Cache-Control"
            ],
            "no-store, max-age=0",
        )

        self.assertEqual(
            response.headers[
                "X-Trust-Robot-Dashboard-Mode"
            ],
            "read-only",
        )


if __name__ == "__main__":
    unittest.main()
