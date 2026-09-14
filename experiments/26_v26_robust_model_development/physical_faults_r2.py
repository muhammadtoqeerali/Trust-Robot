from __future__ import annotations

import math

import torch


FAMILIES = [
    "modality_outage",
    "single_axis_outage",
    "intermittent_dropout",
    "gaussian_noise",
    "stuck_value",
    "scale_drift",
]


def _rand_scalar(
    generator,
):

    return float(
        torch.rand(
            (),
            generator=generator,
        ).item()
    )


def _random_modality(
    generator,
):

    pick = int(
        torch.randint(
            low=0,
            high=2,
            size=(1,),
            generator=generator,
        ).item()
    )


    if pick == 0:

        return (
            "accelerometer",
            [0, 1, 2],
        )


    return (
        "gyroscope",
        [3, 4, 5],
    )


def apply_random_physical_faults(
    raw_batch,
    train_std,
    generator,
    forced_family=None,
):

    if raw_batch.ndim != 3:

        raise ValueError(
            "raw_batch must be [B,T,6]"
        )


    if raw_batch.shape[-1] != 6:

        raise ValueError(
            "raw_batch must have six channels"
        )


    if raw_batch.device.type != "cpu":

        raise ValueError(
            "Frozen R2 physical training operator "
            "runs on CPU before normalization/GPU transfer"
        )


    if train_std.shape != (6,):

        raise ValueError(
            "train_std must have shape [6]"
        )


    if forced_family is not None:

        if forced_family not in FAMILIES:

            raise KeyError(
                forced_family
            )


    original = raw_batch

    out = raw_batch.clone()

    batch_size = out.shape[0]
    time_steps = out.shape[1]

    metadata = []


    for i in range(
        batch_size
    ):

        if forced_family is None:

            family_index = int(
                torch.randint(
                    low=0,
                    high=len(FAMILIES),
                    size=(1,),
                    generator=generator,
                ).item()
            )

            family = FAMILIES[
                family_index
            ]

        else:

            family = forced_family


        entry = {
            "sample_index":
                i,

            "family":
                family,
        }


        if family == "modality_outage":

            modality, channels = (
                _random_modality(
                    generator
                )
            )

            out[
                i,
                :,
                channels,
            ] = 0.0

            entry.update({
                "modality":
                    modality,

                "channels":
                    channels,
            })


        elif family == "single_axis_outage":

            channel = int(
                torch.randint(
                    low=0,
                    high=6,
                    size=(1,),
                    generator=generator,
                ).item()
            )

            out[
                i,
                :,
                channel,
            ] = 0.0

            entry.update({
                "channel":
                    channel,
            })


        elif family == "intermittent_dropout":

            modality, channels = (
                _random_modality(
                    generator
                )
            )

            probability = (
                0.10
                +
                0.40
                *
                _rand_scalar(
                    generator
                )
            )

            mask = (
                torch.rand(
                    (
                        time_steps,
                    ),
                    generator=generator,
                )
                <
                probability
            )


            for channel in channels:

                out[
                    i,
                    mask,
                    channel,
                ] = 0.0


            entry.update({
                "modality":
                    modality,

                "channels":
                    channels,

                "drop_probability":
                    probability,

                "dropped_time_steps":
                    int(
                        mask.sum().item()
                    ),
            })


        elif family == "gaussian_noise":

            modality, channels = (
                _random_modality(
                    generator
                )
            )

            sigma_units = (
                0.10
                +
                0.60
                *
                _rand_scalar(
                    generator
                )
            )


            epsilon = torch.randn(
                (
                    time_steps,
                    len(channels),
                ),
                generator=generator,
                dtype=out.dtype,
            )


            scale = (
                sigma_units
                *
                train_std[
                    channels
                ].reshape(
                    1,
                    -1,
                )
            )


            out[
                i,
                :,
                channels,
            ] += (
                epsilon
                *
                scale
            )


            entry.update({
                "modality":
                    modality,

                "channels":
                    channels,

                "sigma_normalized_units":
                    sigma_units,
            })


        elif family == "stuck_value":

            modality, channels = (
                _random_modality(
                    generator
                )
            )

            onset_fraction = (
                0.20
                +
                0.60
                *
                _rand_scalar(
                    generator
                )
            )

            onset = int(
                math.floor(
                    onset_fraction
                    *
                    time_steps
                )
            )

            onset = min(
                max(
                    onset,
                    0,
                ),
                time_steps - 1,
            )


            stuck_value = out[
                i,
                onset,
                channels,
            ].clone()


            tail = out[
                i,
                onset:,
                :,
            ]

            tail[
                :,
                channels,
            ] = stuck_value.reshape(
                1,
                -1,
            )


            entry.update({
                "modality":
                    modality,

                "channels":
                    channels,

                "onset_fraction":
                    onset_fraction,

                "onset_index":
                    onset,
            })


        elif family == "scale_drift":

            modality, channels = (
                _random_modality(
                    generator
                )
            )

            final_factor = (
                0.50
                +
                1.50
                *
                _rand_scalar(
                    generator
                )
            )


            factor = torch.linspace(
                1.0,
                final_factor,
                time_steps,
                dtype=out.dtype,
            )


            for channel in channels:

                out[
                    i,
                    :,
                    channel,
                ] *= factor


            entry.update({
                "modality":
                    modality,

                "channels":
                    channels,

                "start_factor":
                    1.0,

                "final_factor":
                    final_factor,
            })


        else:

            raise RuntimeError(
                family
            )


        metadata.append(
            entry
        )


    if not torch.equal(
        raw_batch,
        original,
    ):

        raise RuntimeError(
            "Input tensor modified in place"
        )


    return (
        out,
        metadata,
    )


def normalize_with_train_stats(
    raw_batch,
    train_mean,
    train_std,
):

    return (
        raw_batch
        -
        train_mean.reshape(
            1,
            1,
            6,
        )
    ) / train_std.reshape(
        1,
        1,
        6,
    )
