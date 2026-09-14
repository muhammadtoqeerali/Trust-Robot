import torch

from imu_reliability.baseline.historical_decision import (
    decision_from_probabilities,
)


def test_historical_examples():
    p = torch.tensor(
        [
            [0.95, 0.05],  # confident Activity
            [0.05, 0.95],  # confident Falling
            [0.20, 0.80],  # uncertain Falling -> Activity
            [0.80, 0.20],  # uncertain Activity -> Activity
            [0.10, 0.90],  # exactly threshold -> Activity
        ],
        dtype=torch.float64,
    )

    got = decision_from_probabilities(
        p,
        prediction_bias=0.9,
    )

    expected = torch.tensor(
        [0, 1, 0, 0, 0],
        dtype=torch.long,
    )

    assert torch.equal(got, expected)


def test_binary_simplification():
    p_fall = torch.tensor(
        [
            0.01,
            0.49,
            0.50,
            0.89,
            0.90,
            0.9000001,
            0.99,
        ],
        dtype=torch.float64,
    )

    p = torch.stack(
        [
            1.0 - p_fall,
            p_fall,
        ],
        dim=1,
    )

    historical = decision_from_probabilities(
        p,
        prediction_bias=0.9,
    )

    simplified = (
        p_fall > 0.9
    ).to(torch.long)

    assert torch.equal(
        historical,
        simplified,
    )
