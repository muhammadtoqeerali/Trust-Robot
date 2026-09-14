from __future__ import annotations

import torch


HISTORICAL_PREDICTION_BIAS = 0.9
ACTIVITY_CLASS = 0
FALLING_CLASS = 1


def decision_from_probabilities(
    probabilities: torch.Tensor,
    prediction_bias: float = HISTORICAL_PREDICTION_BIAS,
) -> torch.Tensor:
    """
    Exact recovered Simulator.get_output semantics.

    Historical rule:
        output defaults to class 0
        if max(probabilities) > prediction_bias:
            output = argmax(probabilities)

    For the binary historical model with prediction_bias=0.9,
    this is equivalent to:
        Falling iff P(Falling) > 0.9
        Activity otherwise

    The comparison is intentionally strict (>).
    """
    if probabilities.ndim != 2:
        raise ValueError(
            f"Expected [B,C], got {tuple(probabilities.shape)}"
        )

    max_prob, argmax_class = probabilities.max(dim=1)

    output = torch.zeros(
        probabilities.shape[0],
        dtype=torch.long,
        device=probabilities.device,
    )

    accepted = max_prob > prediction_bias

    output[accepted] = argmax_class[accepted]

    return output


def decision_from_logits(
    logits: torch.Tensor,
    prediction_bias: float = HISTORICAL_PREDICTION_BIAS,
) -> torch.Tensor:
    """
    Historical deployment-style decision from task logits.

    This consumes logits already produced by the single protected-model
    forward pass. It does not invoke the task model again.
    """
    probabilities = torch.softmax(
        logits,
        dim=1,
    )

    return decision_from_probabilities(
        probabilities,
        prediction_bias=prediction_bias,
    )
