from __future__ import annotations

import torch

from imu_reliability.integrity import (
    IntegrityAssessment,
)

from .decision import (
    ReliabilityDecision,
    RuntimeContractViolation,
    decide_from_logits,
)


EXPECTED_WINDOW_SHAPE = (
    1,
    40,
    9,
)


def run_reliability_window(
    model,
    window: torch.Tensor,
    integrity_assessment: IntegrityAssessment,
) -> ReliabilityDecision:
    """
    Execute the frozen reference reliability wrapper for one 400-ms window.

    Exactly one full task-model invocation is performed:
        logits = model(window)

    OOD uses those same logits. No feature-vector extraction and no
    second task-model forward are performed.
    """
    if not isinstance(
        window,
        torch.Tensor,
    ):
        raise TypeError(
            "window must be a torch.Tensor"
        )

    if tuple(
        window.shape
    ) != EXPECTED_WINDOW_SHAPE:
        raise RuntimeContractViolation(
            "Frozen reference runtime expects input shape "
            f"{EXPECTED_WINDOW_SHAPE}; "
            f"got {tuple(window.shape)}"
        )

    training = getattr(
        model,
        "training",
        None,
    )

    if training is not False:
        raise RuntimeContractViolation(
            "Protected task model must already be in inference/eval mode"
        )

    with torch.inference_mode():
        logits = model(
            window
        )

    return decide_from_logits(
        logits,
        integrity_assessment,
    )
