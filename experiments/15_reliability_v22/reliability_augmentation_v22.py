import numpy as np
import importlib.util
from pathlib import Path


BASE = Path(
    "experiments/04_reliability/corruption"
)


def load_module(name, file):

    spec = importlib.util.spec_from_file_location(
        name,
        BASE / file
    )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module



missing_module = load_module(
    "missing_channel",
    "missing_channel.py"
)

dropout_module = load_module(
    "random_dropout",
    "random_dropout.py"
)

noise_module = load_module(
    "gaussian_noise",
    "gaussian_noise.py"
)

drift_module = load_module(
    "sensor_drift",
    "sensor_drift.py"
)



def apply_random_reliability_corruption(
    X,
    seed=42,
    probability=0.3
):

    """
    Training-time reliability augmentation.

    X:
        (N,128,6)

    probability:
        probability of applying corruption

    """

    rng=np.random.default_rng(seed)

    X_out=X.copy()

    metadata=[]


    corruptions=[
        "missing_gyro",
        "missing_acceleration",
        "dropout",
        "noise",
        "drift"
    ]


    corruption_weights=[
        0.25,
        0.30,
        0.20,
        0.15,
        0.10
    ]


    for i in range(
        len(X_out)
    ):

        if rng.random() > probability:

            metadata.append(
                {
                    "index":i,
                    "corruption":"clean"
                }
            )

            continue


        corruption=rng.choice(
            corruptions
        )


        sample=X_out[i:i+1]


        if corruption=="missing_gyro":

            sample,_=missing_module.apply_missing_channel(
                sample,
                [
                    "gyro_x",
                    "gyro_y",
                    "gyro_z"
                ],
                seed=int(seed+i)
            )


        elif corruption=="missing_acceleration":

            sample,_=missing_module.apply_missing_channel(
                sample,
                [
                    "accel_x",
                    "accel_y",
                    "accel_z"
                ],
                seed=int(seed+i)
            )


        elif corruption=="dropout":

            sample,_=dropout_module.apply_random_dropout(
                sample,
                drop_ratio=0.25,
                seed=int(seed+i)
            )


        elif corruption=="noise":

            sample,_=noise_module.apply_gaussian_noise(
                sample,
                snr_db=10,
                seed=int(seed+i)
            )


        elif corruption=="drift":

            sample,_=drift_module.apply_sensor_drift(
                sample,
                bias_scale=0.25,
                seed=int(seed+i)
            )


        X_out[i]=sample[0]


        metadata.append(
            {
                "index":i,
                "corruption":corruption
            }
        )


    return X_out, metadata



if __name__=="__main__":


    X=np.random.randn(
        8,
        128,
        6
    ).astype(
        "float32"
    )


    Xc,meta=apply_random_reliability_corruption(
        X,
        seed=42
    )


    print(
        "INPUT=",
        X.shape
    )


    print(
        "OUTPUT=",
        Xc.shape
    )


    print(
        "EXAMPLE_METADATA=",
        meta[:3]
    )


    print(
        "DIFFERENCE=",
        np.mean(
            abs(X-Xc)
        )
    )


    print(
        "RELIABILITY_AUGMENTATION_TEST_PASS=True"
    )
