import unittest

import numpy as np

from imu_reliability.integrity import (
    ChannelFreezeConfig,
    ChannelFreezeMonitor,
    EvidenceStatus,
    IntegrityCause,
    IntegrityEvidence,
    SuspectIndicator,
    TimingEnvelope,
    assess_evidence,
    evaluate_timing_envelope,
    observe_frame_counter,
    observe_timing_delta,
)


class FrameGapTests(unittest.TestCase):

    def test_contiguous_counter_has_no_evidence(self):
        evidence = observe_frame_counter(
            10,
            11,
            provenance_qualified=True,
            source="kfall_raw",
        )

        self.assertIsNone(evidence)


    def test_qualified_gap_enters_hard_set(self):
        evidence = observe_frame_counter(
            10,
            14,
            provenance_qualified=True,
            source="kfall_raw",
        )

        self.assertIsNotNone(evidence)

        self.assertEqual(
            evidence.status,
            EvidenceStatus.HARD_QUALIFIED,
        )

        assessment = assess_evidence(
            [evidence]
        )

        self.assertTrue(
            assessment.has_hard_alert
        )

        self.assertIn(
            IntegrityCause.FRAME_GAP,
            assessment.hard_causes,
        )

        self.assertEqual(
            assessment.cause_mask,
            IntegrityCause.FRAME_GAP,
        )


    def test_unverified_counter_gap_cannot_enter_hard_set(self):
        evidence = observe_frame_counter(
            10,
            14,
            provenance_qualified=False,
            source="univr_oriented_derived_counter",
        )

        self.assertEqual(
            evidence.status,
            EvidenceStatus.OBSERVATION_ONLY,
        )

        assessment = assess_evidence(
            [evidence]
        )

        self.assertFalse(
            assessment.has_hard_alert
        )

        self.assertEqual(
            assessment.cause_mask,
            IntegrityCause.NONE,
        )


    def test_duplicate_counter_is_not_frame_repeat(self):
        evidence = observe_frame_counter(
            10,
            10,
            provenance_qualified=True,
            source="raw_counter",
        )

        self.assertEqual(
            evidence.status,
            EvidenceStatus.OBSERVATION_ONLY,
        )

        self.assertEqual(
            evidence.candidate_cause,
            IntegrityCause.NONE,
        )

        assessment = assess_evidence(
            [evidence]
        )

        self.assertEqual(
            assessment.cause_mask,
            IntegrityCause.NONE,
        )


class TimingTests(unittest.TestCase):

    def test_raw_timing_observation_never_hard(self):
        evidence = observe_timing_delta(
            1000,
            1000,
            unit="ms",
            source="univr_raw_time_ms",
        )

        self.assertEqual(
            evidence.status,
            EvidenceStatus.OBSERVATION_ONLY,
        )

        assessment = assess_evidence(
            [evidence]
        )

        self.assertFalse(
            assessment.has_hard_alert
        )


    def test_unfrozen_envelope_cannot_be_hard(self):
        envelope = TimingEnvelope(
            minimum_delta=5,
            maximum_delta=25,
            unit="ms",
            frozen=False,
        )

        evidence = evaluate_timing_envelope(
            1000,
            1100,
            envelope=envelope,
            timestamp_provenance_qualified=True,
            source="development_test",
        )

        self.assertIsNotNone(evidence)

        self.assertEqual(
            evidence.status,
            EvidenceStatus.OBSERVATION_ONLY,
        )

        assessment = assess_evidence(
            [evidence]
        )

        self.assertFalse(
            assessment.has_hard_alert
        )


    def test_frozen_and_qualified_timing_may_be_hard(self):
        envelope = TimingEnvelope(
            minimum_delta=5,
            maximum_delta=25,
            unit="ms",
            frozen=True,
        )

        evidence = evaluate_timing_envelope(
            1000,
            1100,
            envelope=envelope,
            timestamp_provenance_qualified=True,
            source="qualified_test_stream",
        )

        self.assertEqual(
            evidence.status,
            EvidenceStatus.HARD_QUALIFIED,
        )

        assessment = assess_evidence(
            [evidence]
        )

        self.assertEqual(
            assessment.cause_mask,
            IntegrityCause.ACQ_TIMING_VIOLATION,
        )


