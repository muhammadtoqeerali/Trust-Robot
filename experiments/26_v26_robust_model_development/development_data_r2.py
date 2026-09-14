from __future__ import annotations

from pathlib import Path

import numpy as np


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

DATA_ROOT = (
    ROOT
    / "data"
    / "processed"
    / "harmonized"
)

SPLIT_ROOT = (
    ROOT
    / "data"
    / "processed"
    / "splits"
)

ALLOWED_DEVELOPMENT_DATASETS = {
    "UCI_HAR",
    "DSADS",
}


def load_development_train_val(
    dataset,
):

    if dataset not in ALLOWED_DEVELOPMENT_DATASETS:

        raise PermissionError(
            f"{dataset} is not an allowed "
            "candidate-development dataset"
        )


    X = np.load(
        DATA_ROOT
        / dataset
        / "X.npy",
        mmap_mode="r",
        allow_pickle=False,
    )

    y = np.load(
        DATA_ROOT
        / dataset
        / "y.npy",
        mmap_mode="r",
        allow_pickle=False,
    )


    train_idx = np.load(
        SPLIT_ROOT
        / dataset
        / "train_idx.npy",
        allow_pickle=False,
    )

    val_idx = np.load(
        SPLIT_ROOT
        / dataset
        / "val_idx.npy",
        allow_pickle=False,
    )


    train_idx = np.asarray(
        train_idx,
        dtype=np.int64,
    )

    val_idx = np.asarray(
        val_idx,
        dtype=np.int64,
    )


    X_train = np.asarray(
        X[
            train_idx
        ],
        dtype=np.float32,
    )

    X_val = np.asarray(
        X[
            val_idx
        ],
        dtype=np.float32,
    )


    y_train_native = np.asarray(
        y[
            train_idx
        ]
    )

    y_val_native = np.asarray(
        y[
            val_idx
        ]
    )


    native_classes = np.sort(
        np.unique(
            y_train_native
        )
    )


    mapping = {
        native:
            i

        for i, native in enumerate(
            native_classes.tolist()
        )
    }


    unseen_val = (
        set(
            np.unique(
                y_val_native
            ).tolist()
        )
        -
        set(
            mapping.keys()
        )
    )


    if unseen_val:

        raise RuntimeError(
            f"{dataset}: validation contains "
            f"classes absent from training: "
            f"{sorted(unseen_val)}"
        )


    y_train = np.asarray(
        [
            mapping[x]
            for x in y_train_native.tolist()
        ],
        dtype=np.int64,
    )

    y_val = np.asarray(
        [
            mapping[x]
            for x in y_val_native.tolist()
        ],
        dtype=np.int64,
    )


    mean = np.asarray(
        X_train.mean(
            axis=(
                0,
                1,
            )
        ),
        dtype=np.float32,
    )

    std = np.asarray(
        X_train.std(
            axis=(
                0,
                1,
            )
        ),
        dtype=np.float32,
    )


    if np.any(
        std <= 0
    ):

        raise RuntimeError(
            f"{dataset}: invalid train std"
        )


    return {
        "dataset":
            dataset,

        "X_train_raw":
            X_train,

        "y_train":
            y_train,

        "X_val_raw":
            X_val,

        "y_val":
            y_val,

        "train_mean":
            mean,

        "train_std":
            std,

        "native_classes":
            native_classes,

        "num_classes":
            len(
                native_classes
            ),

        "train_count":
            len(
                train_idx
            ),

        "val_count":
            len(
                val_idx
            ),
    }
