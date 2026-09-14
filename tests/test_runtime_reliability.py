from __future__ import annotations

import ast
import math
import unittest
from pathlib import Path

import torch
from torch import nn

from imu_reliability.integrity import (
    EvidenceStatus,
    IntegrityCause,
    IntegrityEvidence,
    SuspectIndicator,
    assess_evidence,
)
from imu_reliability.runtime import (
    OOD_THRESHOLD,
    SUPPORTED_HARD_CAUSE_MASK,
    RuntimeContractViolation,
    TrustState,
    decide_from_logits,
    run_reliability_window,
)


ROOT = Path(
    __file__
).resolve().parents[1]

DECISION_SOURCE = (
    ROOT
    / "src/imu_reliability/runtime/"
      "decision.py"
)

RELIABILITY_SOURCE = (
    ROOT
    / "src/imu_reliability/runtime/"
      "reliability.py"
)


def empty_assessment():
    return assess_evidence(
        []
    )


def frame_gap_assessment():
    evidence = IntegrityEvidence(
        indicator="FRAME_COUNTER_GAP",
        status=EvidenceStatus.HARD_QUALIFIED,
        candidate_cause=IntegrityCause.FRAME_GAP,
        source="qualified_raw_counter",
    )

    return assess_evidence(
        [
            evidence,
        ]
    )


class CountingModel(
    nn.Module
):
    def __init__(
        self,
        logits,
    ):
        super().__init__()

        self.calls = 0

        self.register_buffer(
            "_fixed_logits",
            torch.tensor(
                logits,
                dtype=torch.float64,
            ),
        )

        self.grad_enabled_during_call = None
        self.inference_mode_during_call = None

    def forward(
        self,
        window,
    ):
        self.calls += 1

        self.grad_enabled_during_call = (
            torch.is_grad_enabled()
        )

        self.inference_mode_during_call = (
            torch.is_inference_mode_enabled()
        )

        return (
            self._fixed_logits
            .reshape(
                1,
                2,
            )
            .clone()
        )


