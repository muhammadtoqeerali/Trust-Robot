import tempfile
import unittest
from pathlib import Path

import numpy as np

from imu_reliability.injection import (
    P0CorruptionKind,
    P0InjectionSpec,
    P0Stream,
    apply_p0_injection,
    p0_truth_to_evidence,
    write_immutable_manifest,
)
from imu_reliability.integrity import (
    EvidenceStatus,
    IntegrityCause,
    assess_evidence,
    observe_frame_counter,
)


def make_stream() -> P0Stream:

    values = np.arange(
        60,
        dtype=np.float64,
    ).reshape(10, 6)

    timestamps = (
        np.arange(
            1,
            11,
            dtype=np.float64,
        )
        * 0.01
    )

    counters = np.arange(
        1,
        11,
        dtype=np.int64,
    )

    return P0Stream(
        values=values,
        timestamps=timestamps,
        counters=counters,
        source_id="unit_test_stream",
    )


class StreamTests(unittest.TestCase):

    def test_stream_arrays_are_read_only(self):

        stream = make_stream()

        with self.assertRaises(
            ValueError
        ):
            stream.values[
                0,
                0,
            ] = -1


    def test_spec_id_is_deterministic(self):

        a = P0InjectionSpec(
            kind=P0CorruptionKind.FRAME_GAP,
            start_index=3,
            length=2,
            severity="moderate",
        )

        b = P0InjectionSpec(
            kind=P0CorruptionKind.FRAME_GAP,
            start_index=3,
            length=2,
            severity="moderate",
        )

        self.assertEqual(
            a.spec_id,
            b.spec_id,
        )


class FrameGapTests(unittest.TestCase):

    def test_frame_gap_removes_samples_but_not_clean(self):

        clean = make_stream()

        original = clean.values.copy()

        spec = P0InjectionSpec(
            kind=P0CorruptionKind.FRAME_GAP,
            start_index=4,
            length=2,
            severity="moderate",
        )

        pair = apply_p0_injection(
            clean,
            spec,
        )

        self.assertEqual(
            pair.clean.n_samples,
            10,
        )

        self.assertEqual(
            pair.corrupt.n_samples,
            8,
        )

        np.testing.assert_array_equal(
            clean.values,
            original,
        )

        np.testing.assert_array_equal(
            pair.corrupt.origin_indices,
            np.array(
                [0, 1, 2, 3, 6, 7, 8, 9]
            ),
        )


    def test_gap_creates_runtime_counter_discontinuity(self):

        clean = make_stream()

        pair = apply_p0_injection(
            clean,
            P0InjectionSpec(
                kind=P0CorruptionKind.FRAME_GAP,
                start_index=4,
                length=2,
                severity="moderate",
            ),
        )

        previous = int(
            pair.corrupt.counters[3]
        )

        current = int(
            pair.corrupt.counters[4]
        )

        evidence = observe_frame_counter(
            previous,
            current,
            provenance_qualified=True,
            source="qualified_test_counter",
        )

        assessment = assess_evidence(
            [evidence]
        )

        self.assertEqual(
            assessment.cause_mask,
            IntegrityCause.FRAME_GAP,
        )

        self.assertEqual(
            evidence.details[
                "estimated_missing_frames"
            ],
            2,
        )


    def test_p0_gap_truth_itself_is_not_hard_runtime_evidence(self):

        clean = make_stream()

        pair = apply_p0_injection(
            clean,
            P0InjectionSpec(
                kind=P0CorruptionKind.FRAME_GAP,
                start_index=4,
                length=2,
                severity="moderate",
            ),
        )

        truth_evidence = (
            p0_truth_to_evidence(
                pair.truths[0]
            )
        )

        self.assertEqual(
            truth_evidence.status,
            EvidenceStatus.SYNTHETIC_GROUND_TRUTH,
        )

        assessment = assess_evidence(
            [truth_evidence]
        )

        self.assertEqual(
            assessment.cause_mask,
            IntegrityCause.NONE,
        )


