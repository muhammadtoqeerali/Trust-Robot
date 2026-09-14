import sys

import numpy as np
import torch

from torch.utils.data import (
    DataLoader,
    TensorDataset
)


sys.path.insert(
    0,
    "experiments/16_benchmark_suite"
)


from engine.reliability_dataset_v2 import (
    ReliabilityDatasetV2
)


def main():

    rng = np.random.default_rng(
        777
    )


    x_np = rng.normal(
        size=(
            12,
            128,
            6
        )
    ).astype(
        np.float32
    )


    y_np = np.arange(
        12,
        dtype=np.int64
    )


    base = TensorDataset(

        torch.from_numpy(
            x_np.copy()
        ),

        torch.from_numpy(
            y_np.copy()
        )

    )


    original_x = (
        base
        .tensors[
            0
        ]
        .clone()
    )


    original_y = (
        base
        .tensors[
            1
        ]
        .clone()
    )


    conditions = [

        (
            "missing_channel",
            {
                "channel":
                    2
            }
        ),

        (
            "random_dropout",
            {
                "drop_ratio":
                    0.25
            }
        ),

        (
            "gaussian_noise",
            {
                "snr_db":
                    10
            }
        ),

        (
            "sensor_drift",
            {
                "bias_scale":
                    0.25
            }
        )

    ]


    for corruption, kwargs in conditions:

        ds = ReliabilityDatasetV2(

            base,

            corruption,

            corruption_seed=42,

            **kwargs

        )


        for idx in range(
            len(
                ds
            )
        ):

            x_corrupt, y, metadata = ds[
                idx
            ]


            assert x_corrupt.shape == (
                128,
                6
            )


            assert (
                x_corrupt.dtype
                ==
                torch.float32
            )


            assert (
                y.item()
                ==
                idx
            )


            assert (
                metadata[
                    "protocol_version"
                ]
                ==
                "v2"
            )


            assert (
                metadata[
                    "sample_index"
                ]
                ==
                idx
            )


            assert (
                metadata[
                    "corruption"
                ]
                ==
                corruption
            )


    assert torch.equal(
        original_x,
        base.tensors[
            0
        ]
    )


    assert torch.equal(
        original_y,
        base.tensors[
            1
        ]
    )


    print(
        "V2_DATASET_CLEAN_IMMUTABILITY_PASS=True"
    )


    missing = ReliabilityDatasetV2(

        base,

        "missing_channel",

        channel=4,

        corruption_seed=42

    )


    missing_x, _, missing_meta = (
        missing[
            0
        ]
    )


    assert torch.all(
        missing_x[
            :,
            4
        ]
        ==
        0
    )


    for channel in [
        0,
        1,
        2,
        3,
        5
    ]:

        assert torch.equal(

            missing_x[
                :,
                channel
            ],

            original_x[
                0,
                :,
                channel
            ]

        )


    assert (
        missing_meta[
            "channel"
        ]
        ==
        4
    )


    print(
        "V2_DATASET_MISSING_CHANNEL_PASS=True"
    )


    gaussian = ReliabilityDatasetV2(

        base,

        "gaussian_noise",

        snr_db=10,

        corruption_seed=42

    )


    g0_a = gaussian[
        0
    ][
        0
    ]


    g0_b = gaussian[
        0
    ][
        0
    ]


    g1 = gaussian[
        1
    ][
        0
    ]


    assert torch.equal(
        g0_a,
        g0_b
    )


    noise0 = (
        g0_a
        -
        original_x[
            0
        ]
    )


    noise1 = (
        g1
        -
        original_x[
            1
        ]
    )


    assert not torch.equal(
        noise0,
        noise1
    )


    gaussian_other_seed = (
        ReliabilityDatasetV2(

            base,

            "gaussian_noise",

            snr_db=10,

            corruption_seed=123

        )
    )


    g0_other_seed = (
        gaussian_other_seed[
            0
        ][
            0
        ]
    )


    assert not torch.equal(
        g0_a,
        g0_other_seed
    )


    print(
        "V2_DATASET_GAUSSIAN_REPRODUCIBILITY_PASS=True"
    )


    dropout = ReliabilityDatasetV2(

        base,

        "random_dropout",

        drop_ratio=0.25,

        corruption_seed=42

    )


    d0_a = dropout[
        0
    ][
        0
    ]


    d0_b = dropout[
        0
    ][
        0
    ]


    d1 = dropout[
        1
    ][
        0
    ]


    assert torch.equal(
        d0_a,
        d0_b
    )


    mask0 = torch.all(
        d0_a == 0,
        dim=1
    )


    mask1 = torch.all(
        d1 == 0,
        dim=1
    )


    assert int(
        mask0.sum()
    ) == 32


    assert int(
        mask1.sum()
    ) == 32


    assert not torch.equal(
        mask0,
        mask1
    )


    print(
        "V2_DATASET_DROPOUT_REPRODUCIBILITY_PASS=True"
    )


    drift = ReliabilityDatasetV2(

        base,

        "sensor_drift",

        bias_scale=0.25,

        corruption_seed=42

    )


    drift0 = drift[
        0
    ][
        0
    ]


    delta = (
        drift0
        -
        original_x[
            0
        ]
    )


    assert torch.allclose(

        delta,

        delta[
            0
        ][
            None,
            :
        ].expand_as(
            delta
        ),

        atol=1e-6,

        rtol=0

    )


    print(
        "V2_DATASET_SENSOR_DRIFT_PASS=True"
    )


    loader = DataLoader(

        gaussian,

        batch_size=4,

        shuffle=False

    )


    batch = next(
        iter(
            loader
        )
    )


    assert len(
        batch
    ) == 3


    batch_x = batch[
        0
    ]


    batch_y = batch[
        1
    ]


    assert batch_x.shape == (
        4,
        128,
        6
    )


    assert batch_y.shape == (
        4,
    )


    print(
        "V2_DATASET_DATALOADER_PASS=True"
    )


    assert torch.equal(
        original_x,
        base.tensors[
            0
        ]
    )


    print(
        "RELIABILITY_DATASET_V2_REGRESSION_PASS=True"
    )


if __name__ == "__main__":

    main()
