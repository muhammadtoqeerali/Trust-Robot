from __future__ import annotations

import hashlib

import numpy as np
import torch

from sklearn.metrics import (
    f1_score,
)

from torch.utils.data import (
    DataLoader,
    TensorDataset,
)


VALIDATION_ROOT_SEED = 26001


VALIDATION_CONDITIONS = [
    {
        "name":
            "acc_total_failure",

        "family":
            "modality_outage",

        "channels":
            [0, 1, 2],
    },

    {
        "name":
            "gyro_total_failure",

        "family":
            "modality_outage",

        "channels":
            [3, 4, 5],
    },

    *[
        {
            "name":
                f"single_axis_{channel}",

            "family":
                "single_axis_outage",

            "channels":
                [channel],
        }
        for channel in range(6)
    ],

    {
        "name":
            "acc_intermittent_30pct",

        "family":
            "intermittent_dropout",

        "channels":
            [0, 1, 2],

        "drop_probability":
            0.30,
    },

    {
        "name":
            "gyro_intermittent_30pct",

        "family":
            "intermittent_dropout",

        "channels":
            [3, 4, 5],

        "drop_probability":
            0.30,
    },

    {
        "name":
            "acc_noise_sigma0.5",

        "family":
            "gaussian_noise",

        "channels":
            [0, 1, 2],

        "sigma_normalized_units":
            0.50,
    },

    {
        "name":
            "gyro_noise_sigma0.5",

        "family":
            "gaussian_noise",

        "channels":
            [3, 4, 5],

        "sigma_normalized_units":
            0.50,
    },

    {
        "name":
            "acc_stuck_value",

        "family":
            "stuck_value",

        "channels":
            [0, 1, 2],
    },

    {
        "name":
            "gyro_stuck_value",

        "family":
            "stuck_value",

        "channels":
            [3, 4, 5],
    },

    {
        "name":
            "acc_scale_drift_2.0x",

        "family":
            "scale_drift",

        "channels":
            [0, 1, 2],

        "final_factor":
            2.0,
    },

    {
        "name":
            "gyro_scale_drift_2.0x",

        "family":
            "scale_drift",

        "channels":
            [3, 4, 5],

        "final_factor":
            2.0,
    },
]


def stable_seed(
    dataset,
    condition,
):

    payload = (
        f"{VALIDATION_ROOT_SEED}|"
        f"{dataset}|"
        f"{condition}"
    ).encode(
        "utf-8"
    )

    digest = hashlib.sha256(
        payload
    ).digest()

    return int.from_bytes(
        digest[:4],
        "little",
        signed=False,
    )


def normalize(
    raw,
    mean,
    std,
):

    return np.asarray(
        (
            raw
            -
            mean.reshape(
                1,
                1,
                6,
            )
        )
        /
        std.reshape(
            1,
            1,
            6,
        ),
        dtype=np.float32,
    )


def apply_validation_condition(
    raw,
    train_std,
    dataset,
    condition,
):

    out = np.array(
        raw,
        copy=True,
        dtype=np.float32,
    )

    family = condition[
        "family"
    ]

    channels = condition[
        "channels"
    ]

    rng = np.random.RandomState(
        stable_seed(
            dataset,
            condition[
                "name"
            ],
        )
    )


    if family in {
        "modality_outage",
        "single_axis_outage",
    }:

        out[
            :,
            :,
            channels,
        ] = 0.0


    elif family == "intermittent_dropout":

        mask = (
            rng.rand(
                out.shape[0],
                out.shape[1],
            )
            <
            float(
                condition[
                    "drop_probability"
                ]
            )
        )


        for channel in channels:

            view = out[
                :,
                :,
                channel,
            ]

            view[
                mask
            ] = 0.0


    elif family == "gaussian_noise":

        eps = rng.normal(
            0.0,
            1.0,
            size=(
                out.shape[0],
                out.shape[1],
                len(channels),
            ),
        ).astype(
            np.float32
        )

        sigma = float(
            condition[
                "sigma_normalized_units"
            ]
        )


        for local_i, channel in enumerate(
            channels
        ):

            out[
                :,
                :,
                channel,
            ] += (
                sigma
                *
                train_std[
                    channel
                ]
                *
                eps[
                    :,
                    :,
                    local_i,
                ]
            )


    elif family == "stuck_value":

        low = (
            out.shape[1]
            //
            4
        )

        high = (
            3
            *
            out.shape[1]
            //
            4
        )

        tau = rng.randint(
            low=low,
            high=high,
            size=out.shape[0],
        )


        for i in range(
            out.shape[0]
        ):

            t = int(
                tau[i]
            )

            stuck = np.asarray(
                out[
                    i,
                    t,
                    channels,
                ]
            ).copy()

            tail = out[
                i,
                t:,
                :,
            ]

            tail[
                :,
                channels,
            ] = stuck.reshape(
                1,
                -1,
            )


    elif family == "scale_drift":

        factors = np.linspace(
            1.0,
            float(
                condition[
                    "final_factor"
                ]
            ),
            out.shape[1],
            dtype=np.float32,
        )


        for channel in channels:

            out[
                :,
                :,
                channel,
            ] *= factors.reshape(
                1,
                -1,
            )


    else:

        raise KeyError(
            family
        )


    return out


