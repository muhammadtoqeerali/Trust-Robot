from pathlib import Path
import ast
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
    "ui3_dashboard_data_views_contract_v1.json"
)


class DashboardUI3StateTests(
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
            "TRUST_ROBOT_UI3_DASHBOARD_DATA_VIEWS_CONTRACT_V1",
        )

    def test_02_replay_projection_exists(self):
        self.assertIn(
            "replay",
            self.snapshot,
        )

    def test_03_replay_is_TRAIN(self):
        self.assertEqual(
            self.snapshot[
                "replay"
            ][
                "split"
            ],
            "TRAIN",
        )

    def test_04_replay_trajectory(self):
        self.assertEqual(
            self.snapshot[
                "replay"
            ][
                "trajectory_id"
            ],
            "room_02",
        )

    def test_05_replay_bag_path(self):
        self.assertEqual(
            self.snapshot[
                "replay"
            ][
                "bag_relative_path"
            ],
            "raw/rosbags/room_02.bag",
        )

    def test_06_replay_bag_size(self):
        self.assertEqual(
            self.snapshot[
                "replay"
            ][
                "bag_file_size_bytes"
            ],
            15162620712,
        )

    def test_07_replay_message_count(self):
        self.assertEqual(
            self.snapshot[
                "replay"
            ][
                "bounded_replay_message_count"
            ],
            45,
        )

    def test_08_replay_digest(self):
        self.assertEqual(
            self.snapshot[
                "replay"
            ][
                "bounded_replay_digest_sha256"
            ],
            "68cda190573e34204567407a7783b7ba028696f9d21d10e72a149c7508e2904e",
        )

    def test_09_replay_deterministic(self):
        self.assertTrue(
            self.snapshot[
                "replay"
            ][
                "bounded_replay_deterministic"
            ]
        )

    def test_10_four_stream_ids(self):
        self.assertEqual(
            set(
                self.snapshot[
                    "replay"
                ][
                    "real_stream_ids"
                ]
            ),
            {
                "/camera/color/image_raw/compressed",
                "/camera/imu",
                "/handsfree/imu",
                "/velodyne_points",
            },
        )

    def test_11_reference_not_accessed(self):
        self.assertFalse(
            self.snapshot[
                "replay"
            ][
                "reference_trajectory_accessed"
            ]
        )

    def test_12_ATE_RPE_not_computed(self):
        self.assertFalse(
            self.snapshot[
                "replay"
            ][
                "ATE_RPE_computed"
            ]
        )

    def test_13_partition_trajectory_counts(self):
        trajectories = self.snapshot[
            "dataset"
        ][
            "trajectories"
        ]

        self.assertEqual(
            len(
                trajectories[
                    "TRAIN"
                ]
            ),
            22,
        )

        self.assertEqual(
            len(
                trajectories[
                    "VALIDATION"
                ]
            ),
            7,
        )

        self.assertEqual(
            len(
                trajectories[
                    "CONFIRMATION"
                ]
            ),
            7,
        )

    def test_14_room_02_in_TRAIN(self):
        self.assertIn(
            "room_02",
            self.snapshot[
                "dataset"
            ][
                "trajectories"
            ][
                "TRAIN"
            ],
        )

    def test_15_validation_closed(self):
        self.assertFalse(
            self.snapshot[
                "dataset"
            ][
                "validation_open"
            ]
        )

    def test_16_confirmation_closed(self):
        self.assertFalse(
            self.snapshot[
                "dataset"
            ][
                "confirmation_open"
            ]
        )

    def test_17_camera_timestamp_present(self):
        self.assertEqual(
            self.snapshot[
                "features"
            ][
                "camera"
            ][
                "bag_timestamp_ns"
            ],
            1627643739533299874,
        )

    def test_18_d435i_timestamp_present(self):
        self.assertEqual(
            self.snapshot[
                "features"
            ][
                "d435i_imu"
            ][
                "bag_timestamp_ns"
            ],
            1627643739482808635,
        )

    def test_19_handsfree_timestamp_present(self):
        self.assertEqual(
            self.snapshot[
                "features"
            ][
                "handsfree_imu"
            ][
                "bag_timestamp_ns"
            ],
            1627643739487759438,
        )

    def test_20_velodyne_timestamp_present(self):
        self.assertEqual(
            self.snapshot[
                "features"
            ][
                "velodyne"
            ][
                "bag_timestamp_ns"
            ],
            1627643739605994074,
        )

    def test_21_features_not_health_labels(self):
        self.assertFalse(
            self.snapshot[
                "features"
            ][
                "feature_values_are_health_labels"
            ]
        )

    def test_22_features_not_health_predictions(self):
        self.assertFalse(
            self.snapshot[
                "features"
            ][
                "feature_values_are_health_predictions"
            ]
        )

    def test_23_html_trajectory_browser(self):
        self.assertIn(
            'id="train-trajectory-list"',
            self.html,
        )

        self.assertIn(
            'id="validation-trajectory-list"',
            self.html,
        )

        self.assertIn(
            'id="confirmation-trajectory-list"',
            self.html,
        )

    def test_24_html_replay_stream_list(self):
        self.assertIn(
            'id="replay-stream-list"',
            self.html,
        )

    def test_25_html_repository_strip(self):
        for element_id in (
            "repo-branch",
            "repo-head",
            "repo-tree",
            "repo-clean",
        ):
            self.assertIn(
                f'id="{element_id}"',
                self.html,
            )

    def test_26_JS_renders_trajectory_lists(self):
        self.assertIn(
            "renderTrajectoryList",
            self.js,
        )

        self.assertIn(
            "dataset.trajectories.TRAIN",
            self.js,
        )

    def test_27_JS_renders_replay_streams(self):
        self.assertIn(
            "renderReplayStreams(replay.real_stream_ids)",
            self.js,
        )

    def test_28_JS_renders_bag_path(self):
        self.assertIn(
            'setText("replay-bag-path", replay.bag_relative_path)',
            self.js,
        )

    def test_29_JS_renders_repository_metadata(self):
        for element_id in (
            "repo-branch",
            "repo-head",
            "repo-tree",
            "repo-clean",
        ):
            self.assertIn(
                f'"{element_id}"',
                self.js,
            )

        self.assertIn(
            'repository.branch ?? "Unavailable"',
            self.js,
        )

        self.assertIn(
            'repository.head ?? "Unavailable"',
            self.js,
        )

        self.assertIn(
            'repository.tree ?? "Unavailable"',
            self.js,
        )

        self.assertIn(
            "repository.worktree_clean === true",
            self.js,
        )

        self.assertIn(
            "repository.worktree_clean === false",
            self.js,
        )

    def test_30_JS_no_innerHTML(self):
        self.assertNotIn(
            ".innerHTML",
            self.js,
        )

    def test_31_CSS_has_trajectory_chips(self):
        self.assertIn(
            ".trajectory-chip",
            self.css,
        )

    def test_32_CSS_has_replay_stream_items(self):
        self.assertIn(
            ".replay-stream-item",
            self.css,
        )

    def test_33_CSS_has_repository_strip(self):
        self.assertIn(
            ".repository-strip",
            self.css,
        )

    def test_34_no_write_controls(self):
        prohibited = (
            "Start Real Acquisition",
            "Create Health Label",
            "Open Validation",
            "Open Confirmation",
            "Run ATE",
        )

        for phrase in prohibited:
            self.assertNotIn(
                phrase,
                self.html,
            )

    def test_35_javascript_syntax(self):
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


class DashboardUI3ServingTests(
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

    async def test_36_replay_route_contract(self):
        self.assertIn(
            "GET /api/v1/replay",
            route_contract(),
        )

    async def test_37_replay_endpoint(self):
        response = await self.client.get(
            f"{API_PREFIX}/replay"
        )

        self.assertEqual(
            response.status,
            200,
        )

        payload = await response.json()

        self.assertEqual(
            payload[
                "trajectory_id"
            ],
            "room_02",
        )

    async def test_38_replay_endpoint_is_read_only(self):
        response = await self.client.post(
            f"{API_PREFIX}/replay",
            json={
                "trajectory_id":
                    "other",
            },
        )

        self.assertEqual(
            response.status,
            405,
        )

    async def test_39_snapshot_contains_replay(self):
        response = await self.client.get(
            f"{API_PREFIX}/snapshot"
        )

        payload = await response.json()

        self.assertIn(
            "replay",
            payload,
        )

    async def test_40_frontend_still_served(self):
        response = await self.client.get(
            "/"
        )

        self.assertEqual(
            response.status,
            200,
        )

        text = await response.text()

        self.assertIn(
            "Trajectory browser",
            text,
        )


if __name__ == "__main__":
    unittest.main()
