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

ALLOWED_DATASETS = {
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
}


EXPECTED = {
    "UCI_HAR": {
        "train": 5817,
        "val": 2196,
        "classes": 6,
    },

    "PAMAP2": {
        "train": 18609,
        "val": 7542,
        "classes": 12,
    },

    "DSADS": {
        "train": 4560,
        "val": 2280,
        "classes": 19,
    },

    "MotionSense": {
        "train": 12370,
        "val": 4809,
        "classes": 6,
    },
}


def load_confirmation_train_val(
    dataset: str,
):

    if dataset not in ALLOWED_DATASETS:
        raise PermissionError(
            f"Dataset not permitted by frozen R4: {dataset}"
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

    if np.intersect1d(
        train_idx,
        val_idx,
    ).size != 0:
        raise RuntimeError(
            f"{dataset}: train/validation overlap"
        )

    expected = EXPECTED[
        dataset
    ]

    if len(train_idx) != expected["train"]:
        raise RuntimeError(
            f"{dataset}: train cardinality mismatch"
        )

    if len(val_idx) != expected["val"]:
        raise RuntimeError(
            f"{dataset}: validation cardinality mismatch"
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

    if len(native_classes) != expected["classes"]:
        raise RuntimeError(
            f"{dataset}: expected "
            f"{expected['classes']} training classes, "
            f"found {len(native_classes)}"
        )

    mapping = {
        native:
            i
        for i, native
        in enumerate(
            native_classes.tolist()
        )
    }

    unseen_validation = (
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

    if unseen_validation:
        raise RuntimeError(
            f"{dataset}: validation contains classes "
            f"absent from training: "
            f"{sorted(unseen_validation)}"
        )

    y_train = np.asarray(
        [
            mapping[value]
            for value
            in y_train_native.tolist()
        ],
        dtype=np.int64,
    )

    y_val = np.asarray(
        [
            mapping[value]
            for value
            in y_val_native.tolist()
        ],
        dtype=np.int64,
    )

    train_mean = np.asarray(
        X_train.mean(
            axis=(
                0,
                1,
            )
        ),
        dtype=np.float32,
    )

    train_std = np.asarray(
        X_train.std(
            axis=(
                0,
                1,
            )
        ),
        dtype=np.float32,
    )

    if train_mean.shape != (6,):
        raise RuntimeError(
            f"{dataset}: invalid train mean shape"
        )

    if train_std.shape != (6,):
        raise RuntimeError(
            f"{dataset}: invalid train std shape"
        )

    if np.any(
        train_std <= 0
    ):
        raise RuntimeError(
            f"{dataset}: non-positive train std"
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
            train_mean,

        "train_std":
            train_std,

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
