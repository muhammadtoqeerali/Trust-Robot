
import numpy as np


CHANNELS = [
    "accel_x",
    "accel_y",
    "accel_z",
    "gyro_x",
    "gyro_y",
    "gyro_z"
]


def apply_missing_channel(
    X,
    channels,
    seed=42
):

    """
    Simulate complete IMU channel failure.

    X:
        (N,128,6)

    channels:
        list of channel names to remove
    """

    X_corrupted = X.copy()


    rng = np.random.default_rng(seed)


    indices = [
        CHANNELS.index(c)
        for c in channels
    ]


    X_corrupted[
        :,
        :,
        indices
    ] = 0.0


    metadata = {

        "corruption":
            "missing_channel",

        "channels_removed":
            channels,

        "channel_indices":
            indices,

        "seed":
            seed

    }


    return X_corrupted, metadata