class FreezeSuspectTests(unittest.TestCase):

    def test_freeze_is_suspect_only(self):
        monitor = ChannelFreezeMonitor(
            n_channels=3,
            config=ChannelFreezeConfig(
                absolute_tolerance=0.0,
                consecutive_deltas=3,
            ),
        )

        evidence = []

        for sample in [
            [1.0, 2.0, 3.0],
            [1.0, 2.1, 3.1],
            [1.0, 2.2, 3.2],
            [1.0, 2.3, 3.3],
        ]:
            evidence.extend(
                monitor.update(
                    sample,
                    source="unit_test",
                )
            )

        self.assertEqual(
            len(evidence),
            1,
        )

        self.assertEqual(
            evidence[0].status,
            EvidenceStatus.SUSPECT_ONLY,
        )

        self.assertEqual(
            evidence[0].suspect,
            SuspectIndicator.CHANNEL_FREEZE_SUSPECT,
        )

        assessment = assess_evidence(
            evidence
        )

        self.assertFalse(
            assessment.has_hard_alert
        )

        self.assertIn(
            SuspectIndicator.CHANNEL_FREEZE_SUSPECT,
            assessment.suspects,
        )


    def test_freeze_remains_active_after_threshold(self):
        monitor = ChannelFreezeMonitor(
            n_channels=1,
            config=ChannelFreezeConfig(
                absolute_tolerance=0.0,
                consecutive_deltas=2,
            ),
        )

        first = monitor.update(
            [5.0],
            source="unit_test",
        )

        second = monitor.update(
            [5.0],
            source="unit_test",
        )

        threshold_reached = monitor.update(
            [5.0],
            source="unit_test",
        )

        still_frozen = monitor.update(
            [5.0],
            source="unit_test",
        )

        self.assertEqual(first, [])
        self.assertEqual(second, [])

        self.assertEqual(
            len(threshold_reached),
            1,
        )

        self.assertEqual(
            len(still_frozen),
            1,
        )

        self.assertEqual(
            threshold_reached[0].suspect,
            SuspectIndicator.CHANNEL_FREEZE_SUSPECT,
        )

        self.assertEqual(
            still_frozen[0].status,
            EvidenceStatus.SUSPECT_ONLY,
        )

        assessment = assess_evidence(
            still_frozen
        )

        self.assertFalse(
            assessment.has_hard_alert
        )


class QualificationBarrierTests(unittest.TestCase):

    def test_synthetic_ground_truth_cannot_enter_hard_set(self):
        injected = IntegrityEvidence(
            indicator="P0_INJECTED_FRAME_GAP",
            status=EvidenceStatus.SYNTHETIC_GROUND_TRUTH,
            candidate_cause=IntegrityCause.FRAME_GAP,
            source="p0_injector",
        )

        assessment = assess_evidence(
            [injected]
        )

        self.assertEqual(
            assessment.cause_mask,
            IntegrityCause.NONE,
        )


    def test_multiple_qualified_causes_are_retained(self):
        frame_gap = IntegrityEvidence(
            indicator="FRAME_COUNTER_GAP",
            status=EvidenceStatus.HARD_QUALIFIED,
            candidate_cause=IntegrityCause.FRAME_GAP,
            source="unit_test",
        )

        timing = IntegrityEvidence(
            indicator="TIMING",
            status=EvidenceStatus.HARD_QUALIFIED,
            candidate_cause=IntegrityCause.ACQ_TIMING_VIOLATION,
            source="unit_test",
        )

        assessment = assess_evidence(
            [
                frame_gap,
                timing,
            ]
        )

        self.assertEqual(
            assessment.hard_causes,
            frozenset(
                {
                    IntegrityCause.FRAME_GAP,
                    IntegrityCause.ACQ_TIMING_VIOLATION,
                }
            ),
        )

        expected_mask = (
            IntegrityCause.FRAME_GAP
            | IntegrityCause.ACQ_TIMING_VIOLATION
        )

        self.assertEqual(
            assessment.cause_mask,
            expected_mask,
        )


if __name__ == "__main__":
    unittest.main()