class FrameRepeatTests(unittest.TestCase):

    def test_repeat_changes_values_only(self):

        clean = make_stream()

        pair = apply_p0_injection(
            clean,
            P0InjectionSpec(
                kind=P0CorruptionKind.FRAME_REPEAT,
                start_index=4,
                length=3,
                severity="moderate",
            ),
        )

        expected = np.repeat(
            clean.values[
                3:4
            ],
            3,
            axis=0,
        )

        np.testing.assert_array_equal(
            pair.corrupt.values[
                4:7
            ],
            expected,
        )

        np.testing.assert_array_equal(
            pair.corrupt.counters,
            clean.counters,
        )

        np.testing.assert_array_equal(
            pair.corrupt.timestamps,
            clean.timestamps,
        )


class ChannelFreezeTests(unittest.TestCase):

    def test_channel_freeze_only_touches_selected_channels(self):

        clean = make_stream()

        pair = apply_p0_injection(
            clean,
            P0InjectionSpec(
                kind=P0CorruptionKind.CHANNEL_FREEZE,
                start_index=3,
                length=4,
                severity="moderate",
                channels=(1, 4),
            ),
        )

        for channel in (1, 4):

            expected = np.repeat(
                clean.values[
                    2,
                    channel,
                ],
                4,
            )

            np.testing.assert_array_equal(
                pair.corrupt.values[
                    3:7,
                    channel,
                ],
                expected,
            )

        for channel in (0, 2, 3, 5):

            np.testing.assert_array_equal(
                pair.corrupt.values[
                    :,
                    channel,
                ],
                clean.values[
                    :,
                    channel,
                ],
            )


class TimingTests(unittest.TestCase):

    def test_timing_step_changes_one_boundary(self):

        clean = make_stream()

        pair = apply_p0_injection(
            clean,
            P0InjectionSpec(
                kind=P0CorruptionKind.TIMING_PERTURBATION,
                start_index=5,
                length=1,
                severity="moderate",
                parameters={
                    "offset": 0.05,
                },
            ),
        )

        clean_delta = np.diff(
            clean.timestamps
        )

        corrupt_delta = np.diff(
            pair.corrupt.timestamps
        )

        changed = np.where(
            ~np.isclose(
                clean_delta,
                corrupt_delta,
            )
        )[0]

        np.testing.assert_array_equal(
            changed,
            np.array([4]),
        )

        self.assertAlmostEqual(
            corrupt_delta[4]
            - clean_delta[4],
            0.05,
        )


class RangeClipTests(unittest.TestCase):

    def test_range_clip_is_experimental_not_physical_rail_claim(self):

        clean = make_stream()

        pair = apply_p0_injection(
            clean,
            P0InjectionSpec(
                kind=P0CorruptionKind.RANGE_CLIP,
                start_index=2,
                length=5,
                severity="moderate",
                channels=(0, 1),
                parameters={
                    "low": 15.0,
                    "high": 25.0,
                },
            ),
        )

        affected = pair.corrupt.values[
            2:7,
            :2,
        ]

        self.assertTrue(
            np.all(
                affected >= 15.0
            )
        )

        self.assertTrue(
            np.all(
                affected <= 25.0
            )
        )

        self.assertFalse(
            pair.truths[0].details[
                "physical_rail_claim"
            ]
        )


class ManifestTests(unittest.TestCase):

    def test_manifest_is_idempotent_but_immutable(self):

        clean = make_stream()

        pair_a = apply_p0_injection(
            clean,
            P0InjectionSpec(
                kind=P0CorruptionKind.FRAME_GAP,
                start_index=3,
                length=1,
                severity="low",
            ),
        )

        pair_b = apply_p0_injection(
            clean,
            P0InjectionSpec(
                kind=P0CorruptionKind.FRAME_GAP,
                start_index=3,
                length=2,
                severity="high",
            ),
        )

        with tempfile.TemporaryDirectory() as tmp:

            path = Path(tmp) / "manifest.json"

            write_immutable_manifest(
                path,
                pair_a,
            )

            first = path.read_text()

            # Exact same content is allowed.
            write_immutable_manifest(
                path,
                pair_a,
            )

            second = path.read_text()

            self.assertEqual(
                first,
                second,
            )

            # Different content cannot replace the frozen path.
            with self.assertRaises(
                FileExistsError
            ):
                write_immutable_manifest(
                    path,
                    pair_b,
                )


    def test_clean_and_corrupt_fingerprints_differ(self):

        clean = make_stream()

        pair = apply_p0_injection(
            clean,
            P0InjectionSpec(
                kind=P0CorruptionKind.FRAME_REPEAT,
                start_index=3,
                length=2,
                severity="moderate",
            ),
        )

        self.assertNotEqual(
            pair.clean.fingerprint(),
            pair.corrupt.fingerprint(),
        )



