from pathlib import Path
from tempfile import TemporaryDirectory
import ast
import json
import unittest

import numpy as np

from trust_robot.corruption import (
    CorruptionError,
    CorruptionFamily,
    CorruptionSpec,
    EventStream,
    ScenarioContext,
    SensorModality,
    apply_corruption,
    build_pair_manifest,
    inject_event_gap,
    inject_event_repeat,
    inject_timestamp_step_shift,
    manifest_json,
    write_immutable_manifest,
)


ROOT = Path(__file__).resolve().parents[2]

MODULE = (
    ROOT
    / "src/trust_robot/corruption.py"
)

CONFIG = (
    ROOT
    / "configs/trust_robot/"
      "phase3_corruption_taxonomy_candidate_v1.json"
)


def make_stream(
    *,
    modality=SensorModality.LIDAR,
    source_id="/velodyne_points",
):
    payloads = (
        np.asarray(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
            ],
            dtype=np.float64,
        ),
        np.asarray(
            [
                [0.1, 0.0, 0.0],
                [1.1, 0.0, 0.0],
            ],
            dtype=np.float64,
        ),
        np.asarray(
            [
                [0.2, 0.0, 0.0],
                [1.2, 0.0, 0.0],
            ],
            dtype=np.float64,
        ),
        np.asarray(
            [
                [0.3, 0.0, 0.0],
                [1.3, 0.0, 0.0],
            ],
            dtype=np.float64,
        ),
        np.asarray(
            [
                [0.4, 0.0, 0.0],
                [1.4, 0.0, 0.0],
            ],
            dtype=np.float64,
        ),
    )

    return EventStream(
        modality=
            modality,

        source_id=
            source_id,

        timestamps_ns=
            np.asarray(
                [
                    100,
                    200,
                    300,
                    400,
                    500,
                ],
                dtype=np.int64,
            ),

        payloads=
            payloads,

        metadata={
            "adapter":
                "synthetic_test_fixture",
        },
    )


