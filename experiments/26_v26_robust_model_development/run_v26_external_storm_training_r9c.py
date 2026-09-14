from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import math
import random
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

EXP = (
    ROOT
    / "experiments/26_v26_robust_model_development"
)

if str(EXP) not in sys.path:
    sys.path.insert(
        0,
        str(EXP),
    )


from candidate_models_r2 import (
    create_v26_candidate,
    parameter_count,
)

from physical_faults_r2 import (
    apply_random_physical_faults,
)


CANDIDATE = "V26C_DualGateLiteCons"

TRAIN_NPZ = (
    ROOT
    / "results/storm_external_r2/data/unified/train.npz"
)

VAL_NPZ = (
    ROOT
    / "results/storm_external_r2/data/unified/val.npz"
)


SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]


NUM_CLASSES = 8
INPUT_CHANNELS = 6
WINDOW_LENGTH = 64

BATCH_SIZE = 64
VAL_BATCH_SIZE = 256

MAX_EPOCHS = 100
PATIENCE = 15

LR = 1e-3
WEIGHT_DECAY = 1e-4
GRAD_CLIP = 1.0

CONSISTENCY_WEIGHT = 0.20

VALIDATION_RANDOM_ROOT = 26001


CONDITIONS = [
    ("acc_total_failure", "modality_outage"),
    ("gyro_total_failure", "modality_outage"),

    ("single_axis_failure_acc_x", "single_axis_outage"),
    ("single_axis_failure_acc_y", "single_axis_outage"),
    ("single_axis_failure_acc_z", "single_axis_outage"),
    ("single_axis_failure_gyro_x", "single_axis_outage"),
    ("single_axis_failure_gyro_y", "single_axis_outage"),
    ("single_axis_failure_gyro_z", "single_axis_outage"),

    ("acc_intermittent_dropout_30pct", "intermittent_dropout"),
    ("gyro_intermittent_dropout_30pct", "intermittent_dropout"),

    ("acc_gaussian_noise_sigma_0.5", "gaussian_noise"),
    ("gyro_gaussian_noise_sigma_0.5", "gaussian_noise"),

    ("acc_stuck_value", "stuck_value"),
    ("gyro_stuck_value", "stuck_value"),

    ("acc_scale_drift_2.0x", "scale_drift"),
    ("gyro_scale_drift_2.0x", "scale_drift"),
]


FAMILIES = [
    "modality_outage",
    "single_axis_outage",
    "intermittent_dropout",
    "gaussian_noise",
    "stuck_value",
    "scale_drift",
]