class RuntimeDecisionTests(
    unittest.TestCase
):

    def test_fixed_constants(
        self,
    ):
        self.assertEqual(
            OOD_THRESHOLD,
            0.00914505124092102,
        )

        self.assertEqual(
            SUPPORTED_HARD_CAUSE_MASK,
            IntegrityCause.FRAME_GAP,
        )

    def test_valid_state(
        self,
    ):
        logits = torch.tensor(
            [
                [
                    1.0,
                    0.0,
                ],
            ],
            dtype=torch.float64,
        )

        decision = decide_from_logits(
            logits,
            empty_assessment(),
        )

        self.assertEqual(
            decision.trust_state,
            TrustState.VALID,
        )

        self.assertEqual(
            decision.integrity_cause_mask,
            IntegrityCause.NONE,
        )

        self.assertGreater(
            decision.ood_margin,
            OOD_THRESHOLD,
        )

    def test_ood_unknown_below_threshold(
        self,
    ):
        logits = torch.tensor(
            [
                [
                    0.0,
                    0.0,
                ],
            ],
            dtype=torch.float64,
        )

        decision = decide_from_logits(
            logits,
            empty_assessment(),
        )

        self.assertEqual(
            decision.trust_state,
            TrustState.OOD_UNKNOWN,
        )

        self.assertEqual(
            decision.ood_margin,
            0.0,
        )

        self.assertEqual(
            decision.task_prediction,
            0,
        )

    def test_threshold_equality_is_accepted(
        self,
    ):
        logits = torch.tensor(
            [
                [
                    0.0,
                    OOD_THRESHOLD,
                ],
            ],
            dtype=torch.float64,
        )

        decision = decide_from_logits(
            logits,
            empty_assessment(),
        )

        self.assertEqual(
            decision.ood_margin,
            OOD_THRESHOLD,
        )

        self.assertEqual(
            decision.trust_state,
            TrustState.VALID,
        )

    def test_integrity_precedes_ood_unknown(
        self,
    ):
        logits = torch.tensor(
            [
                [
                    0.0,
                    0.0,
                ],
            ],
            dtype=torch.float64,
        )

        decision = decide_from_logits(
            logits,
            frame_gap_assessment(),
        )

        self.assertEqual(
            decision.trust_state,
            TrustState.INTEGRITY_ALERT,
        )

        self.assertEqual(
            decision.ood_margin,
            0.0,
        )

        self.assertEqual(
            decision.integrity_cause_mask,
            IntegrityCause.FRAME_GAP,
        )

    def test_task_prediction_preserved_under_integrity_alert(
        self,
    ):
        logits = torch.tensor(
            [
                [
                    0.0,
                    math.log(
                        19.0
                    ),
                ],
            ],
            dtype=torch.float64,
        )

        decision = decide_from_logits(
            logits,
            frame_gap_assessment(),
        )

        self.assertEqual(
            decision.trust_state,
            TrustState.INTEGRITY_ALERT,
        )

        self.assertEqual(
            decision.task_prediction,
            1,
        )

    def test_historical_decision_not_plain_argmax(
        self,
    ):
        logits = torch.tensor(
            [
                [
                    0.0,
                    math.log(
                        4.0
                    ),
                ],
            ],
            dtype=torch.float64,
        )

        self.assertEqual(
            int(
                torch.argmax(
                    logits,
                    dim=1,
                )[
                    0
                ]
            ),
            1,
        )

        decision = decide_from_logits(
            logits,
            empty_assessment(),
        )

        self.assertEqual(
            decision.task_prediction,
            0,
        )

        self.assertEqual(
            decision.trust_state,
            TrustState.VALID,
        )

    def test_suspect_is_diagnostic_only(
        self,
    ):
        suspect = IntegrityEvidence(
            indicator="CHANNEL_NEAR_CONSTANT",
            status=EvidenceStatus.SUSPECT_ONLY,
            suspect=(
                SuspectIndicator
                .CHANNEL_FREEZE_SUSPECT
            ),
            source="diagnostic",
        )

        assessment = assess_evidence(
            [
                suspect,
            ]
        )

        logits = torch.tensor(
            [
                [
                    1.0,
                    0.0,
                ],
            ],
            dtype=torch.float64,
        )

        decision = decide_from_logits(
            logits,
            assessment,
        )

        self.assertEqual(
            decision.trust_state,
            TrustState.VALID,
        )

        self.assertIn(
            SuspectIndicator.CHANNEL_FREEZE_SUSPECT,
            decision.suspects,
        )

    def test_unsupported_timing_hard_cause_is_rejected(
        self,
    ):
        evidence = IntegrityEvidence(
            indicator="TIMING",
            status=EvidenceStatus.HARD_QUALIFIED,
            candidate_cause=(
                IntegrityCause.ACQ_TIMING_VIOLATION
            ),
            source="generic_integrity_api",
        )

        assessment = assess_evidence(
            [
                evidence,
            ]
        )

        logits = torch.tensor(
            [
                [
                    1.0,
                    0.0,
                ],
            ],
            dtype=torch.float64,
        )

        with self.assertRaises(
            RuntimeContractViolation
        ):
            decide_from_logits(
                logits,
                assessment,
            )

    def test_mixed_supported_and_unsupported_hard_causes_are_rejected(
        self,
    ):
        frame = IntegrityEvidence(
            indicator="FRAME_COUNTER_GAP",
            status=EvidenceStatus.HARD_QUALIFIED,
            candidate_cause=(
                IntegrityCause.FRAME_GAP
            ),
            source="qualified_counter",
        )

        timing = IntegrityEvidence(
            indicator="TIMING",
            status=EvidenceStatus.HARD_QUALIFIED,
            candidate_cause=(
                IntegrityCause.ACQ_TIMING_VIOLATION
            ),
            source="generic_api",
        )

        assessment = assess_evidence(
            [
                frame,
                timing,
            ]
        )

        logits = torch.tensor(
            [
                [
                    1.0,
                    0.0,
                ],
            ],
            dtype=torch.float64,
        )

        with self.assertRaises(
            RuntimeContractViolation
        ):
            decide_from_logits(
                logits,
                assessment,
            )

    def test_logits_shape_is_exactly_one_binary_window(
        self,
    ):
        for shape in (
            (
                2,
            ),
            (
                2,
                2,
            ),
            (
                1,
                3,
            ),
        ):
            logits = torch.zeros(
                shape,
                dtype=torch.float64,
            )

            with self.assertRaises(
                RuntimeContractViolation
            ):
                decide_from_logits(
                    logits,
                    empty_assessment(),
                )


