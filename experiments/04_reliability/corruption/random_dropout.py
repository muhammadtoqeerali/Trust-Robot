
import numpy as np


def apply_random_dropout(
    X,
    drop_ratio=0.1,
    seed=42
):

    """
    Temporal IMU packet dropout simulation.

    Parameters
    ----------
    X:
        numpy array
        shape:
        (windows, samples, channels)

    drop_ratio:
        fraction of temporal samples removed

    seed:
        reproducibility seed


    Returns
    -------
    corrupted_X,
    metadata
    """


    rng=np.random.default_rng(
        seed
    )


    corrupted=X.copy()


    n_windows,n_samples,n_channels = corrupted.shape


    total_points = (
        n_windows*n_samples
    )


    mask = rng.random(
        (
            n_windows,
            n_samples
        )
    )


    dropout_mask = (
        mask < drop_ratio
    )


    for c in range(n_channels):

        corrupted[:,:,c][dropout_mask]=0



    metadata={

        "corruption":
            "random_dropout",

        "drop_ratio":
            float(drop_ratio),

        "seed":
            seed,

        "dropped_samples":
            int(
                dropout_mask.sum()
            ),

        "total_samples":
            int(
                total_points
            )

    }


    return corrupted, metadata