def sha256_file(path):

    h = hashlib.sha256()

    with Path(path).open("rb") as f:

        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def write_json(path, obj):

    Path(path).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    Path(path).write_text(
        json.dumps(
            obj,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n"
    )


def write_csv(path, rows):

    if not rows:
        raise RuntimeError(
            f"No rows for {path}"
        )

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(rows)


def seed_all(seed):

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def decode_meta(meta_value):

    if isinstance(
        meta_value,
        np.ndarray,
    ):

        if meta_value.shape != ():
            raise RuntimeError(
                "NPZ meta must be scalar"
            )

        meta_value = meta_value.item()


    if isinstance(
        meta_value,
        bytes,
    ):

        meta_value = meta_value.decode(
            "utf-8"
        )


    if not isinstance(
        meta_value,
        str,
    ):
        raise RuntimeError(
            f"Unsupported meta type "
            f"{type(meta_value)}"
        )


    return json.loads(
        meta_value
    )


def normalization_candidates(meta):

    candidates = []


    def recurse(obj, path="root"):

        if isinstance(obj, dict):

            lower = {
                str(k).lower():
                    k
                for k in obj
            }


            mean_names = [
                name
                for name in [
                    "mean",
                    "train_mean",
                    "normalization_mean",
                    "norm_mean",
                ]
                if name in lower
            ]


            std_names = [
                name
                for name in [
                    "std",
                    "train_std",
                    "normalization_std",
                    "norm_std",
                ]
                if name in lower
            ]


            for mn in mean_names:

                for sn in std_names:

                    try:

                        mean = np.asarray(
                            obj[
                                lower[mn]
                            ],
                            dtype=np.float64,
                        ).reshape(-1)

                        std = np.asarray(
                            obj[
                                lower[sn]
                            ],
                            dtype=np.float64,
                        ).reshape(-1)

                    except Exception:
                        continue


                    if (
                        mean.shape == (6,)
                        and
                        std.shape == (6,)
                        and
                        np.all(
                            np.isfinite(mean)
                        )
                        and
                        np.all(
                            np.isfinite(std)
                        )
                        and
                        np.all(
                            std > 0
                        )
                    ):

                        candidates.append(
                            (
                                path,
                                mean,
                                std,
                            )
                        )


            for key, value in obj.items():

                recurse(
                    value,
                    f"{path}.{key}",
                )


        elif isinstance(obj, list):

            for index, value in enumerate(obj):

                recurse(
                    value,
                    f"{path}[{index}]",
                )


    recurse(meta)


    unique = []


    for candidate in candidates:

        _, mean, std = candidate

        duplicate = any(
            np.array_equal(
                mean,
                old_mean,
            )
            and
            np.array_equal(
                std,
                old_std,
            )
            for _, old_mean, old_std
            in unique
        )

        if not duplicate:
            unique.append(
                candidate
            )


    return unique


def load_normalized_split(path):

    with np.load(
        path,
        allow_pickle=False,
    ) as z:

        if set(
            z.files
        ) != {
            "X",
            "y",
            "subj",
            "meta",
        }:
            raise RuntimeError(
                f"{path}: unexpected keys "
                f"{z.files}"
            )


        X = np.asarray(
            z["X"],
            dtype=np.float64,
        )

        y = np.asarray(
            z["y"],
            dtype=np.int64,
        )

        subj = np.asarray(
            z["subj"],
            dtype=np.int64,
        )

        meta = decode_meta(
            z["meta"]
        )


    return X, y, subj, meta


def reconstruct_train_val():

    train_norm, train_y, train_subj, train_meta = (
        load_normalized_split(
            TRAIN_NPZ
        )
    )

    val_norm, val_y, val_subj, val_meta = (
        load_normalized_split(
            VAL_NPZ
        )
    )


    if train_norm.shape != (
        60379,
        64,
        6,
    ):
        raise RuntimeError(
            f"Unexpected train shape "
            f"{train_norm.shape}"
        )


    if val_norm.shape != (
        13158,
        64,
        6,
    ):
        raise RuntimeError(
            f"Unexpected val shape "
            f"{val_norm.shape}"
        )


    if set(
        np.unique(train_y).tolist()
    ) != set(
        range(8)
    ):
        raise RuntimeError(
            "Train label space != 0..7"
        )


    if set(
        np.unique(val_y).tolist()
    ) != set(
        range(8)
    ):
        raise RuntimeError(
            "Validation label space != 0..7"
        )


    if (
        set(
            np.unique(train_subj).tolist()
        )
        &
        set(
            np.unique(val_subj).tolist()
        )
    ):
        raise RuntimeError(
            "Train/val subject overlap"
        )


    train_candidates = normalization_candidates(
        train_meta
    )

    val_candidates = normalization_candidates(
        val_meta
    )


    if len(
        train_candidates
    ) != 1:

        raise RuntimeError(
            "Expected exactly one train "
            "normalization pair; "
            f"found={len(train_candidates)}; "
            f"paths={[x[0] for x in train_candidates]}"
        )


    if len(
        val_candidates
    ) != 1:

        raise RuntimeError(
            "Expected exactly one val "
            "normalization pair; "
            f"found={len(val_candidates)}; "
            f"paths={[x[0] for x in val_candidates]}"
        )


    train_path, mean, std = (
        train_candidates[0]
    )

    val_path, val_mean, val_std = (
        val_candidates[0]
    )


    if not np.array_equal(
        mean,
        val_mean,
    ):
        raise RuntimeError(
            "Train/val frozen normalization means differ"
        )


    if not np.array_equal(
        std,
        val_std,
    ):
        raise RuntimeError(
            "Train/val frozen normalization stds differ"
        )


    train_raw64 = (
        train_norm
        *
        std.reshape(
            1,
            1,
            6,
        )
        +
        mean.reshape(
            1,
            1,
            6,
        )
    )


    val_raw64 = (
        val_norm
        *
        std.reshape(
            1,
            1,
            6,
        )
        +
        mean.reshape(
            1,
            1,
            6,
        )
    )


    train_rt = (
        train_raw64
        -
        mean.reshape(
            1,
            1,
            6,
        )
    ) / std.reshape(
        1,
        1,
        6,
    )


    val_rt = (
        val_raw64
        -
        mean.reshape(
            1,
            1,
            6,
        )
    ) / std.reshape(
        1,
        1,
        6,
    )


    train_error = float(
        np.max(
            np.abs(
                train_rt
                -
                train_norm
            )
        )
    )


    val_error = float(
        np.max(
            np.abs(
                val_rt
                -
                val_norm
            )
        )
    )


    if train_error > 1e-12:
        raise RuntimeError(
            f"Train roundtrip error "
            f"{train_error}"
        )

    if val_error > 1e-12:
        raise RuntimeError(
            f"Val roundtrip error "
            f"{val_error}"
        )


    reconstruction = {
        "train_normalization_meta_path":
            train_path,

        "val_normalization_meta_path":
            val_path,

        "mean":
            mean.tolist(),

        "std":
            std.tolist(),

        "train_roundtrip_max_abs_error":
            train_error,

        "val_roundtrip_max_abs_error":
            val_error,

        "train_shape":
            list(train_norm.shape),

        "val_shape":
            list(val_norm.shape),

        "train_subject_count":
            int(
                len(
                    np.unique(train_subj)
                )
            ),

        "val_subject_count":
            int(
                len(
                    np.unique(val_subj)
                )
            ),
    }


    return (
        np.asarray(
            train_raw64,
            dtype=np.float32,
        ),
        train_y,
        np.asarray(
            val_raw64,
            dtype=np.float32,
        ),
        val_y,
        np.asarray(
            mean,
            dtype=np.float32,
        ),
        np.asarray(
            std,
            dtype=np.float32,
        ),
        reconstruction,
    )


def normalize(raw, mean_t, std_t):

    return (
        raw
        -
        mean_t.view(
            1,
            1,
            6,
        )
    ) / std_t.view(
        1,
        1,
        6,
    )


def symmetric_kl(a, b):

    log_a = F.log_softmax(
        a,
        dim=1,
    )

    log_b = F.log_softmax(
        b,
        dim=1,
    )

    p_a = log_a.exp()
    p_b = log_b.exp()


    return 0.5 * (
        F.kl_div(
            log_a,
            p_b,
            reduction="batchmean",
        )
        +
        F.kl_div(
            log_b,
            p_a,
            reduction="batchmean",
        )
    )


def confusion_add(
    confusion,
    truth,
    pred,
):

    flat = (
        truth.astype(
            np.int64
        )
        *
        NUM_CLASSES
        +
        pred.astype(
            np.int64
        )
    )

    confusion += np.bincount(
        flat,
        minlength=(
            NUM_CLASSES
            *
            NUM_CLASSES
        ),
    ).reshape(
        NUM_CLASSES,
        NUM_CLASSES,
    )


def metrics_from_confusion(confusion):

    confusion = np.asarray(
        confusion,
        dtype=np.float64,
    )

    total = float(
        confusion.sum()
    )

    if total <= 0:
        raise RuntimeError(
            "Empty confusion matrix"
        )


    accuracy = float(
        np.trace(confusion)
        /
        total
    )


    f1s = []


    for cls in range(
        NUM_CLASSES
    ):

        tp = confusion[
            cls,
            cls
        ]

        fp = (
            confusion[
                :,
                cls
            ].sum()
            -
            tp
        )

        fn = (
            confusion[
                cls,
                :
            ].sum()
            -
            tp
        )


        denom = (
            2.0
            *
            tp
            +
            fp
            +
            fn
        )


        f1s.append(
            0.0
            if denom == 0.0
            else
            float(
                2.0
                *
                tp
                /
                denom
            )
        )


    return (
        accuracy,
        float(
            np.mean(f1s)
        ),
    )


def modality_channels(name):

    if name.startswith(
        "acc_"
    ):
        return [
            0,
            1,
            2,
        ]

    return [
        3,
        4,
        5,
    ]


def apply_fixed_validation_fault(
    raw,
    name,
    rng,
    train_std,
):

    x = np.array(
        raw,
        dtype=np.float32,
        copy=True,
    )


    if name == "acc_total_failure":

        x[
            :,
            :,
            0:3
        ] = 0.0


    elif name == "gyro_total_failure":

        x[
            :,
            :,
            3:6
        ] = 0.0


    elif name.startswith(
        "single_axis_failure_"
    ):

        mapping = {
            "single_axis_failure_acc_x": 0,
            "single_axis_failure_acc_y": 1,
            "single_axis_failure_acc_z": 2,
            "single_axis_failure_gyro_x": 3,
            "single_axis_failure_gyro_y": 4,
            "single_axis_failure_gyro_z": 5,
        }

        x[
            :,
            :,
            mapping[name]
        ] = 0.0


    elif "intermittent_dropout" in name:

        channels = modality_channels(
            name
        )

        mask = (
            rng.rand(
                x.shape[0],
                x.shape[1],
            )
            <
            0.30
        )


        for channel in channels:

            view = x[
                :,
                :,
                channel
            ]

            view[
                mask
            ] = 0.0


    elif "gaussian_noise" in name:

        channels = modality_channels(
            name
        )


        for channel in channels:

            noise = rng.normal(
                0.0,
                0.5
                *
                float(
                    train_std[
                        channel
                    ]
                ),
                size=(
                    x.shape[0],
                    x.shape[1],
                ),
            ).astype(
                np.float32
            )


            x[
                :,
                :,
                channel
            ] += noise


    elif "stuck_value" in name:

        channels = modality_channels(
            name
        )


        tau = rng.randint(
            x.shape[1] // 4,
            3 * x.shape[1] // 4,
            size=x.shape[0],
        )


        for row_index in range(
            x.shape[0]
        ):

            t = int(
                tau[
                    row_index
                ]
            )


            for channel in channels:

                value = x[
                    row_index,
                    t,
                    channel,
                ]

                x[
                    row_index,
                    t:,
                    channel,
                ] = value


    elif "scale_drift" in name:

        channels = modality_channels(
            name
        )

        scale = np.linspace(
            1.0,
            2.0,
            x.shape[1],
            dtype=np.float32,
        ).reshape(
            1,
            -1,
            1,
        )


        x[
            :,
            :,
            channels
        ] *= scale


    else:

        raise KeyError(
            name
        )


    return x


def evaluate_clean(
    model,
    val_raw,
    val_y,
    mean_t,
    std_t,
    device,
    limit=None,
):

    if limit is not None:
        val_raw = val_raw[
            :limit
        ]
        val_y = val_y[
            :limit
        ]


    confusion = np.zeros(
        (
            NUM_CLASSES,
            NUM_CLASSES,
        ),
        dtype=np.int64,
    )


    model.eval()


    with torch.inference_mode():

        for start in range(
            0,
            len(val_y),
            VAL_BATCH_SIZE,
        ):

            stop = min(
                start
                +
                VAL_BATCH_SIZE,
                len(val_y),
            )


            raw = torch.from_numpy(
                val_raw[
                    start:stop
                ]
            ).to(
                device
            )


            logits = model(
                normalize(
                    raw,
                    mean_t,
                    std_t,
                )
            )


            pred = (
                logits.argmax(
                    dim=1
                )
                .cpu()
                .numpy()
            )


            confusion_add(
                confusion,
                val_y[
                    start:stop
                ],
                pred,
            )


    return metrics_from_confusion(
        confusion
    )


def evaluate_faults(
    model,
    val_raw,
    val_y,
    mean,
    std,
    device,
    limit=None,
):

    if limit is not None:
        val_raw = val_raw[
            :limit
        ]
        val_y = val_y[
            :limit
        ]


    rows = []


    for condition_index, (
        name,
        family,
    ) in enumerate(
        CONDITIONS
    ):

        rng = np.random.RandomState(
            VALIDATION_RANDOM_ROOT
            +
            condition_index
            *
            1009
        )


        confusion = np.zeros(
            (
                NUM_CLASSES,
                NUM_CLASSES,
            ),
            dtype=np.int64,
        )


        with torch.inference_mode():

            for start in range(
                0,
                len(val_y),
                VAL_BATCH_SIZE,
            ):

                stop = min(
                    start
                    +
                    VAL_BATCH_SIZE,
                    len(val_y),
                )


                corrupt_raw = (
                    apply_fixed_validation_fault(
                        val_raw[
                            start:stop
                        ],
                        name,
                        rng,
                        std,
                    )
                )


                x = (
                    corrupt_raw
                    -
                    mean.reshape(
                        1,
                        1,
                        6,
                    )
                ) / std.reshape(
                    1,
                    1,
                    6,
                )


                logits = model(
                    torch.from_numpy(
                        np.asarray(
                            x,
                            dtype=np.float32,
                        )
                    ).to(
                        device
                    )
                )


                pred = (
                    logits.argmax(
                        dim=1
                    )
                    .cpu()
                    .numpy()
                )


                confusion_add(
                    confusion,
                    val_y[
                        start:stop
                    ],
                    pred,
                )


        accuracy, macro_f1 = (
            metrics_from_confusion(
                confusion
            )
        )


        rows.append({
            "condition":
                name,

            "family":
                family,

            "accuracy":
                accuracy,

            "macro_f1":
                macro_f1,
        })


    recoverable_f1 = float(
        statistics.fmean(
            row[
                "macro_f1"
            ]
            for row in rows
        )
    )


    family_f1 = []


    for family in FAMILIES:

        values = [
            row[
                "macro_f1"
            ]
            for row in rows
            if row[
                "family"
            ]
            ==
            family
        ]

        if not values:
            raise RuntimeError(
                f"Missing family "
                f"{family}"
            )


        family_f1.append(
            statistics.fmean(
                values
            )
        )


    return (
        rows,
        recoverable_f1,
        float(
            statistics.fmean(
                family_f1
            )
        ),
    )


def score(
    clean_f1,
    recoverable_f1,
    family_balanced_f1,
):

    return float(
        0.20
        *
        clean_f1
        +
        0.30
        *
        recoverable_f1
        +
        0.50
        *
        family_balanced_f1
    )


def run_smoke(
    out_dir,
    device,
):

    (
        train_raw,
        train_y,
        val_raw,
        val_y,
        mean,
        std,
        reconstruction,
    ) = reconstruct_train_val()


    write_json(
        out_dir
        / "normalization_reconstruction.json",
        reconstruction,
    )


    seed_all(
        42
    )


    model = create_v26_candidate(
        CANDIDATE,
        NUM_CLASSES,
        input_channels=6,
    ).to(
        device
    )


    if parameter_count(
        model
    ) != 23210:
        raise RuntimeError(
            "K8 parameter count mismatch"
        )


    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LR,
        weight_decay=WEIGHT_DECAY,
    )


    mean_t = torch.tensor(
        mean,
        dtype=torch.float32,
        device=device,
    )

    std_t = torch.tensor(
        std,
        dtype=torch.float32,
        device=device,
    )


    raw_cpu = torch.from_numpy(
        train_raw[
            :128
        ]
    ).to(
        dtype=torch.float32,
        device="cpu",
    )

    y = torch.from_numpy(
        train_y[
            :128
        ]
    ).to(
        device
    )


    std_cpu_t = torch.from_numpy(
        std
    ).to(
        dtype=torch.float32,
        device="cpu",
    )


    generator = torch.Generator()

    generator.manual_seed(
        42 * 100003
        +
        26001
    )


    model.train()


    # Frozen R2 ordering:
    # CPU pre-normalization raw -> CPU physical fault ->
    # transfer both variants to GPU -> frozen normalization.
    fault_raw_cpu, _ = (
        apply_random_physical_faults(
            raw_cpu,
            std_cpu_t,
            generator,
        )
    )


    raw = raw_cpu.to(
        device=device,
        dtype=torch.float32,
    )

    fault_raw = fault_raw_cpu.to(
        device=device,
        dtype=torch.float32,
    )


    clean_x = normalize(
        raw,
        mean_t,
        std_t,
    )


    fault_x = normalize(
        fault_raw,
        mean_t,
        std_t,
    )


    clean_logits = model(
        clean_x
    )

    fault_logits = model(
        fault_x
    )


    loss = (
        F.cross_entropy(
            clean_logits,
            y,
        )
        +
        F.cross_entropy(
            fault_logits,
            y,
        )
        +
        CONSISTENCY_WEIGHT
        *
        symmetric_kl(
            clean_logits,
            fault_logits,
        )
    )


    optimizer.zero_grad(
        set_to_none=True
    )

    loss.backward()

    torch.nn.utils.clip_grad_norm_(
        model.parameters(),
        GRAD_CLIP,
    )

    optimizer.step()


    clean_acc, clean_f1 = (
        evaluate_clean(
            model,
            val_raw,
            val_y,
            mean_t,
            std_t,
            device,
            limit=512,
        )
    )


    (
        condition_rows,
        recoverable_f1,
        family_balanced_f1,
    ) = evaluate_faults(
        model,
        val_raw,
        val_y,
        mean,
        std,
        device,
        limit=512,
    )


    if len(
        condition_rows
    ) != 16:
        raise RuntimeError(
            "Smoke validation conditions != 16"
        )


    receipt = {
        "status":
            "PASS",

        "candidate":
            CANDIDATE,

        "parameter_count":
            parameter_count(
                model
            ),

        "train_shape":
            reconstruction[
                "train_shape"
            ],

        "val_shape":
            reconstruction[
                "val_shape"
            ],

        "train_roundtrip_max_abs_error":
            reconstruction[
                "train_roundtrip_max_abs_error"
            ],

        "val_roundtrip_max_abs_error":
            reconstruction[
                "val_roundtrip_max_abs_error"
            ],

        "physical_fault_required_call_arguments":
            3,

        "optional_forced_family_used_for_training":
            False,

        "optimizer_step_pass":
            True,

        "clean_validation_subset_macro_f1":
            clean_f1,

        "recoverable_validation_subset_macro_f1":
            recoverable_f1,

        "family_balanced_validation_subset_macro_f1":
            family_balanced_f1,

        "validation_conditions":
            16,

        "external_test_loaded":
            False,

        "external_test_inference":
            False,

        "scientific_checkpoint_created":
            False,
    }


    write_json(
        out_dir
        / "r9c_training_smoke_receipt.json",
        receipt,
    )


    print(
        "R9C_NORMALIZATION_RECONSTRUCTION_PASS=True"
    )

    print(
        "R9C_TRAIN_SHAPE_PASS_60379x64x6=True"
    )

    print(
        "R9C_VAL_SHAPE_PASS_13158x64x6=True"
    )

    print(
        "R9C_EXTERNAL_K8_PARAMETERS_PASS_23210=True"
    )

    print(
        "R9C_THREE_ARGUMENT_PHYSICAL_FAULT_CALL_PASS=True"
    )

    print(
        "R9C_SMOKE_OPTIMIZER_STEP_PASS=True"
    )

    print(
        "R9C_SMOKE_VALIDATION_CONDITIONS_PASS_16=True"
    )

    print(
        "EXTERNAL_TEST_LOADED=False"
    )

    print(
        "EXTERNAL_TEST_INFERENCE=False"
    )

    print(
        "V26_EXTERNAL_STORM_TRAINING_SMOKE_R9C0_PASS=True"
    )