class Phase3CorruptionKernelTests(
    unittest.TestCase
):
    def test_01_taxonomy_enums_are_explicit(self):
        self.assertEqual(
            CorruptionFamily.EVENT_GAP.value,
            "EVENT_GAP",
        )

        self.assertEqual(
            SensorModality.LIDAR.value,
            "lidar",
        )

        self.assertEqual(
            ScenarioContext.ATTACK.value,
            "attack",
        )

    def test_02_stream_copies_and_freezes_arrays(self):
        timestamps = np.asarray(
            [
                1,
                2,
            ],
            dtype=np.int64,
        )

        payload = np.asarray(
            [
                1.0,
                2.0,
            ]
        )

        stream = EventStream(
            modality="imu",
            source_id="imu",
            timestamps_ns=timestamps,
            payloads=(
                payload,
                payload + 1.0,
            ),
        )

        timestamps[
            0
        ] = 99

        payload[
            0
        ] = 99.0

        self.assertEqual(
            int(
                stream.timestamps_ns[
                    0
                ]
            ),
            1,
        )

        self.assertEqual(
            float(
                stream.payloads[
                    0
                ][
                    0
                ]
            ),
            1.0,
        )

        self.assertFalse(
            stream.timestamps_ns.flags.writeable
        )

        self.assertFalse(
            stream.payloads[
                0
            ].flags.writeable
        )

    def test_03_object_dtype_payload_is_rejected(self):
        with self.assertRaises(
            CorruptionError
        ):
            EventStream(
                modality="other",
                source_id="bad",
                timestamps_ns=np.asarray(
                    [
                        1,
                    ],
                    dtype=np.int64,
                ),
                payloads=(
                    np.asarray(
                        [
                            object(),
                        ],
                        dtype=object,
                    ),
                ),
            )

    def test_04_stream_fingerprint_is_deterministic(self):
        first = make_stream()
        second = make_stream()

        self.assertEqual(
            first.fingerprint(),
            second.fingerprint(),
        )

    def test_05_stream_identity_changes_fingerprint(self):
        first = make_stream()
        second = make_stream(
            source_id="/another_source"
        )

        self.assertNotEqual(
            first.fingerprint(),
            second.fingerprint(),
        )

    def test_06_spec_id_is_parameter_order_independent(self):
        first = CorruptionSpec(
            family=
                CorruptionFamily.TIMESTAMP_STEP_SHIFT,

            modality=
                SensorModality.LIDAR,

            start_index=
                2,

            length=
                1,

            parameters={
                "offset_ns":
                    10,
            },
        )

        second = CorruptionSpec(
            family="TIMESTAMP_STEP_SHIFT",
            modality="lidar",
            start_index=2,
            length=1,
            parameters=dict(
                reversed(
                    list(
                        {
                            "offset_ns":
                                10,
                        }.items()
                    )
                )
            ),
        )

        self.assertEqual(
            first.spec_id,
            second.spec_id,
        )

    def test_07_attack_requires_explicit_threat_model(self):
        with self.assertRaises(
            CorruptionError
        ):
            CorruptionSpec(
                family="EVENT_GAP",
                modality="lidar",
                start_index=1,
                length=1,
                scenario_context="attack",
            )

    def test_08_nonattack_cannot_silently_carry_threat_model(self):
        with self.assertRaises(
            CorruptionError
        ):
            CorruptionSpec(
                family="EVENT_GAP",
                modality="lidar",
                start_index=1,
                length=1,
                scenario_context="fault",
                threat_model_id="unexpected",
            )

    def test_09_severity_is_optional_and_not_selected_by_kernel(self):
        spec = CorruptionSpec(
            family="EVENT_GAP",
            modality="lidar",
            start_index=1,
            length=1,
        )

        self.assertIsNone(
            spec.severity_id
        )

    def test_10_event_gap_preserves_clean_origin_mapping(self):
        clean = make_stream()

        pair = inject_event_gap(
            clean,
            CorruptionSpec(
                family="EVENT_GAP",
                modality="lidar",
                start_index=2,
                length=1,
            ),
        )

        self.assertEqual(
            clean.n_events,
            5,
        )

        self.assertEqual(
            pair.corrupt.n_events,
            4,
        )

        np.testing.assert_array_equal(
            pair.corrupt.origin_indices,
            np.asarray(
                [
                    0,
                    1,
                    3,
                    4,
                ]
            ),
        )

    def test_11_event_gap_does_not_mutate_clean(self):
        clean = make_stream()

        original = clean.fingerprint()

        apply_corruption(
            clean,
            CorruptionSpec(
                family="EVENT_GAP",
                modality="lidar",
                start_index=2,
                length=1,
            ),
        )

        self.assertEqual(
            clean.fingerprint(),
            original,
        )

    def test_12_event_gap_requires_pre_gap_boundary(self):
        with self.assertRaises(
            CorruptionError
        ):
            apply_corruption(
                make_stream(),
                CorruptionSpec(
                    family="EVENT_GAP",
                    modality="lidar",
                    start_index=0,
                    length=1,
                ),
            )

    def test_13_event_gap_requires_post_gap_boundary(self):
        with self.assertRaises(
            CorruptionError
        ):
            apply_corruption(
                make_stream(),
                CorruptionSpec(
                    family="EVENT_GAP",
                    modality="lidar",
                    start_index=4,
                    length=1,
                ),
            )

    def test_14_event_repeat_preserves_metadata_progression(self):
        clean = make_stream()

        pair = inject_event_repeat(
            clean,
            CorruptionSpec(
                family="EVENT_REPEAT",
                modality="lidar",
                start_index=2,
                length=2,
            ),
        )

        self.assertEqual(
            pair.corrupt.n_events,
            clean.n_events,
        )

        np.testing.assert_array_equal(
            pair.corrupt.timestamps_ns,
            clean.timestamps_ns,
        )

        np.testing.assert_array_equal(
            pair.corrupt.origin_indices,
            clean.origin_indices,
        )

        np.testing.assert_array_equal(
            pair.corrupt.payloads[
                2
            ],
            clean.payloads[
                1
            ],
        )

        np.testing.assert_array_equal(
            pair.corrupt.payloads[
                3
            ],
            clean.payloads[
                1
            ],
        )

    def test_15_event_repeat_rejects_noop(self):
        clean = EventStream(
            modality="imu",
            source_id="imu",
            timestamps_ns=np.asarray(
                [
                    1,
                    2,
                    3,
                ],
                dtype=np.int64,
            ),
            payloads=(
                np.asarray(
                    [
                        1.0,
                    ]
                ),
                np.asarray(
                    [
                        1.0,
                    ]
                ),
                np.asarray(
                    [
                        2.0,
                    ]
                ),
            ),
        )

        with self.assertRaises(
            CorruptionError
        ):
            apply_corruption(
                clean,
                CorruptionSpec(
                    family="EVENT_REPEAT",
                    modality="imu",
                    start_index=1,
                    length=1,
                ),
            )

    def test_16_timestamp_step_shift_is_explicit(self):
        clean = make_stream()

        pair = inject_timestamp_step_shift(
            clean,
            CorruptionSpec(
                family="TIMESTAMP_STEP_SHIFT",
                modality="lidar",
                start_index=2,
                length=1,
                parameters={
                    "offset_ns":
                        25,
                },
            ),
        )

        np.testing.assert_array_equal(
            pair.corrupt.timestamps_ns,
            np.asarray(
                [
                    100,
                    200,
                    325,
                    425,
                    525,
                ],
                dtype=np.int64,
            ),
        )

        for clean_payload, corrupt_payload in zip(
            clean.payloads,
            pair.corrupt.payloads,
            strict=True,
        ):
            np.testing.assert_array_equal(
                clean_payload,
                corrupt_payload,
            )

    def test_17_timestamp_zero_shift_is_rejected(self):
        with self.assertRaises(
            CorruptionError
        ):
            apply_corruption(
                make_stream(),
                CorruptionSpec(
                    family="TIMESTAMP_STEP_SHIFT",
                    modality="lidar",
                    start_index=2,
                    length=1,
                    parameters={
                        "offset_ns":
                            0,
                    },
                ),
            )

    def test_18_timestamp_shift_requires_length_one(self):
        with self.assertRaises(
            CorruptionError
        ):
            apply_corruption(
                make_stream(),
                CorruptionSpec(
                    family="TIMESTAMP_STEP_SHIFT",
                    modality="lidar",
                    start_index=2,
                    length=2,
                    parameters={
                        "offset_ns":
                            5,
                    },
                ),
            )

    def test_19_timestamp_corruption_may_make_output_nonmonotonic(self):
        pair = apply_corruption(
            make_stream(),
            CorruptionSpec(
                family="TIMESTAMP_STEP_SHIFT",
                modality="lidar",
                start_index=2,
                length=1,
                parameters={
                    "offset_ns":
                        -150,
                },
            ),
        )

        self.assertFalse(
            pair.corrupt.timestamps_strictly_increasing()
        )

        self.assertTrue(
            pair.clean.timestamps_strictly_increasing()
        )

    def test_20_nonmonotonic_clean_input_is_rejected(self):
        clean = EventStream(
            modality="imu",
            source_id="imu",
            timestamps_ns=np.asarray(
                [
                    1,
                    3,
                    2,
                ],
                dtype=np.int64,
            ),
            payloads=(
                np.asarray(
                    [
                        1.0,
                    ]
                ),
                np.asarray(
                    [
                        2.0,
                    ]
                ),
                np.asarray(
                    [
                        3.0,
                    ]
                ),
            ),
        )

        with self.assertRaises(
            CorruptionError
        ):
            apply_corruption(
                clean,
                CorruptionSpec(
                    family="EVENT_REPEAT",
                    modality="imu",
                    start_index=1,
                    length=1,
                ),
            )

    def test_21_modality_mismatch_is_rejected(self):
        with self.assertRaises(
            CorruptionError
        ):
            apply_corruption(
                make_stream(),
                CorruptionSpec(
                    family="EVENT_GAP",
                    modality="camera",
                    start_index=1,
                    length=1,
                ),
            )

    def test_22_manifest_is_deterministic_and_scientifically_bounded(self):
        pair = apply_corruption(
            make_stream(),
            CorruptionSpec(
                family="EVENT_GAP",
                modality="lidar",
                start_index=2,
                length=1,
            ),
        )

        first = build_pair_manifest(
            pair
        )

        second = build_pair_manifest(
            pair
        )

        self.assertEqual(
            first,
            second,
        )

        scope = first[
            "scientific_scope"
        ]

        self.assertTrue(
            scope[
                "paired_clean_corrupt"
            ]
        )

        for key in (
            "clean_input_mutated",
            "reference_data_used",
            "confirmation_test_data_used",
            "severity_selected_by_engine",
            "attack_budget_selected_by_engine",
            "synthetic_truth_is_physical_cause_evidence",
            "synthetic_truth_is_runtime_causal_evidence",
            "estimator_scoring_performed",
            "ate_computed",
            "rpe_computed",
        ):
            self.assertFalse(
                scope[
                    key
                ]
            )

    def test_23_immutable_writer_allows_identical_and_rejects_change(self):
        first_pair = apply_corruption(
            make_stream(),
            CorruptionSpec(
                family="EVENT_GAP",
                modality="lidar",
                start_index=2,
                length=1,
            ),
        )

        second_pair = apply_corruption(
            make_stream(),
            CorruptionSpec(
                family="EVENT_REPEAT",
                modality="lidar",
                start_index=2,
                length=1,
            ),
        )

        with TemporaryDirectory() as tmp:
            path = (
                Path(
                    tmp
                )
                / "pair.json"
            )

            write_immutable_manifest(
                path,
                first_pair,
            )

            before = path.read_text(
                encoding="utf-8"
            )

            write_immutable_manifest(
                path,
                first_pair,
            )

            self.assertEqual(
                path.read_text(
                    encoding="utf-8"
                ),
                before,
            )

            with self.assertRaises(
                FileExistsError
            ):
                write_immutable_manifest(
                    path,
                    second_pair,
                )

    def test_24_identical_input_and_spec_reproduce_exact_pair(self):
        first = apply_corruption(
            make_stream(),
            CorruptionSpec(
                family="EVENT_REPEAT",
                modality="lidar",
                start_index=2,
                length=2,
            ),
        )

        second = apply_corruption(
            make_stream(),
            CorruptionSpec(
                family="EVENT_REPEAT",
                modality="lidar",
                start_index=2,
                length=2,
            ),
        )

        self.assertEqual(
            first.clean.fingerprint(),
            second.clean.fingerprint(),
        )

        self.assertEqual(
            first.corrupt.fingerprint(),
            second.corrupt.fingerprint(),
        )

        self.assertEqual(
            first.truths[
                0
            ].injection_id,
            second.truths[
                0
            ].injection_id,
        )

        self.assertEqual(
            manifest_json(
                first
            ),
            manifest_json(
                second
            ),
        )

    def test_25_no_historical_runtime_dependency_or_numeric_policy_defaults(self):
        source = MODULE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source,
            filename=str(
                MODULE
            ),
        )

        imported_roots = set()

        for node in ast.walk(
            tree
        ):
            if isinstance(
                node,
                ast.Import,
            ):
                for alias in node.names:
                    imported_roots.add(
                        alias.name.split(
                            "."
                        )[
                            0
                        ]
                    )

            elif (
                isinstance(
                    node,
                    ast.ImportFrom,
                )
                and node.module
                and node.level == 0
            ):
                imported_roots.add(
                    node.module.split(
                        "."
                    )[
                        0
                    ]
                )

        self.assertNotIn(
            "imu_reliability",
            imported_roots,
        )

        config = json.loads(
            CONFIG.read_text(
                encoding="utf-8"
            )
        )

        policy = config[
            "parameter_policy"
        ]

        for key in (
            "severity_grid",
            "fault_magnitudes",
            "attack_budgets",
            "noise_distribution_parameters",
            "dropout_probability",
            "drift_rate",
            "timing_jitter_distribution",
            "default_numeric_corruption_magnitude",
        ):
            self.assertIsNone(
                policy[
                    key
                ]
            )

        self.assertFalse(
            policy[
                "confirmation_test_may_select_parameters"
            ]
        )


if __name__ == "__main__":
    unittest.main()
