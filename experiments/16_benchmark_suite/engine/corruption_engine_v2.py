import numpy as np


EPS = 1e-12


def _window(x):

    x = np.asarray(x)

    if x.ndim != 2:

        raise ValueError(
            "Expected one IMU window [time, channels], "
            f"got {x.shape}"
        )

    return x


def _rng(
    seed,
    sample_index
):

    sequence = np.random.SeedSequence(
        [
            int(seed),
            int(sample_index)
        ]
    )

    return np.random.default_rng(
        sequence
    )


def apply_missing_channel_v2(
    x,
    channel
):

    x = _window(x).copy()

    channel = int(channel)

    if (
        channel < 0
        or
        channel >= x.shape[1]
    ):

        raise ValueError(
            f"Invalid channel {channel}"
        )

    x[:, channel] = 0

    return x


def apply_random_dropout_v2(
    x,
    drop_ratio,
    seed,
    sample_index
):

    x = _window(x).copy()

    ratio = float(drop_ratio)

    if not (
        0 <= ratio <= 1
    ):

        raise ValueError(
            "drop_ratio must be in [0,1]"
        )

    n_time = x.shape[0]

    n_drop = int(
        round(
            n_time *
            ratio
        )
    )

    if n_drop == 0:

        return x

    rng = _rng(
        seed,
        sample_index
    )

    indices = rng.choice(
        n_time,
        size=n_drop,
        replace=False
    )

    # Temporal packet/sample loss:
    # selected time steps disappear for all channels.
    x[indices, :] = 0

    return x


def apply_gaussian_noise_v2(
    x,
    snr_db,
    seed,
    sample_index
):

    original = _window(x)

    work = original.astype(
        np.float64,
        copy=True
    )

    rng = _rng(
        seed,
        sample_index
    )

    noise = rng.normal(
        0.0,
        1.0,
        size=work.shape
    )

    signal_power = np.mean(
        work ** 2,
        axis=0,
        keepdims=True
    )

    raw_noise_power = np.mean(
        noise ** 2,
        axis=0,
        keepdims=True
    )

    target_noise_power = (
        signal_power
        /
        (
            10.0 **
            (
                float(snr_db)
                /
                10.0
            )
        )
    )

    scale = np.sqrt(
        target_noise_power
        /
        np.maximum(
            raw_noise_power,
            EPS
        )
    )

    scale = np.where(
        signal_power > EPS,
        scale,
        0.0
    )

    corrupted = (
        work
        +
        noise *
        scale
    )

    return corrupted.astype(
        original.dtype,
        copy=False
    )


def apply_sensor_drift_v2(
    x,
    bias_scale,
    seed,
    channel_std
):

    original = _window(x)

    work = original.astype(
        np.float64,
        copy=True
    )

    channel_std = np.asarray(
        channel_std,
        dtype=np.float64
    )

    if channel_std.shape != (
        work.shape[1],
    ):

        raise ValueError(
            "channel_std shape mismatch"
        )

    rng = np.random.default_rng(
        int(seed)
    )

    direction = rng.choice(
        np.array(
            [-1.0, 1.0]
        ),
        size=work.shape[1]
    )

    bias = (
        float(bias_scale)
        *
        channel_std
        *
        direction
    )

    corrupted = (
        work
        +
        bias[None, :]
    )

    return corrupted.astype(
        original.dtype,
        copy=False
    )


def apply_corruption_v2(
    x,
    corruption_name,
    *,
    sample_index,
    seed=42,
    channel=None,
    drop_ratio=None,
    snr_db=None,
    bias_scale=None,
    channel_std=None
):

    if corruption_name == "missing_channel":

        if channel is None:

            raise ValueError(
                "missing_channel requires channel"
            )

        return apply_missing_channel_v2(
            x,
            channel
        )


    if corruption_name == "random_dropout":

        if drop_ratio is None:

            raise ValueError(
                "random_dropout requires drop_ratio"
            )

        return apply_random_dropout_v2(
            x,
            drop_ratio,
            seed,
            sample_index
        )


    if corruption_name == "gaussian_noise":

        if snr_db is None:

            raise ValueError(
                "gaussian_noise requires snr_db"
            )

        return apply_gaussian_noise_v2(
            x,
            snr_db,
            seed,
            sample_index
        )


    if corruption_name == "sensor_drift":

        if (
            bias_scale is None
            or
            channel_std is None
        ):

            raise ValueError(
                "sensor_drift requires "
                "bias_scale and channel_std"
            )

        return apply_sensor_drift_v2(
            x,
            bias_scale,
            seed,
            channel_std
        )


    raise ValueError(
        f"Unknown corruption: {corruption_name}"
    )