def train_seed(
    seed,
    out_dir,
    device,
    train_raw,
    train_y,
    val_raw,
    val_y,
    mean,
    std,
):

    seed_all(
        seed
    )


    run_dir = (
        out_dir
        / "raw_runs"
        / "STORM_cross_source"
        / f"seed_{seed}"
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    model = create_v26_candidate(
        CANDIDATE,
        NUM_CLASSES,
        input_channels=6,
    ).to(
        device
    )


    params = parameter_count(
        model
    )

    if params != 23210:
        raise RuntimeError(
            f"Parameter mismatch "
            f"{params}"
        )


    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LR,
        weight_decay=WEIGHT_DECAY,
    )


    mean_t = torch.tensor(
        mean,
        dtype=torch.float32,
        device=device,
    )

    std_t = torch.tensor(
        std,
        dtype=torch.float32,
        device=device,
    )


    dataset = TensorDataset(
        torch.from_numpy(
            train_raw
        ),
        torch.from_numpy(
            train_y
        ),
    )


    loader_generator = torch.Generator()
    loader_generator.manual_seed(
        seed
    )


    loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,
        pin_memory=True,
        generator=loader_generator,
    )


    std_cpu_t = torch.from_numpy(
        std
    ).to(
        dtype=torch.float32,
        device="cpu",
    )


    fault_generator = torch.Generator()

    fault_generator.manual_seed(
        (
            seed * 100003
            +
            26001
        )
        %
        (
            2**63
            -
            1
        )
    )


    best_score = -math.inf
    best_epoch = 0
    best_metrics = None

    patience_count = 0

    history = []

    training_start = time.perf_counter()


    for epoch in range(
        1,
        MAX_EPOCHS + 1,
    ):

        epoch_start = time.perf_counter()

        model.train()

        total_loss = 0.0
        total_clean = 0.0
        total_fault = 0.0
        total_consistency = 0.0
        seen = 0


        for raw_cpu, y_cpu in loader:

            # Exact frozen physical-training ordering:
            # fault corruption runs on CPU before normalization
            # and before GPU transfer.
            fault_raw_cpu, _ = (
                apply_random_physical_faults(
                    raw_cpu,
                    std_cpu_t,
                    fault_generator,
                )
            )


            raw = raw_cpu.to(
                device=device,
                dtype=torch.float32,
                non_blocking=True,
            )

            fault_raw = fault_raw_cpu.to(
                device=device,
                dtype=torch.float32,
                non_blocking=True,
            )

            y = y_cpu.to(
                device=device,
                dtype=torch.long,
                non_blocking=True,
            )


            clean_x = normalize(
                raw,
                mean_t,
                std_t,
            )


            fault_x = normalize(
                fault_raw,
                mean_t,
                std_t,
            )


            optimizer.zero_grad(
                set_to_none=True
            )


            clean_logits = model(
                clean_x
            )

            fault_logits = model(
                fault_x
            )


            clean_ce = F.cross_entropy(
                clean_logits,
                y,
            )

            fault_ce = F.cross_entropy(
                fault_logits,
                y,
            )

            consistency = symmetric_kl(
                clean_logits,
                fault_logits,
            )


            loss = (
                clean_ce
                +
                fault_ce
                +
                CONSISTENCY_WEIGHT
                *
                consistency
            )


            loss.backward()


            torch.nn.utils.clip_grad_norm_(
                model.parameters(),
                GRAD_CLIP,
            )


            optimizer.step()


            n = int(
                y.shape[0]
            )


            seen += n

            total_loss += (
                float(
                    loss.detach().item()
                )
                *
                n
            )

            total_clean += (
                float(
                    clean_ce.detach().item()
                )
                *
                n
            )

            total_fault += (
                float(
                    fault_ce.detach().item()
                )
                *
                n
            )

            total_consistency += (
                float(
                    consistency.detach().item()
                )
                *
                n
            )


        clean_acc, clean_f1 = (
            evaluate_clean(
                model,
                val_raw,
                val_y,
                mean_t,
                std_t,
                device,
            )
        )


        (
            condition_rows,
            recoverable_f1,
            family_balanced_f1,
        ) = evaluate_faults(
            model,
            val_raw,
            val_y,
            mean,
            std,
            device,
        )


        selection_score = score(
            clean_f1,
            recoverable_f1,
            family_balanced_f1,
        )


        improved = (
            selection_score
            >
            best_score
        )


        if improved:

            best_score = (
                selection_score
            )

            best_epoch = epoch

            best_metrics = {
                "clean_accuracy":
                    clean_acc,

                "clean_macro_f1":
                    clean_f1,

                "recoverable_fault_macro_f1":
                    recoverable_f1,

                "family_balanced_macro_f1":
                    family_balanced_f1,

                "selection_score":
                    selection_score,
            }


            torch.save(
                model.state_dict(),
                run_dir
                / "best_model.pt",
            )


            write_csv(
                run_dir
                / "best_condition_metrics_16.csv",
                condition_rows,
            )


            patience_count = 0


        else:

            patience_count += 1


        epoch_seconds = (
            time.perf_counter()
            -
            epoch_start
        )


        history.append({
            "epoch":
                epoch,

            "train_total_loss":
                total_loss
                /
                seen,

            "train_clean_ce":
                total_clean
                /
                seen,

            "train_fault_ce":
                total_fault
                /
                seen,

            "train_consistency":
                total_consistency
                /
                seen,

            "val_clean_macro_f1":
                clean_f1,

            "val_recoverable_fault_macro_f1":
                recoverable_f1,

            "val_family_balanced_macro_f1":
                family_balanced_f1,

            "val_selection_score":
                selection_score,

            "best_selection_score_so_far":
                best_score,

            "best_epoch_so_far":
                best_epoch,

            "improved":
                improved,

            "epochs_without_improvement":
                patience_count,

            "epoch_seconds":
                epoch_seconds,
        })


        write_csv(
            run_dir
            / "history.csv",
            history,
        )


        print(
            "R9C_EPOCH:",
            f"seed={seed}",
            f"epoch={epoch}",
            f"clean_f1={clean_f1:.6f}",
            f"rec_f1={recoverable_f1:.6f}",
            f"fb_f1={family_balanced_f1:.6f}",
            f"score={selection_score:.6f}",
            f"best={best_score:.6f}",
            f"best_epoch={best_epoch}",
            f"patience={patience_count}/{PATIENCE}",
            f"seconds={epoch_seconds:.2f}",
            flush=True,
        )


        if patience_count >= PATIENCE:

            print(
                "R9C_EARLY_STOP:",
                f"seed={seed}",
                f"epoch={epoch}",
                f"best_epoch={best_epoch}",
                flush=True,
            )

            break


    checkpoint = (
        run_dir
        / "best_model.pt"
    )


    if not checkpoint.exists():
        raise RuntimeError(
            f"No checkpoint for seed "
            f"{seed}"
        )


    receipt = {
        "candidate":
            CANDIDATE,

        "seed":
            seed,

        "parameter_count":
            params,

        "best_epoch":
            best_epoch,

        "best_validation_metrics":
            best_metrics,

        "checkpoint":
            str(
                checkpoint.relative_to(
                    ROOT
                )
            ),

        "checkpoint_sha256":
            sha256_file(
                checkpoint
            ),

        "training_seconds":
            (
                time.perf_counter()
                -
                training_start
            ),

        "physical_pre_normalization_training":
            True,

        "physical_fault_required_argument_call":
            3,

        "forced_family_training_override_used":
            False,

        "external_test_loaded":
            False,

        "external_test_inference":
            False,

        "candidate_modified":
            False,
    }


    write_json(
        run_dir
        / "run_receipt.json",
        receipt,
    )


    print(
        "R9C_SEED_COMPLETE:",
        f"seed={seed}",
        f"best_epoch={best_epoch}",
        f"clean_f1={best_metrics['clean_macro_f1']:.9f}",
        f"rec_f1={best_metrics['recoverable_fault_macro_f1']:.9f}",
        f"fb_f1={best_metrics['family_balanced_macro_f1']:.9f}",
        f"score={best_metrics['selection_score']:.9f}",
        f"sha={receipt['checkpoint_sha256']}",
        flush=True,
    )


    del model
    del optimizer

    gc.collect()

    torch.cuda.empty_cache()


    return receipt