class P0HardeningTests(unittest.TestCase):

    def test_same_spec_different_streams_get_different_instance_ids(self):

        clean_a = make_stream()

        clean_b = P0Stream(
            values=clean_a.values,
            timestamps=clean_a.timestamps,
            counters=clean_a.counters,
            source_id="different_trial",
        )

        spec = P0InjectionSpec(
            kind=P0CorruptionKind.FRAME_GAP,
            start_index=3,
            length=1,
            severity="low",
        )

        pair_a = apply_p0_injection(
            clean_a,
            spec,
        )

        pair_b = apply_p0_injection(
            clean_b,
            spec,
        )

        self.assertEqual(
            pair_a.truths[0].spec.spec_id,
            pair_b.truths[0].spec.spec_id,
        )

        self.assertNotEqual(
            pair_a.truths[0].injection_id,
            pair_b.truths[0].injection_id,
        )


    def test_frame_gap_must_leave_post_gap_boundary(self):

        clean = make_stream()

        spec = P0InjectionSpec(
            kind=P0CorruptionKind.FRAME_GAP,
            start_index=8,
            length=2,
            severity="high",
        )

        with self.assertRaises(
            ValueError
        ):
            apply_p0_injection(
                clean,
                spec,
            )


    def test_frame_repeat_noop_is_rejected(self):

        clean = P0Stream(
            values=np.ones(
                (8, 3),
                dtype=np.float64,
            ),
            timestamps=np.arange(
                8,
                dtype=np.float64,
            ),
            counters=np.arange(
                8,
                dtype=np.int64,
            ),
            source_id="constant_stream",
        )

        spec = P0InjectionSpec(
            kind=P0CorruptionKind.FRAME_REPEAT,
            start_index=2,
            length=2,
            severity="low",
        )

        with self.assertRaises(
            ValueError
        ):
            apply_p0_injection(
                clean,
                spec,
            )


    def test_channel_freeze_noop_is_rejected(self):

        clean = P0Stream(
            values=np.ones(
                (8, 3),
                dtype=np.float64,
            ),
            source_id="constant_stream",
        )

        spec = P0InjectionSpec(
            kind=P0CorruptionKind.CHANNEL_FREEZE,
            start_index=2,
            length=3,
            severity="low",
            channels=(1,),
        )

        with self.assertRaises(
            ValueError
        ):
            apply_p0_injection(
                clean,
                spec,
            )


    def test_zero_timing_offset_is_rejected(self):

        clean = make_stream()

        spec = P0InjectionSpec(
            kind=P0CorruptionKind.TIMING_PERTURBATION,
            start_index=4,
            length=1,
            severity="low",
            parameters={
                "offset": 0.0,
            },
        )

        with self.assertRaises(
            ValueError
        ):
            apply_p0_injection(
                clean,
                spec,
            )


    def test_range_clip_noop_is_rejected(self):

        clean = make_stream()

        spec = P0InjectionSpec(
            kind=P0CorruptionKind.RANGE_CLIP,
            start_index=2,
            length=3,
            severity="low",
            channels=(0,),
            parameters={
                "low": -1_000_000.0,
                "high": 1_000_000.0,
            },
        )

        with self.assertRaises(
            ValueError
        ):
            apply_p0_injection(
                clean,
                spec,
            )


if __name__ == "__main__":
    unittest.main()
