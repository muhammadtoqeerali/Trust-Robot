from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]

MODULE_PATH = (
    ROOT
    / "experiments/01_integrity_p0/"
      "evaluate_integrity_calibration_v1.py"
)

SPEC = importlib.util.spec_from_file_location(
    "evaluate_integrity_calibration_v1",
    MODULE_PATH,
)

if (
    SPEC is None
    or SPEC.loader is None
):
    raise RuntimeError(
        "Unable to import calibration evaluator"
    )

EVAL = importlib.util.module_from_spec(
    SPEC
)

sys.modules[
    SPEC.name
] = EVAL

SPEC.loader.exec_module(
    EVAL
)

from imu_reliability.integrity.evidence import (
    EvidenceStatus,
    IntegrityCause,
    SuspectIndicator,
)
from imu_reliability.integrity.flatness import (
    ChannelFreezeConfig,
    ChannelFreezeMonitor,
)
from imu_reliability.integrity.monitor import (
    assess_evidence,
)
from imu_reliability.integrity.timing import (
    TimingEnvelope,
    evaluate_timing_envelope,
)
from imu_reliability.injection.p0 import (
    apply_p0_injection,
)
from imu_reliability.injection.types import (
    P0InjectionSpec,
    P0Stream,
)


def tiny_protocol():
    return {
        "timing_preprocessing_contract": {
            "KFALL": {
                "multiply_raw_timestamp_by":
                    1000.0,
            },
            "UNIVRFALL": {
                "multiply_raw_timestamp_by":
                    1.0,
            },
        },
    }


