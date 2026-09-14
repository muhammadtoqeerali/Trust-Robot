
import numpy as np


def apply_sensor_drift(
    X,
    bias_scale=0.1,
    seed=42
):

    """
    Simulate IMU calibration drift.

    Adds constant sensor bias
    to each channel.

    Parameters
    ----------
    X:
        IMU windows
        (N,128,6)

    bias_scale:
        drift magnitude

    seed:
        reproducibility


    Returns
    -------
    corrupted_X,
    metadata
    """


    rng=np.random.default_rng(
        seed
    )


    channels=X.shape[-1]


    bias=rng.normal(
        0,
        bias_scale,
        channels
    )


    corrupted=(
        X + bias
    ).astype(
        "float32"
    )


    metadata={

        "corruption":
            "sensor_drift",

        "bias_scale":
            float(bias_scale),

        "bias":
            bias.tolist(),

        "seed":
            seed

    }


    return corrupted,metadata
