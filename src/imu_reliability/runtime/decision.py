from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import torch

from imu_reliability.baseline.historical_decision import (
    decision_from_logits,
)
from imu_reliability.integrity import (
    IntegrityAssessment,
    IntegrityCause,
    SuspectIndicator,
)


OOD_THRESHOLD = 0.00914505124092102

SUPPORTED_HARD_CAUSE_MASK = (
    IntegrityCause.FRAME_GAP
)


class RuntimeContractViolation(
    RuntimeError
):
    """
    Raised when runtime inputs would violate the frozen V1 contract.

    This is deliberately different from a reliability trust state.
    Unsupported evidence must not be silently promoted, suppressed,
    or reinterpreted as VALID/OOD_UNKNOWN/INTEGRITY_ALERT.
    """


class TrustState(
    str,
    Enum,
):
    VALID = "VALID"
    OOD_UNKNOWN = "OOD_UNKNOWN"
    INTEGRITY_ALERT = "INTEGRITY_ALERT"


@dataclass(
    frozen=True
)
class ReliabilityDecision:
    task_prediction: int
    trust_state: TrustState

    integrity_cause_mask: IntegrityCause
    hard_causes: frozenset[IntegrityCause]
    suspects: frozenset[SuspectIndicator]

    ood_margin: float
    ood_threshold: float

    @property
    def has_integrity_alert(
        self,
    ) -> bool:
        return (
            self.trust_state
            is TrustState.INTEGRITY_ALERT
        )


def _validate_logits(
    logits: torch.Tensor,
) -> None:
    if not isinstance(
        logits,
        torch.Tensor,
    ):
        raise TypeError(
            "logits must be a torch.Tensor"
        )

    if tuple(
        logits.shape
    ) != (
        1,
        2,
    ):
        raise RuntimeContractViolation(
            "Frozen reference runtime expects exactly "
            "one binary-model output with shape (1, 2); "
            f"got {tuple(logits.shape)}"
        )


def _validate_integrity_assessment(
    assessment: IntegrityAssessment,
) -> None:
    if not isinstance(
        assessment,
        IntegrityAssessment,
    ):
        raise TypeError(
            "integrity_assessment must be IntegrityAssessment"
        )

    reconstructed_mask = (
        IntegrityCause.NONE
    )

    for cause in assessment.hard_causes:
        if not isinstance(
            cause,
            IntegrityCause,
        ):
            raise RuntimeContractViolation(
                "IntegrityAssessment contains a non-IntegrityCause "
                "hard-cause entry"
            )

        reconstructed_mask |= cause

    if (
        reconstructed_mask
        != assessment.cause_mask
    ):
        raise RuntimeContractViolation(
            "IntegrityAssessment hard_causes and cause_mask disagree"
        )

    unsupported_bits = (
        int(
            assessment.cause_mask
        )
        & ~int(
            SUPPORTED_HARD_CAUSE_MASK
        )
    )

    if unsupported_bits:
        raise RuntimeContractViolation(
            "Frozen runtime V1 supports only FRAME_GAP as a "
            "hard external integrity cause; "
            f"unsupported hard-cause bits={unsupported_bits}"
        )


def decide_from_logits(
    logits: torch.Tensor,
    integrity_assessment: IntegrityAssessment,
) -> ReliabilityDecision:
    """
    Apply the frozen runtime decision to logits from one task forward.

    This function does not invoke the model.

    Precedence:
      1. supported qualified hard integrity cause -> INTEGRITY_ALERT
      2. otherwise margin < frozen threshold      -> OOD_UNKNOWN
      3. otherwise                                -> VALID

    The historical task prediction is always computed and returned.
    """
    _validate_logits(
        logits
    )

    _validate_integrity_assessment(
        integrity_assessment
    )

    task_prediction_tensor = (
        decision_from_logits(
            logits
        )
    )

    task_prediction = int(
        task_prediction_tensor[
            0
        ]
        .detach()
        .cpu()
        .item()
    )

    margin = float(
        torch.abs(
            logits[
                0,
                0
            ]
            - logits[
                0,
                1
            ]
        )
        .detach()
        .cpu()
        .item()
    )

    if (
        integrity_assessment
        .has_hard_alert
    ):
        trust_state = (
            TrustState.INTEGRITY_ALERT
        )

    elif margin < OOD_THRESHOLD:
        trust_state = (
            TrustState.OOD_UNKNOWN
        )

    else:
        trust_state = (
            TrustState.VALID
        )

    return ReliabilityDecision(
        task_prediction=task_prediction,
        trust_state=trust_state,
        integrity_cause_mask=(
            integrity_assessment
            .cause_mask
        ),
        hard_causes=(
            integrity_assessment
            .hard_causes
        ),
        suspects=(
            integrity_assessment
            .suspects
        ),
        ood_margin=margin,
        ood_threshold=OOD_THRESHOLD,
    )