class IntegrityCalibrationV1Tests(
    unittest.TestCase
):

    def test_artifact_content_digest_survives_json_roundtrip(
        self,
    ):
        import json

        payload = {
            "channel_freeze": {
                2: {
                    "feasible":
                        False,
                },
                10: {
                    "feasible":
                        True,
                },
                20: {
                    "feasible":
                        False,
                },
            },
        }

        stored = (
            EVAL
            .artifact_content_digest(
                payload
            )
        )

        reloaded = json.loads(
            json.dumps(
                payload
            )
        )

        computed_after_reload = (
            EVAL
            .canonical_digest(
                reloaded
            )
        )

        self.assertEqual(
            stored,
            computed_after_reload,
        )

    def test_deterministic_candidate_selection(
        self,
    ):
        candidates = [
            {
                "absolute_tolerance":
                    0.0,
                "consecutive_deltas":
                    5,
                "feasible":
                    True,
                "equal_dataset_weighted_macro_event_recall":
                    0.8,
                "median_confirmation_latency_ms":
                    40.0,
            },
            {
                "absolute_tolerance":
                    0.0,
                "consecutive_deltas":
                    8,
                "feasible":
                    True,
                "equal_dataset_weighted_macro_event_recall":
                    0.8,
                "median_confirmation_latency_ms":
                    40.0,
            },
        ]

        a = (
            EVAL
            .select_channel_freeze_candidate(
                candidates
            )
        )

        b = (
            EVAL
            .select_channel_freeze_candidate(
                candidates
            )
        )

        self.assertEqual(
            a[
                "selected_candidate"
            ][
                "consecutive_deltas"
            ],
            8,
        )

        self.assertEqual(
            EVAL.canonical_digest(
                a
            ),
            EVAL.canonical_digest(
                b
            ),
        )

    def test_clean_corrupt_pairing_retained(
        self,
    ):
        clean = P0Stream(
            values=np.asarray(
                [
                    [0.0],
                    [1.0],
                    [2.0],
                    [3.0],
                    [4.0],
                ]
            ),
            timestamps=np.arange(
                5,
                dtype=float,
            )
            * 0.01,
            counters=np.arange(
                10,
                15,
                dtype=np.int64,
            ),
            source_id="TEST",
        )

        spec = P0InjectionSpec(
            kind="FRAME_GAP",
            start_index=2,
            length=1,
            severity="low",
        )

        pair = apply_p0_injection(
            clean,
            spec,
        )

        self.assertIs(
            pair.clean,
            clean,
        )

        self.assertTrue(
            np.array_equal(
                pair.corrupt.origin_indices,
                np.asarray(
                    [0, 1, 3, 4]
                ),
            )
        )

        self.assertEqual(
            pair.truths[0]
            .affected_clean_start,
            2,
        )

    def test_no_final_test_access_boundary(
        self,
    ):
        manifest = {
            "partition":
                "final_test",
            "calibration_trial_count":
                446,
            "trials":
                [],
            "attempts":
                [],
        }

        with self.assertRaises(
            RuntimeError
        ):
            (
                EVAL
                .validate_calibration_manifest_boundary(
                    manifest
                )
            )

    def test_exact_timing_unit_conversion(
        self,
    ):
        protocol = tiny_protocol()

        kfall = P0Stream(
            values=np.zeros(
                (3, 1)
            ),
            timestamps=np.asarray(
                [
                    0.0,
                    0.01,
                    0.02,
                ]
            ),
            source_id="K",
        )

        univr = P0Stream(
            values=np.zeros(
                (3, 1)
            ),
            timestamps=np.asarray(
                [
                    0.0,
                    10.0,
                    20.0,
                ]
            ),
            source_id="U",
        )

        self.assertTrue(
            np.array_equal(
                EVAL.timestamps_to_ms(
                    kfall,
                    "KFALL",
                    protocol,
                ),
                np.asarray(
                    [
                        0.0,
                        10.0,
                        20.0,
                    ]
                ),
            )
        )

        self.assertTrue(
            np.array_equal(
                EVAL.timestamps_to_ms(
                    univr,
                    "UNIVRFALL",
                    protocol,
                ),
                np.asarray(
                    [
                        0.0,
                        10.0,
                        20.0,
                    ]
                ),
            )
        )

    def test_kfall_gap_hard_univr_not_hard(
        self,
    ):
        corrupt = P0Stream(
            values=np.zeros(
                (4, 1)
            ),
            timestamps=np.asarray(
                [
                    0.0,
                    0.01,
                    0.03,
                    0.04,
                ]
            ),
            counters=np.asarray(
                [
                    1,
                    2,
                    4,
                    5,
                ]
            ),
            source_id="TEST",
        )

        kfall = (
            EVAL
            .evaluate_frame_gap_event(
                "KFALL",
                corrupt,
                corrupt_anchor_index=2,
            )
        )

        self.assertTrue(
            kfall[
                "detected"
            ]
        )

        self.assertTrue(
            kfall[
                "hard_qualified"
            ]
        )

        self.assertEqual(
            kfall[
                "cause"
            ],
            "FRAME_GAP",
        )

        univr = (
            EVAL
            .evaluate_frame_gap_event(
                "UNIVRFALL",
                corrupt,
                corrupt_anchor_index=2,
            )
        )

        self.assertFalse(
            univr[
                "detected"
            ]
        )

        self.assertFalse(
            univr[
                "hard_qualified"
            ]
        )

    def test_channel_freeze_persistence_matches_core(
        self,
    ):
        values = np.asarray(
            [
                [0.0, 0.0],
                [1.0, 1.0],
                [1.0, 2.0],
                [1.0, 3.0],
                [1.0, 4.0],
                [5.0, 5.0],
            ]
        )

        runs = (
            EVAL
            .freeze_run_lengths(
                values,
                absolute_tolerance=0.0,
            )
        )

        vectorized = (
            EVAL
            .freeze_state_from_runs(
                runs,
                consecutive_deltas=3,
            )
        )

        reference = (
            EVAL
            .monitor_freeze_state_reference(
                values,
                absolute_tolerance=0.0,
                consecutive_deltas=3,
            )
        )

        self.assertTrue(
            np.array_equal(
                vectorized,
                reference,
            )
        )

        self.assertTrue(
            np.array_equal(
                vectorized,
                np.asarray(
                    [
                        False,
                        False,
                        False,
                        False,
                        True,
                        False,
                    ]
                ),
            )
        )

    def test_channel_freeze_remains_suspect_only(
        self,
    ):
        monitor = (
            ChannelFreezeMonitor(
                n_channels=1,
                config=(
                    ChannelFreezeConfig(
                        absolute_tolerance=
                            0.0,
                        consecutive_deltas=
                            2,
                    )
                ),
            )
        )

        monitor.update(
            [1.0],
            source="TEST",
        )

        monitor.update(
            [1.0],
            source="TEST",
        )

        evidence = monitor.update(
            [1.0],
            source="TEST",
        )

        assessment = assess_evidence(
            evidence
        )

        self.assertFalse(
            assessment.has_hard_alert
        )

        self.assertEqual(
            assessment.cause_mask,
            IntegrityCause.NONE,
        )

        self.assertIn(
            SuspectIndicator
            .CHANNEL_FREEZE_SUSPECT,
            assessment.suspects,
        )

        self.assertTrue(
            all(
                item.status
                is EvidenceStatus.SUSPECT_ONLY
                for item
                in evidence
            )
        )

    def test_timing_candidate_is_observation_only(
        self,
    ):
        envelope = TimingEnvelope(
            minimum_delta=9.9,
            maximum_delta=10.1,
            unit="ms",
            frozen=False,
        )

        evidence = (
            evaluate_timing_envelope(
                0.0,
                20.0,
                envelope=envelope,
                timestamp_provenance_qualified=
                    False,
                source="TEST",
            )
        )

        self.assertIsNotNone(
            evidence
        )

        self.assertIs(
            evidence.status,
            EvidenceStatus.OBSERVATION_ONLY,
        )

        self.assertFalse(
            assess_evidence(
                [evidence]
            ).has_hard_alert
        )

    def test_unsupported_causes_do_not_enter_hard_set(
        self,
    ):
        clean = P0Stream(
            values=np.asarray(
                [
                    [0.0],
                    [1.0],
                    [2.0],
                    [3.0],
                ]
            ),
            timestamps=np.asarray(
                [
                    0.0,
                    0.01,
                    0.02,
                    0.03,
                ]
            ),
            counters=np.asarray(
                [
                    1,
                    2,
                    3,
                    4,
                ]
            ),
            source_id="TEST",
        )

        spec = P0InjectionSpec(
            kind="FRAME_REPEAT",
            start_index=2,
            length=1,
            severity="low",
        )

        pair = apply_p0_injection(
            clean,
            spec,
        )

        truth_evidence = (
            EVAL
            .p0_truth_to_evidence(
                pair.truths[0]
            )
        )

        assessment = assess_evidence(
            [truth_evidence]
        )

        self.assertFalse(
            assessment.has_hard_alert
        )

        self.assertEqual(
            assessment.cause_mask,
            IntegrityCause.NONE,
        )

    def test_noop_corruption_rejected(
        self,
    ):
        clean = P0Stream(
            values=np.asarray(
                [
                    [1.0],
                    [1.0],
                    [1.0],
                    [1.0],
                ]
            ),
            timestamps=np.asarray(
                [
                    0.0,
                    0.01,
                    0.02,
                    0.03,
                ]
            ),
            source_id="TEST",
        )

        spec = P0InjectionSpec(
            kind="CHANNEL_FREEZE",
            start_index=1,
            length=2,
            severity="low",
            channels=(0,),
        )

        with self.assertRaisesRegex(
            ValueError,
            "no selected-channel change",
        ):
            apply_p0_injection(
                clean,
                spec,
            )

    def test_selection_rejects_infeasible_before_recall(
        self,
    ):
        candidates = [
            {
                "absolute_tolerance":
                    0.0,
                "consecutive_deltas":
                    2,
                "feasible":
                    False,
                "equal_dataset_weighted_macro_event_recall":
                    1.0,
                "median_confirmation_latency_ms":
                    0.0,
            },
            {
                "absolute_tolerance":
                    0.0,
                "consecutive_deltas":
                    10,
                "feasible":
                    True,
                "equal_dataset_weighted_macro_event_recall":
                    0.2,
                "median_confirmation_latency_ms":
                    90.0,
            },
        ]

        selected = (
            EVAL
            .select_channel_freeze_candidate(
                candidates
            )[
                "selected_candidate"
            ]
        )

        self.assertEqual(
            selected[
                "consecutive_deltas"
            ],
            10,
        )

    def test_timing_tie_break_prefers_wider_envelope(
        self,
    ):
        candidates = [
            {
                "minimum_delta_ms":
                    9.5,
                "maximum_delta_ms":
                    10.5,
                "feasible":
                    True,
                "macro_event_recall":
                    0.75,
            },
            {
                "minimum_delta_ms":
                    8.0,
                "maximum_delta_ms":
                    12.0,
                "feasible":
                    True,
                "macro_event_recall":
                    0.75,
            },
        ]

        selected = (
            EVAL
            .select_timing_candidate(
                candidates
            )[
                "selected_candidate"
            ]
        )

        self.assertEqual(
            selected[
                "minimum_delta_ms"
            ],
            8.0,
        )

        self.assertEqual(
            selected[
                "maximum_delta_ms"
            ],
            12.0,
        )

    def test_no_feasible_candidate_does_not_relax(
        self,
    ):
        freeze = (
            EVAL
            .select_channel_freeze_candidate(
                [
                    {
                        "absolute_tolerance":
                            0.0,
                        "consecutive_deltas":
                            2,
                        "feasible":
                            False,
                        "equal_dataset_weighted_macro_event_recall":
                            1.0,
                        "median_confirmation_latency_ms":
                            10.0,
                    }
                ]
            )
        )

        self.assertIsNone(
            freeze[
                "selected_candidate"
            ]
        )

        self.assertEqual(
            freeze[
                "failure_policy_applied"
            ],
            "NO_FEASIBLE_CANDIDATE_DISABLE_MAIN_SUSPECT",
        )

        timing = (
            EVAL
            .select_timing_candidate(
                [
                    {
                        "minimum_delta_ms":
                            9.9,
                        "maximum_delta_ms":
                            10.1,
                        "feasible":
                            False,
                        "macro_event_recall":
                            1.0,
                    }
                ]
            )
        )

        self.assertIsNone(
            timing[
                "selected_candidate"
            ]
        )

        self.assertEqual(
            timing[
                "failure_policy_applied"
            ],
            "NO_FEASIBLE_ENVELOPE_REMAIN_RAW_OBSERVATION_ONLY",
        )

    def test_clean_feasibility_is_independent_of_corruption_recall(
        self,
    ):
        protocol = {
            "clean_constraints": {
                "CHANNEL_FREEZE_SUSPECT": {
                    "maximum_onsets_per_hour_per_dataset":
                        1.0,
                    "maximum_time_in_suspect_fraction_per_dataset":
                        0.005,
                    "maximum_fraction_of_clean_trials_with_any_suspect_per_dataset":
                        0.05,
                },
                "TIMING_OBSERVATION_ENVELOPE": {
                    "maximum_outside_intervals_per_hour_per_dataset":
                        3.0,
                    "maximum_fraction_of_clean_trials_with_any_outside_interval_per_dataset":
                        0.05,
                },
            },
            "search_spaces": {
                "CHANNEL_FREEZE_SUSPECT": {
                    "consecutive_deltas":
                        [2],
                },
            },
        }

        clean = {
            "channel_freeze": {
                2: {
                    "KFALL": {
                        "suspect_onsets_per_hour":
                            2.0,
                        "time_in_suspect_fraction":
                            0.0,
                        "fraction_trials_with_any_suspect":
                            0.0,
                    },
                    "UNIVRFALL": {
                        "suspect_onsets_per_hour":
                            0.0,
                        "time_in_suspect_fraction":
                            0.0,
                        "fraction_trials_with_any_suspect":
                            0.0,
                    },
                },
            },
            "timing": {
                "KFALL": [
                    {
                        "minimum_delta_ms":
                            9.9,
                        "maximum_delta_ms":
                            10.1,
                        "timing_outside_intervals_per_hour":
                            0.0,
                        "fraction_trials_with_any_timing_outside":
                            0.0,
                    }
                ],
                "UNIVRFALL": [
                    {
                        "minimum_delta_ms":
                            -0.5,
                        "maximum_delta_ms":
                            20.5,
                        "timing_outside_intervals_per_hour":
                            0.0,
                        "fraction_trials_with_any_timing_outside":
                            0.0,
                    }
                ],
            },
            "hard_cause": {
                "KFALL": {
                    "hard_alert_count":
                        0,
                },
                "UNIVRFALL": {
                    "hard_alert_count":
                        0,
                },
            },
        }

        result = (
            EVAL
            .evaluate_clean_feasibility(
                clean,
                protocol,
            )
        )

        self.assertFalse(
            result[
                "CHANNEL_FREEZE_SUSPECT"
            ][0][
                "feasible"
            ]
        )

        self.assertIn(
            "KFALL:suspect_onsets_per_hour",
            result[
                "CHANNEL_FREEZE_SUSPECT"
            ][0][
                "infeasible_reasons"
            ],
        )

        self.assertTrue(
            result[
                "TIMING_OBSERVATION_ENVELOPE"
            ][
                "KFALL"
            ][0][
                "feasible"
            ]
        )

        self.assertTrue(
            result[
                "hard_cause_set"
            ][
                "feasible"
            ]
        )

    def test_event_level_latency_aggregation(
        self,
    ):
        protocol = {
            "clean_constraints": {
                "CHANNEL_FREEZE_SUSPECT": {
                    "maximum_onsets_per_hour_per_dataset":
                        1.0,
                    "maximum_time_in_suspect_fraction_per_dataset":
                        0.005,
                    "maximum_fraction_of_clean_trials_with_any_suspect_per_dataset":
                        0.05,
                },
            },
            "search_spaces": {
                "CHANNEL_FREEZE_SUSPECT": {
                    "consecutive_deltas":
                        [2],
                },
            },
        }

        clean_metrics = {
            "channel_freeze": {
                2: {
                    dataset: {
                        "suspect_onsets_per_hour":
                            0.0,
                        "time_in_suspect_fraction":
                            0.0,
                        "fraction_trials_with_any_suspect":
                            0.0,
                    }
                    for dataset
                    in EVAL.SUPPORTED_DATASETS
                },
            },
        }

        values = {
            "KFALL": {
                "low":
                    [10.0],
                "medium":
                    [20.0],
                "high":
                    [30.0],
            },
            "UNIVRFALL": {
                "low":
                    [40.0],
                "medium":
                    [50.0],
                "high":
                    [100.0],
            },
        }

        corrupt_metrics = {
            "channel_freeze": {
                "2": {
                    dataset: {
                        severity: {
                            "event_detection_recall":
                                1.0,
                            "detected_count":
                                len(
                                    values[
                                        dataset
                                    ][severity]
                                ),
                            "confirmation_latency_samples":
                                [
                                    int(
                                        x / 10
                                    )
                                    for x
                                    in values[
                                        dataset
                                    ][severity]
                                ],
                            "confirmation_latency_ms":
                                list(
                                    values[
                                        dataset
                                    ][severity]
                                ),
                            "median_confirmation_latency_ms":
                                999.0,
                        }
                        for severity
                        in EVAL.SEVERITIES
                    }
                    for dataset
                    in EVAL.SUPPORTED_DATASETS
                },
            },
        }

        rows = (
            EVAL
            .build_channel_freeze_candidates(
                clean_metrics,
                corrupt_metrics,
                protocol,
            )
        )

        self.assertEqual(
            len(
                rows
            ),
            1,
        )

        self.assertEqual(
            rows[0][
                "confirmation_latency_event_count"
            ],
            6,
        )

        self.assertEqual(
            rows[0][
                "median_confirmation_latency_ms"
            ],
            35.0,
        )


if __name__ == "__main__":
    unittest.main()
