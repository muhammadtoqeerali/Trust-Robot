import numpy as np
import torch

from torch.utils.data import Dataset

from engine.corruption_engine_v2 import (
    apply_corruption_v2
)


class ReliabilityDatasetV2(
    Dataset
):

    def __init__(
        self,
        base_dataset,
        corruption,
        *,
        corruption_seed=42,
        channel=None,
        drop_ratio=None,
        snr_db=None,
        bias_scale=None,
        channel_std=None
    ):

        if not hasattr(
            base_dataset,
            "tensors"
        ):

            raise TypeError(
                "ReliabilityDatasetV2 requires "
                "a TensorDataset-like object "
                "with a .tensors attribute"
            )


        if len(
            base_dataset.tensors
        ) < 2:

            raise ValueError(
                "Base dataset must contain "
                "input and label tensors"
            )


        self.x = (
            base_dataset
            .tensors[
                0
            ]
        )

        self.y = (
            base_dataset
            .tensors[
                1
            ]
        )


        if self.x.ndim != 3:

            raise ValueError(
                "Expected base input tensor "
                "[samples, time, channels], "
                f"got {tuple(self.x.shape)}"
            )


        self.corruption = (
            corruption
        )

        self.corruption_seed = int(
            corruption_seed
        )

        self.channel = (
            channel
        )

        self.drop_ratio = (
            drop_ratio
        )

        self.snr_db = (
            snr_db
        )

        self.bias_scale = (
            bias_scale
        )


        if channel_std is None:

            self.channel_std = (
                self.x
                .float()
                .std(
                    dim=(
                        0,
                        1
                    ),
                    unbiased=False
                )
                .detach()
                .cpu()
                .numpy()
                .astype(
                    np.float64,
                    copy=True
                )
            )

        else:

            self.channel_std = np.asarray(
                channel_std,
                dtype=np.float64
            ).copy()


        expected_shape = (
            self.x.shape[
                2
            ],
        )


        if (
            self.channel_std.shape
            !=
            expected_shape
        ):

            raise ValueError(
                "channel_std must have shape "
                f"{expected_shape}, "
                f"got {self.channel_std.shape}"
            )


    def __len__(
        self
    ):

        return len(
            self.y
        )


    def __getitem__(
        self,
        idx
    ):

        idx = int(
            idx
        )


        clean = (
            self.x[
                idx
            ]
            .detach()
            .cpu()
            .numpy()
            .copy()
        )


        corrupted = apply_corruption_v2(

            clean,

            self.corruption,

            sample_index=idx,

            seed=self.corruption_seed,

            channel=self.channel,

            drop_ratio=self.drop_ratio,

            snr_db=self.snr_db,

            bias_scale=self.bias_scale,

            channel_std=self.channel_std
        )


        x_corrupt = torch.from_numpy(

            np.asarray(
                corrupted,
                dtype=np.float32
            ).copy()

        )


        metadata = {

            "protocol_version":
                "v2",

            "corruption":
                self.corruption,

            "corruption_seed":
                self.corruption_seed,

            "sample_index":
                idx
        }


        if self.channel is not None:

            metadata[
                "channel"
            ] = int(
                self.channel
            )


        if self.drop_ratio is not None:

            metadata[
                "drop_ratio"
            ] = float(
                self.drop_ratio
            )


        if self.snr_db is not None:

            metadata[
                "snr_db"
            ] = float(
                self.snr_db
            )


        if self.bias_scale is not None:

            metadata[
                "bias_scale"
            ] = float(
                self.bias_scale
            )


        return (

            x_corrupt,

            self.y[
                idx
            ],

            metadata

        )