def selection_score(
    clean_macro_f1,
    all_recoverable_macro_f1,
    family_balanced_macro_f1,
):

    return (
        0.20
        *
        clean_macro_f1
        +
        0.30
        *
        all_recoverable_macro_f1
        +
        0.50
        *
        family_balanced_macro_f1
    )


def _predict(
    model,
    X,
    y,
    device,
    batch_size,
):

    ds = TensorDataset(
        torch.from_numpy(
            np.asarray(
                X,
                dtype=np.float32,
            )
        ),
        torch.from_numpy(
            np.asarray(
                y,
                dtype=np.int64,
            )
        ),
    )

    loader = DataLoader(
        ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        drop_last=False,
    )


    prediction = []


    model.eval()


    with torch.inference_mode():

        for x, _ in loader:

            x = x.to(
                device
            )

            logits = model(
                x
            )

            prediction.extend(
                torch.argmax(
                    logits,
                    dim=1,
                )
                .cpu()
                .tolist()
            )


    return np.asarray(
        prediction,
        dtype=np.int64,
    )


def evaluate_validation_only(
    model,
    dataset,
    raw_val,
    y_val,
    train_mean,
    train_std,
    num_classes,
    device,
    batch_size=64,
):

    clean = normalize(
        raw_val,
        train_mean,
        train_std,
    )

    clean_pred = _predict(
        model,
        clean,
        y_val,
        device,
        batch_size,
    )

    clean_f1 = float(
        f1_score(
            y_val,
            clean_pred,
            labels=list(
                range(
                    num_classes
                )
            ),
            average="macro",
            zero_division=0,
        )
    )


    condition_rows = []


    for condition in VALIDATION_CONDITIONS:

        fault_raw = (
            apply_validation_condition(
                raw_val,
                train_std,
                dataset,
                condition,
            )
        )

        fault_norm = normalize(
            fault_raw,
            train_mean,
            train_std,
        )

        pred = _predict(
            model,
            fault_norm,
            y_val,
            device,
            batch_size,
        )

        macro_f1 = float(
            f1_score(
                y_val,
                pred,
                labels=list(
                    range(
                        num_classes
                    )
                ),
                average="macro",
                zero_division=0,
            )
        )


        condition_rows.append({
            "condition":
                condition[
                    "name"
                ],

            "family":
                condition[
                    "family"
                ],

            "macro_f1":
                macro_f1,
        })


    all_fault_f1 = float(
        np.mean(
            [
                row[
                    "macro_f1"
                ]
                for row in condition_rows
            ]
        )
    )


    families = {}


    for row in condition_rows:

        families.setdefault(
            row[
                "family"
            ],
            [],
        ).append(
            row[
                "macro_f1"
            ]
        )


    if len(
        families
    ) != 6:

        raise RuntimeError(
            "Validation family cardinality "
            "must be six"
        )


    family_balanced_f1 = float(
        np.mean(
            [
                np.mean(
                    values
                )
                for values in families.values()
            ]
        )
    )


    score = selection_score(
        clean_f1,
        all_fault_f1,
        family_balanced_f1,
    )


    return {
        "clean_macro_f1":
            clean_f1,

        "all_recoverable_fault_macro_f1":
            all_fault_f1,

        "family_balanced_macro_f1":
            family_balanced_f1,

        "selection_score":
            score,

        "condition_rows":
            condition_rows,
    }
