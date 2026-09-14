from __future__ import annotations

import csv
import gc
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

EXP = (
    ROOT
    / "experiments"
    / "26_v26_robust_model_development"
)

R4 = (
    ROOT
    / "results"
    / "v26_primary_confirmation_protocol_r4"
)

R2 = (
    ROOT
    / "results"
    / "stage25_physical_fault_protocol"
    / "canonical_reconstruction_audit_r2"
)

OUT = (
    ROOT
    / "results"
    / "v26_primary_confirmation_training_r5"
)

RAW_OUT = (
    OUT
    / "raw_runs"
)

RAW_OUT.mkdir(
    parents=True,
    exist_ok=True,
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

from confirmation_data_r5 import (
    load_confirmation_train_val,
)

from losses_r2 import (
    candidate_training_loss,
)

from physical_faults_r2 import (
    apply_random_physical_faults,
    normalize_with_train_stats,
)

from validation_r2 import (
    evaluate_validation_only,
)


PROMOTED = "V26C_DualGateLiteCons"

DEVICE = torch.device(
    "cuda:0"
)

BATCH_SIZE = 64

MAX_EPOCHS = 100

PATIENCE = 15

LEARNING_RATE = 1e-3

WEIGHT_DECAY = 1e-4

GRADIENT_CLIP = 1.0

PARAMETER_CEILING = 60000


def write_json(
    path: Path,
    obj,
):

    path.write_text(
        json.dumps(
            obj,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n"
    )


def write_csv(
    path: Path,
    rows,
):

    if not rows:
        return

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

        writer.writerows(
            rows
        )


def sha256_file(
    path: Path,
):

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):

            h.update(
                block
            )

    return h.hexdigest()


def stable_seed(
    *parts,
):

    payload = "|".join(
        str(x)
        for x in parts
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


def set_global_seed(
    seed,
):

    random.seed(
        seed
    )

    np.random.seed(
        seed
    )

    torch.manual_seed(
        seed
    )

    torch.cuda.manual_seed_all(
        seed
    )


def save_state_dict_cpu(
    model,
    path,
):

    state = {
        key:
            value.detach()
            .cpu()
            .clone()

        for key, value
        in model.state_dict().items()
    }

    torch.save(
        state,
        path,
    )


def load_direct_state_dict(
    path,
):

    try:

        state = torch.load(
            path,
            map_location="cpu",
            weights_only=True,
        )

    except TypeError:

        state = torch.load(
            path,
            map_location="cpu",
        )

    if not isinstance(
        state,
        dict,
    ):

        raise RuntimeError(
            f"{path}: checkpoint is not dictionary"
        )

    if not state:

        raise RuntimeError(
            f"{path}: checkpoint is empty"
        )

    if not all(
        torch.is_tensor(
            value
        )
        for value in state.values()
    ):

        raise RuntimeError(
            f"{path}: expected direct tensor state_dict"
        )

    return state


print("=" * 118)
print("V26 PRIMARY CONFIRMATION TRAINING R5")
print("V26C — 14 TRAIN/VALIDATION-ONLY RUNS")
print("PROTECTED TEST REMAINS LOCKED")
print("=" * 118)


if not torch.cuda.is_available():

    raise RuntimeError(
        "CUDA unavailable. "
        "Classify dependency/environment failure."
    )


torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True


print(
    "PYTHON_VERSION=",
    sys.version.replace(
        "\n",
        " ",
    ),
)

print(
    "TORCH_VERSION=",
    torch.__version__,
)

print(
    "DEVICE=",
    DEVICE,
)

print(
    "GPU_NAME=",
    torch.cuda.get_device_name(
        0
    ),
)


# ============================================================
# 1. Frozen R4 receipt
# ============================================================

r4_receipt = json.loads(
    (
        R4
        / "v26_primary_confirmation_protocol_receipt_r4.json"
    ).read_text()
)


required = {
    "status":
        "FROZEN_BEFORE_PRIMARY_CONFIRMATION",

    "promoted_candidate":
        PROMOTED,

    "promotion_reconstructed_mechanically":
        True,

    "selection_rule_modified":
        False,

    "confirmation_training_runs":
        14,

    "all_checkpoints_frozen_before_test":
        True,

    "expected_confirmation_test_rows":
        252,

    "test_inference_performed":
        False,

    "confirmation_training_performed":
        False,

    "storm_used_for_selection":
        False,

    "candidate_modified":
        False,

    "training_protocol_modified":
        False,

    "fault_protocol_modified":
        False,
}


for key, expected in required.items():

    actual = r4_receipt.get(
        key
    )

    if actual != expected:

        raise RuntimeError(
            f"R4 prerequisite mismatch: "
            f"{key}={actual!r}, "
            f"expected={expected!r}"
        )


print(
    "FROZEN_R4_CONFIRMATION_PROTOCOL_PASS=True"
)


# ============================================================
# 2. Exact 14-run manifest
# ============================================================

manifest_path = (
    R4
    / "primary_confirmation_training_manifest_14.csv"
)

with manifest_path.open(
    newline="",
    encoding="utf-8",
) as f:

    manifest = list(
        csv.DictReader(
            f
        )
    )


if len(
    manifest
) != 14:

    raise RuntimeError(
        f"Expected 14 manifest rows, found {len(manifest)}"
    )


expected_pairs = {
    ("UCI_HAR", 789),
    ("UCI_HAR", 2026),
    ("DSADS", 789),
    ("DSADS", 2026),

    ("PAMAP2", 42),
    ("PAMAP2", 123),
    ("PAMAP2", 456),
    ("PAMAP2", 789),
    ("PAMAP2", 2026),

    ("MotionSense", 42),
    ("MotionSense", 123),
    ("MotionSense", 456),
    ("MotionSense", 789),
    ("MotionSense", 2026),
}


actual_pairs = {
    (
        row[
            "dataset"
        ],
        int(
            row[
                "seed"
            ]
        ),
    )
    for row in manifest
}


if actual_pairs != expected_pairs:

    raise RuntimeError(
        "Frozen 14-run confirmation manifest changed"
    )


if any(
    row[
        "candidate_id"
    ]
    !=
    PROMOTED
    for row in manifest
):

    raise RuntimeError(
        "Confirmation manifest contains non-V26C candidate"
    )


print(
    "PRIMARY_CONFIRMATION_MANIFEST_BOUND_14_OF_14=True"
)


# ============================================================
# 3. Reproduce frozen train-only normalization on all 4
# ============================================================

normalization_receipts = json.loads(
    (
        R2
        / "dataset_normalization_receipts.json"
    ).read_text()
)


datasets = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]


data_cache = {}

data_integrity_rows = []


for dataset in datasets:

    data = load_confirmation_train_val(
        dataset
    )

    data_cache[
        dataset
    ] = data


    frozen_mean = np.asarray(
        normalization_receipts[
            dataset
        ][
            "mean"
        ],
        dtype=np.float32,
    )

    frozen_std = np.asarray(
        normalization_receipts[
            dataset
        ][
            "std"
        ],
        dtype=np.float32,
    )


    mean_error = float(
        np.max(
            np.abs(
                data[
                    "train_mean"
                ].astype(
                    np.float64
                )
                -
                frozen_mean.astype(
                    np.float64
                )
            )
        )
    )


    std_error = float(
        np.max(
            np.abs(
                data[
                    "train_std"
                ].astype(
                    np.float64
                )
                -
                frozen_std.astype(
                    np.float64
                )
            )
        )
    )


    if mean_error > 1e-6:

        raise RuntimeError(
            f"{dataset}: train mean mismatch: "
            f"{mean_error}"
        )


    if std_error > 1e-6:

        raise RuntimeError(
            f"{dataset}: train std mismatch: "
            f"{std_error}"
        )


    data_integrity_rows.append({
        "dataset":
            dataset,

        "train_count":
            data[
                "train_count"
            ],

        "val_count":
            data[
                "val_count"
            ],

        "num_classes":
            data[
                "num_classes"
            ],

        "train_mean_max_abs_error_vs_r2":
            mean_error,

        "train_std_max_abs_error_vs_r2":
            std_error,
    })


write_csv(
    OUT
    / "confirmation_train_val_data_integrity_4.csv",
    data_integrity_rows,
)


print(
    "CONFIRMATION_TRAIN_ONLY_NORMALIZATION_PASS_4_OF_4=True"
)

print(
    "CONFIRMATION_TRAIN_VAL_DATA_BOUND_4_OF_4=True"
)


# ============================================================
# 4. Train exact frozen V26C run
# ============================================================

def train_one_confirmation_run(
    dataset,
    seed,
):

    data = data_cache[
        dataset
    ]

    num_classes = int(
        data[
            "num_classes"
        ]
    )


    run_dir = (
        RAW_OUT
        / dataset
        / PROMOTED
        / f"seed_{seed}"
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    set_global_seed(
        seed
    )


    model = create_v26_candidate(
        PROMOTED,
        num_classes,
        input_channels=6,
    )


    params = parameter_count(
        model
    )


    if params > PARAMETER_CEILING:

        raise RuntimeError(
            f"{dataset}/seed_{seed}: "
            f"{params} parameters exceeds "
            f"frozen ceiling {PARAMETER_CEILING}"
        )


    model = model.to(
        DEVICE
    )


    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
    )


    X_train = torch.from_numpy(
        np.asarray(
            data[
                "X_train_raw"
            ],
            dtype=np.float32,
        )
    )


    y_train = torch.from_numpy(
        np.asarray(
            data[
                "y_train"
            ],
            dtype=np.int64,
        )
    )


    train_mean = torch.from_numpy(
        np.asarray(
            data[
                "train_mean"
            ],
            dtype=np.float32,
        )
    )


    train_std = torch.from_numpy(
        np.asarray(
            data[
                "train_std"
            ],
            dtype=np.float32,
        )
    )


    n_train = int(
        len(
            X_train
        )
    )


    history = []

    best_score = -float(
        "inf"
    )

    best_epoch = None

    best_metrics = None

    epochs_without_improvement = 0


    best_path = (
        run_dir
        / "best_model.pt"
    )


    start_time = (
        time.perf_counter()
    )


    for epoch in range(
        1,
        MAX_EPOCHS + 1,
    ):

        epoch_start = (
            time.perf_counter()
        )


        model.train()


        # Keep exact R3 screening RNG namespace.
        permutation_generator = (
            torch.Generator()
            .manual_seed(
                stable_seed(
                    "V26_R3",
                    dataset,
                    seed,
                    epoch,
                    "permutation",
                )
            )
        )


        fault_generator = (
            torch.Generator()
            .manual_seed(
                stable_seed(
                    "V26_R3",
                    dataset,
                    seed,
                    epoch,
                    "faults",
                )
            )
        )


        permutation = torch.randperm(
            n_train,
            generator=permutation_generator,
        )


        running_total = 0.0

        running_clean = 0.0

        running_fault = 0.0

        running_consistency = 0.0

        samples_seen = 0


        for start in range(
            0,
            n_train,
            BATCH_SIZE,
        ):

            batch_indices = permutation[
                start:
                start
                +
                BATCH_SIZE
            ]


            raw_batch = X_train[
                batch_indices
            ]

            labels_cpu = y_train[
                batch_indices
            ]


            fault_raw, _ = (
                apply_random_physical_faults(
                    raw_batch,
                    train_std,
                    fault_generator,
                )
            )


            clean_x = (
                normalize_with_train_stats(
                    raw_batch,
                    train_mean,
                    train_std,
                )
                .to(
                    DEVICE,
                    non_blocking=True,
                )
            )


            fault_x = (
                normalize_with_train_stats(
                    fault_raw,
                    train_mean,
                    train_std,
                )
                .to(
                    DEVICE,
                    non_blocking=True,
                )
            )


            labels = labels_cpu.to(
                DEVICE,
                non_blocking=True,
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


            losses = candidate_training_loss(
                PROMOTED,
                clean_logits,
                fault_logits,
                labels,
            )


            loss = losses[
                "loss"
            ]


            if not torch.isfinite(
                loss
            ):

                raise RuntimeError(
                    f"Non-finite training loss: "
                    f"{dataset}/seed_{seed}/epoch_{epoch}"
                )


            loss.backward()


            torch.nn.utils.clip_grad_norm_(
                model.parameters(),
                max_norm=GRADIENT_CLIP,
            )


            optimizer.step()


            batch_n = int(
                len(
                    batch_indices
                )
            )


            samples_seen += (
                batch_n
            )


            running_total += (
                float(
                    losses[
                        "loss"
                    ].detach()
                )
                *
                batch_n
            )


            running_clean += (
                float(
                    losses[
                        "clean_ce"
                    ].detach()
                )
                *
                batch_n
            )


            running_fault += (
                float(
                    losses[
                        "fault_ce"
                    ].detach()
                )
                *
                batch_n
            )


            running_consistency += (
                float(
                    losses[
                        "consistency"
                    ].detach()
                )
                *
                batch_n
            )


        if samples_seen != n_train:

            raise RuntimeError(
                "Training cardinality mismatch"
            )


        metrics = evaluate_validation_only(
            model=model,
            dataset=dataset,
            raw_val=data[
                "X_val_raw"
            ],
            y_val=data[
                "y_val"
            ],
            train_mean=data[
                "train_mean"
            ],
            train_std=data[
                "train_std"
            ],
            num_classes=num_classes,
            device=DEVICE,
            batch_size=BATCH_SIZE,
        )


        score = float(
            metrics[
                "selection_score"
            ]
        )


        improved = (
            score
            >
            best_score
        )


        if improved:

            best_score = score

            best_epoch = epoch


            best_metrics = {
                "clean_macro_f1":
                    float(
                        metrics[
                            "clean_macro_f1"
                        ]
                    ),

                "all_recoverable_fault_macro_f1":
                    float(
                        metrics[
                            "all_recoverable_fault_macro_f1"
                        ]
                    ),

                "family_balanced_macro_f1":
                    float(
                        metrics[
                            "family_balanced_macro_f1"
                        ]
                    ),

                "selection_score":
                    score,
            }


            save_state_dict_cpu(
                model,
                best_path,
            )


            write_csv(
                run_dir
                / "best_validation_condition_metrics_16.csv",
                metrics[
                    "condition_rows"
                ],
            )


            epochs_without_improvement = 0

        else:

            epochs_without_improvement += 1


        epoch_seconds = (
            time.perf_counter()
            -
            epoch_start
        )


        history.append({
            "epoch":
                epoch,

            "train_total_loss":
                running_total
                /
                n_train,

            "train_clean_ce":
                running_clean
                /
                n_train,

            "train_fault_ce":
                running_fault
                /
                n_train,

            "train_consistency":
                running_consistency
                /
                n_train,

            "val_clean_macro_f1":
                metrics[
                    "clean_macro_f1"
                ],

            "val_all_recoverable_fault_macro_f1":
                metrics[
                    "all_recoverable_fault_macro_f1"
                ],

            "val_family_balanced_macro_f1":
                metrics[
                    "family_balanced_macro_f1"
                ],

            "val_selection_score":
                score,

            "best_selection_score_so_far":
                best_score,

            "best_epoch_so_far":
                best_epoch,

            "improved":
                improved,

            "epochs_without_improvement":
                epochs_without_improvement,

            "epoch_seconds":
                epoch_seconds,
        })


        write_csv(
            run_dir
            / "history.csv",
            history,
        )


        print(
            "V26_CONFIRM_EPOCH:",
            dataset,
            seed,
            f"EPOCH={epoch}",
            "TRAIN_LOSS=",
            f"{running_total/n_train:.6f}",
            "VAL_CLEAN_F1=",
            f"{metrics['clean_macro_f1']:.6f}",
            "VAL_REC_F1=",
            f"{metrics['all_recoverable_fault_macro_f1']:.6f}",
            "VAL_FB_F1=",
            f"{metrics['family_balanced_macro_f1']:.6f}",
            "SCORE=",
            f"{score:.6f}",
            "BEST=",
            f"{best_score:.6f}",
            "PATIENCE=",
            f"{epochs_without_improvement}/{PATIENCE}",
            flush=True,
        )


        if (
            epochs_without_improvement
            >=
            PATIENCE
        ):

            break


    if not best_path.exists():

        raise RuntimeError(
            "Best checkpoint not saved"
        )


    if (
        best_epoch is None
        or
        best_metrics is None
    ):

        raise RuntimeError(
            "Best validation result missing"
        )


    # ========================================================
    # Reload exact best checkpoint and reproduce validation.
    # Still no protected test evaluation.
    # ========================================================

    state = load_direct_state_dict(
        best_path
    )


    incompatible = model.load_state_dict(
        state,
        strict=True,
    )


    if (
        list(
            incompatible.missing_keys
        )
        or
        list(
            incompatible.unexpected_keys
        )
    ):

        raise RuntimeError(
            "Strict best-checkpoint reload failed"
        )


    model.eval()


    reproduced = evaluate_validation_only(
        model=model,
        dataset=dataset,
        raw_val=data[
            "X_val_raw"
        ],
        y_val=data[
            "y_val"
        ],
        train_mean=data[
            "train_mean"
        ],
        train_std=data[
            "train_std"
        ],
        num_classes=num_classes,
        device=DEVICE,
        batch_size=BATCH_SIZE,
    )


    for metric in [
        "clean_macro_f1",
        "all_recoverable_fault_macro_f1",
        "family_balanced_macro_f1",
        "selection_score",
    ]:

        error = abs(
            float(
                reproduced[
                    metric
                ]
            )
            -
            float(
                best_metrics[
                    metric
                ]
            )
        )


        if error > 1e-12:

            raise RuntimeError(
                f"Best checkpoint validation "
                f"reproduction failure: "
                f"{dataset}/seed_{seed}/{metric}; "
                f"error={error}"
            )


    elapsed = (
        time.perf_counter()
        -
        start_time
    )


    result = {
        "candidate_id":
            PROMOTED,

        "dataset":
            dataset,

        "seed":
            seed,

        "num_classes":
            num_classes,

        "parameter_count":
            params,

        "epochs_completed":
            len(
                history
            ),

        "best_epoch":
            best_epoch,

        "best_model":
            str(
                best_path.relative_to(
                    ROOT
                )
            ),

        "best_model_sha256":
            sha256_file(
                best_path
            ),

        "val_clean_macro_f1":
            best_metrics[
                "clean_macro_f1"
            ],

        "val_all_recoverable_fault_macro_f1":
            best_metrics[
                "all_recoverable_fault_macro_f1"
            ],

        "val_family_balanced_macro_f1":
            best_metrics[
                "family_balanced_macro_f1"
            ],

        "val_selection_score":
            best_metrics[
                "selection_score"
            ],

        "training_elapsed_seconds":
            elapsed,

        "best_checkpoint_validation_reproduced":
            True,

        "protected_test_inference_performed":
            False,

        "storm_inference_performed":
            False,
    }


    write_json(
        run_dir
        / "run_receipt.json",
        result,
    )


    print(
        "V26_CONFIRM_RUN_COMPLETE:",
        dataset,
        seed,
        "BEST_EPOCH=",
        best_epoch,
        "PARAMS=",
        params,
        "VAL_CLEAN_F1=",
        f"{best_metrics['clean_macro_f1']:.9f}",
        "VAL_REC_F1=",
        f"{best_metrics['all_recoverable_fault_macro_f1']:.9f}",
        "VAL_FB_F1=",
        f"{best_metrics['family_balanced_macro_f1']:.9f}",
        "SCORE=",
        f"{best_metrics['selection_score']:.9f}",
        "SHA=",
        result[
            "best_model_sha256"
        ],
        flush=True,
    )


    del state
    del optimizer
    del model

    gc.collect()

    torch.cuda.empty_cache()


    return result


# ============================================================
# 5. Execute exactly the frozen 14 runs
# ============================================================

results = []


for run_index, row in enumerate(
    manifest,
    start=1,
):

    dataset = row[
        "dataset"
    ]

    seed = int(
        row[
            "seed"
        ]
    )


    print()
    print("=" * 118)

    print(
        f"V26_CONFIRMATION_TRAINING_RUN="
        f"{run_index}/14",
        "DATASET=",
        dataset,
        "SEED=",
        seed,
        "CANDIDATE=",
        PROMOTED,
        flush=True,
    )

    print("=" * 118)


    result = train_one_confirmation_run(
        dataset,
        seed,
    )


    results.append(
        result
    )


    write_csv(
        OUT
        / "confirmation_training_partial.csv",
        results,
    )


if len(
    results
) != 14:

    raise RuntimeError(
        f"Expected 14 completed runs, "
        f"found {len(results)}"
    )


write_csv(
    OUT
    / "confirmation_training_runs_14.csv",
    results,
)


partial = (
    OUT
    / "confirmation_training_partial.csv"
)


if partial.exists():

    partial.unlink()


print(
    "V26_CONFIRMATION_TRAINING_RUNS_PASS_14_OF_14=True"
)


# ============================================================
# 6. Freeze checkpoint manifest BEFORE any protected test use
# ============================================================

checkpoint_manifest = []


for row in results:

    path = (
        ROOT
        / row[
            "best_model"
        ]
    )


    if not path.exists():

        raise FileNotFoundError(
            path
        )


    actual_sha = sha256_file(
        path
    )


    if (
        actual_sha
        !=
        row[
            "best_model_sha256"
        ]
    ):

        raise RuntimeError(
            f"Checkpoint SHA changed: {path}"
        )


    checkpoint_manifest.append({
        "candidate_id":
            PROMOTED,

        "dataset":
            row[
                "dataset"
            ],

        "seed":
            row[
                "seed"
            ],

        "num_classes":
            row[
                "num_classes"
            ],

        "parameter_count":
            row[
                "parameter_count"
            ],

        "best_epoch":
            row[
                "best_epoch"
            ],

        "checkpoint":
            row[
                "best_model"
            ],

        "checkpoint_sha256":
            actual_sha,
    })


if len(
    checkpoint_manifest
) != 14:

    raise RuntimeError(
        "Checkpoint manifest cardinality != 14"
    )


if len(
    {
        (
            row[
                "dataset"
            ],
            int(
                row[
                    "seed"
                ]
            ),
        )
        for row in checkpoint_manifest
    }
) != 14:

    raise RuntimeError(
        "Checkpoint identity set not unique"
    )


write_csv(
    OUT
    / "frozen_confirmation_checkpoint_manifest_14.csv",
    checkpoint_manifest,
)


print(
    "V26_CONFIRMATION_CHECKPOINT_SHA_PASS_14_OF_14=True"
)


# ============================================================
# 7. Descriptive validation summary only
#
# Does NOT affect model selection or tuning.
# ============================================================

summary_rows = []


for dataset in datasets:

    subset = [
        row
        for row in results
        if row[
            "dataset"
        ]
        ==
        dataset
    ]


    if not subset:
        continue


    summary_rows.append({
        "dataset":
            dataset,

        "n_confirmation_seeds":
            len(
                subset
            ),

        "mean_val_clean_macro_f1":
            float(
                np.mean(
                    [
                        row[
                            "val_clean_macro_f1"
                        ]
                        for row in subset
                    ]
                )
            ),

        "mean_val_all_recoverable_fault_macro_f1":
            float(
                np.mean(
                    [
                        row[
                            "val_all_recoverable_fault_macro_f1"
                        ]
                        for row in subset
                    ]
                )
            ),

        "mean_val_family_balanced_macro_f1":
            float(
                np.mean(
                    [
                        row[
                            "val_family_balanced_macro_f1"
                        ]
                        for row in subset
                    ]
                )
            ),

        "mean_val_selection_score":
            float(
                np.mean(
                    [
                        row[
                            "val_selection_score"
                        ]
                        for row in subset
                    ]
                )
            ),
    })


write_csv(
    OUT
    / "confirmation_validation_summary_4.csv",
    summary_rows,
)


# ============================================================
# 8. Final training receipt
# ============================================================

receipt = {
    "stage":
        "V26_PRIMARY_CONFIRMATION_TRAINING_R5",

    "status":
        "PASS",

    "promoted_candidate":
        PROMOTED,

    "confirmation_training_manifest":
        "PASS_14_OF_14",

    "confirmation_training_runs":
        "PASS_14_OF_14",

    "confirmation_checkpoints":
        "FROZEN_SHA_PASS_14_OF_14",

    "training_datasets": [
        "UCI_HAR",
        "PAMAP2",
        "DSADS",
        "MotionSense",
    ],

    "training_run_count":
        14,

    "train_only_normalization":
        "PASS_4_OF_4",

    "optimizer":
        "AdamW",

    "learning_rate":
        1e-3,

    "weight_decay":
        1e-4,

    "batch_size":
        64,

    "max_epochs":
        100,

    "early_stopping_patience":
        15,

    "gradient_clipping_norm":
        1.0,

    "physical_pre_normalization_training":
        True,

    "corrupted_classification_gradient":
        True,

    "consistency_weight":
        0.20,

    "validation_only_checkpoint_selection":
        True,

    "validation_fault_count":
        16,

    "validation_randomness_root":
        26001,

    "candidate_modified":
        False,

    "training_protocol_modified":
        False,

    "fault_protocol_modified":
        False,

    "loss_weight_modified":
        False,

    "protected_test_split_loaded":
        False,

    "protected_test_inference_performed":
        False,

    "storm_inference_performed":
        False,

    "storm_used_for_selection":
        False,

    "all_14_checkpoints_frozen_before_test":
        True,

    "next_gate":
        (
            "Verify frozen R5 checkpoint manifest and source "
            "integrity. Then unlock exactly one protected "
            "252-row Stage25 physical pre-normalization "
            "confirmation evaluation. No retraining or "
            "hyperparameter changes are allowed afterward."
        ),
}


write_json(
    OUT
    / "v26_primary_confirmation_training_receipt_r5.json",
    receipt,
)


print()
print("=" * 118)
print("V26 PRIMARY CONFIRMATION TRAINING R5 FINAL RECEIPT")
print("=" * 118)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)

print()
print(
    "V26_PRIMARY_CONFIRMATION_TRAINING_R5_PASS=True"
)

print(
    "V26_CONFIRMATION_TRAINING_RUNS_PASS_14_OF_14=True"
)

print(
    "V26_CONFIRMATION_CHECKPOINT_SHA_PASS_14_OF_14=True"
)

print(
    "ALL_14_CHECKPOINTS_FROZEN_BEFORE_TEST=True"
)

print(
    "PROTECTED_TEST_SPLIT_LOADED=False"
)

print(
    "PROTECTED_TEST_INFERENCE_PERFORMED=False"
)

print(
    "STORM_USED_FOR_SELECTION=False"
)
