import numpy as np



def apply_missing_channel(
    x,
    channel=0
):

    x=x.copy()

    x[:,:,channel]=0

    return x



def apply_random_dropout(
    x,
    probability=0.1,
    seed=42
):

    rng=np.random.default_rng(
        seed
    )


    mask=rng.random(
        x.shape
    ) < probability


    x=x.copy()

    x[mask]=0


    return x



def apply_gaussian_noise(
    x,
    sigma=0.05,
    seed=42
):

    rng=np.random.default_rng(
        seed
    )


    noise=rng.normal(
        0,
        sigma,
        size=x.shape
    )


    return (
        x+noise
    )



def apply_sensor_drift(
    x,
    drift_strength=0.1
):

    x=x.copy()


    time=np.arange(
        x.shape[1]
    )


    drift=(
        drift_strength *
        time /
        len(time)
    )


    x=x + drift[None,:,None]


    return x




def apply_corruption(
    x,
    corruption_name,
    seed=42,
    **kwargs
):


    if corruption_name=="missing_channel":

        return apply_missing_channel(
            x,
            **kwargs
        )


    if corruption_name=="random_dropout":

        return apply_random_dropout(
            x,
            seed=seed,
            **kwargs
        )


    if corruption_name=="gaussian_noise":

        return apply_gaussian_noise(
            x,
            seed=seed,
            **kwargs
        )


    if corruption_name=="sensor_drift":

        return apply_sensor_drift(
            x,
            **kwargs
        )


    raise ValueError(
        f"Unknown corruption {corruption_name}"
    )