def train_all(
    out_dir,
    device,
):

    marker = (
        out_dir
        / "TRAINING_STARTED"
    )


    if marker.exists():
        raise RuntimeError(
            "TRAINING_STARTED already exists; "
            "refusing second R9C run"
        )


    (
        train_raw,
        train_y,
        val_raw,
        val_y,
        mean,
        std,
        reconstruction,
    ) = reconstruct_train_val()


    write_json(
        out_dir
        / "normalization_reconstruction.json",
        reconstruction,
    )


    marker.write_text(
        "V26 external STORM R9C five-seed "
        "scientific training started.\n"
    )


    print(
        "R9C_TRAINING_STARTED=True",
        flush=True,
    )


    receipts = []


    for seed in SEEDS:

        receipts.append(
            train_seed(
                seed,
                out_dir,
                device,
                train_raw,
                train_y,
                val_raw,
                val_y,
                mean,
                std,
            )
        )


    rows = []


    for receipt in receipts:

        m = receipt[
            "best_validation_metrics"
        ]


        rows.append({
            "candidate":
                receipt[
                    "candidate"
                ],

            "seed":
                receipt[
                    "seed"
                ],

            "parameter_count":
                receipt[
                    "parameter_count"
                ],

            "best_epoch":
                receipt[
                    "best_epoch"
                ],

            "best_clean_macro_f1":
                m[
                    "clean_macro_f1"
                ],

            "best_recoverable_fault_macro_f1":
                m[
                    "recoverable_fault_macro_f1"
                ],

            "best_family_balanced_macro_f1":
                m[
                    "family_balanced_macro_f1"
                ],

            "best_selection_score":
                m[
                    "selection_score"
                ],

            "checkpoint":
                receipt[
                    "checkpoint"
                ],

            "checkpoint_sha256":
                receipt[
                    "checkpoint_sha256"
                ],

            "training_seconds":
                receipt[
                    "training_seconds"
                ],
        })


    write_csv(
        out_dir
        / "external_v26c_checkpoint_manifest_5.csv",
        rows,
    )


    summary = {
        "candidate":
            CANDIDATE,

        "seeds":
            SEEDS,

        "completed_runs":
            5,

        "parameter_count":
            23210,

        "mean_best_clean_macro_f1":
            float(
                statistics.fmean(
                    row[
                        "best_clean_macro_f1"
                    ]
                    for row in rows
                )
            ),

        "mean_best_recoverable_fault_macro_f1":
            float(
                statistics.fmean(
                    row[
                        "best_recoverable_fault_macro_f1"
                    ]
                    for row in rows
                )
            ),

        "mean_best_family_balanced_macro_f1":
            float(
                statistics.fmean(
                    row[
                        "best_family_balanced_macro_f1"
                    ]
                    for row in rows
                )
            ),

        "mean_best_selection_score":
            float(
                statistics.fmean(
                    row[
                        "best_selection_score"
                    ]
                    for row in rows
                )
            ),

        "all_checkpoints_frozen_before_external_test":
            True,

        "external_test_loaded":
            False,

        "external_test_inference":
            False,

        "candidate_modified":
            False,

        "training_fault_domain":
            (
                "pre-normalization sensor-domain "
                "model-window representation"
            ),
    }


    write_json(
        out_dir
        / "external_v26c_training_summary_r9c.json",
        summary,
    )


    print(
        "R9C_COMPLETED_EXTERNAL_TRAINING_RUNS=5/5"
    )

    print(
        "R9C_MEAN_BEST_CLEAN_MACRO_F1=",
        f"{summary['mean_best_clean_macro_f1']:.9f}"
    )

    print(
        "R9C_MEAN_BEST_RECOVERABLE_FAULT_MACRO_F1=",
        f"{summary['mean_best_recoverable_fault_macro_f1']:.9f}"
    )

    print(
        "R9C_MEAN_BEST_FAMILY_BALANCED_MACRO_F1=",
        f"{summary['mean_best_family_balanced_macro_f1']:.9f}"
    )

    print(
        "R9C_MEAN_BEST_SELECTION_SCORE=",
        f"{summary['mean_best_selection_score']:.9f}"
    )

    print(
        "R9C_ALL_5_CHECKPOINTS_FROZEN_BEFORE_EXTERNAL_TEST=True"
    )

    print(
        "R9C_EXTERNAL_TEST_LOADED=False"
    )

    print(
        "R9C_EXTERNAL_TEST_INFERENCE=False"
    )

    print(
        "V26_EXTERNAL_STORM_TRAINING_R9C_PASS=True"
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mode",
        choices=[
            "smoke",
            "train-all",
        ],
        required=True,
    )

    parser.add_argument(
        "--out-dir",
        required=True,
    )

    parser.add_argument(
        "--device",
        default="cuda:0",
    )

    args = parser.parse_args()


    device = torch.device(
        args.device
    )


    if (
        device.type == "cuda"
        and
        not torch.cuda.is_available()
    ):
        raise RuntimeError(
            "CUDA unavailable"
        )


    out_dir = Path(
        args.out_dir
    )

    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    if args.mode == "smoke":

        run_smoke(
            out_dir,
            device,
        )

    else:

        train_all(
            out_dir,
            device,
        )


if __name__ == "__main__":
    main()
