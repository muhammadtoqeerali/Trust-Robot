
import numpy as np


def apply_gaussian_noise(
    X,
    snr_db=20,
    seed=42
):

    """
    Gaussian sensor noise injection.

    Parameters
    ----------
    X:
        IMU windows
        shape:
        (N,128,6)

    snr_db:
        desired signal-to-noise ratio

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


    signal_power=np.mean(
        X**2
    )


    snr_linear=10**(
        snr_db/10
    )


    noise_power=(
        signal_power /
        snr_linear
    )


    noise_std=np.sqrt(
        noise_power
    )


    noise=rng.normal(
        0,
        noise_std,
        X.shape
    )


    corrupted=(
        X + noise
    ).astype(
        "float32"
    )


    metadata={

        "corruption":
            "gaussian_noise",

        "snr_db":
            float(snr_db),

        "noise_std":
            float(noise_std),

        "seed":
            seed

    }


    return corrupted, metadata