class IntegratedRuntimeTests(
    unittest.TestCase
):

    def test_exactly_one_model_invocation(
        self,
    ):
        model = CountingModel(
            [
                1.0,
                0.0,
            ]
        )

        model.eval()

        window = torch.zeros(
            (
                1,
                40,
                9,
            ),
            dtype=torch.float32,
        )

        decision = run_reliability_window(
            model,
            window,
            empty_assessment(),
        )

        self.assertEqual(
            model.calls,
            1,
        )

        self.assertEqual(
            decision.trust_state,
            TrustState.VALID,
        )

    def test_model_invocation_runs_under_inference_mode(
        self,
    ):
        model = CountingModel(
            [
                1.0,
                0.0,
            ]
        )

        model.eval()

        window = torch.zeros(
            (
                1,
                40,
                9,
            ),
            dtype=torch.float32,
        )

        run_reliability_window(
            model,
            window,
            empty_assessment(),
        )

        self.assertFalse(
            model.grad_enabled_during_call
        )

        self.assertTrue(
            model.inference_mode_during_call
        )

    def test_model_must_already_be_eval_mode(
        self,
    ):
        model = CountingModel(
            [
                1.0,
                0.0,
            ]
        )

        self.assertTrue(
            model.training
        )

        window = torch.zeros(
            (
                1,
                40,
                9,
            ),
            dtype=torch.float32,
        )

        with self.assertRaises(
            RuntimeContractViolation
        ):
            run_reliability_window(
                model,
                window,
                empty_assessment(),
            )

        self.assertEqual(
            model.calls,
            0,
        )

    def test_exact_window_shape_required(
        self,
    ):
        model = CountingModel(
            [
                1.0,
                0.0,
            ]
        )

        model.eval()

        for shape in (
            (
                40,
                9,
            ),
            (
                1,
                30,
                9,
            ),
            (
                2,
                40,
                9,
            ),
            (
                1,
                40,
                6,
            ),
        ):
            window = torch.zeros(
                shape,
                dtype=torch.float32,
            )

            with self.assertRaises(
                RuntimeContractViolation
            ):
                run_reliability_window(
                    model,
                    window,
                    empty_assessment(),
                )

        self.assertEqual(
            model.calls,
            0,
        )

    def test_integrity_alert_still_runs_task_model_once(
        self,
    ):
        model = CountingModel(
            [
                0.0,
                math.log(
                    19.0
                ),
            ]
        )

        model.eval()

        window = torch.zeros(
            (
                1,
                40,
                9,
            ),
            dtype=torch.float32,
        )

        decision = run_reliability_window(
            model,
            window,
            frame_gap_assessment(),
        )

        self.assertEqual(
            model.calls,
            1,
        )

        self.assertEqual(
            decision.trust_state,
            TrustState.INTEGRITY_ALERT,
        )

        self.assertEqual(
            decision.task_prediction,
            1,
        )


class StaticRuntimeContractTests(
    unittest.TestCase
):

    def test_integrated_wrapper_has_one_model_call_site(
        self,
    ):
        source = RELIABILITY_SOURCE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source
        )

        model_calls = []

        for node in ast.walk(
            tree
        ):
            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            if (
                isinstance(
                    node.func,
                    ast.Name,
                )
                and node.func.id
                == "model"
            ):
                model_calls.append(
                    node
                )

        self.assertEqual(
            len(
                model_calls
            ),
            1,
        )

    def test_no_forward_with_features_in_runtime(
        self,
    ):
        combined = (
            DECISION_SOURCE.read_text(
                encoding="utf-8"
            )
            + "\n"
            + RELIABILITY_SOURCE.read_text(
                encoding="utf-8"
            )
        )

        self.assertNotIn(
            "forward_with_features",
            combined,
        )

    def test_no_threshold_override_parameter(
        self,
    ):
        source = DECISION_SOURCE.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source
        )

        target = None

        for node in tree.body:
            if (
                isinstance(
                    node,
                    ast.FunctionDef,
                )
                and node.name
                == "decide_from_logits"
            ):
                target = node
                break

        self.assertIsNotNone(
            target
        )

        names = [
            arg.arg
            for arg in target.args.args
        ]

        self.assertEqual(
            names,
            [
                "logits",
                "integrity_assessment",
            ],
        )

    def test_runtime_does_not_create_integrity_evidence(
        self,
    ):
        combined = (
            DECISION_SOURCE.read_text(
                encoding="utf-8"
            )
            + "\n"
            + RELIABILITY_SOURCE.read_text(
                encoding="utf-8"
            )
        )

        self.assertNotIn(
            "IntegrityEvidence(",
            combined,
        )

        self.assertNotIn(
            "observe_frame_counter(",
            combined,
        )

        self.assertNotIn(
            "evaluate_timing_envelope(",
            combined,
        )

        self.assertNotIn(
            "ChannelFreezeMonitor(",
            combined,
        )


if __name__ == "__main__":
    unittest.main()
