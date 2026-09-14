from __future__ import annotations

import csv
import gc
import hashlib
import json
import math
import os
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

PROTO = (
    ROOT
    / "results"
    / "v26_development_protocol_r1"
)

IMPL = (
    ROOT
    / "results"
    / "v26_implementation_integrity_r2"
)

STAGE25_R3 = (
    ROOT
    / "results"
    / "stage25_physical_fault_protocol"
    / "protocol_preregistration_r3"
)

OUT = (
    ROOT
    / "results"
    / "v26_development_screening_r3"
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
    CANDIDATE_IDS,
    create_v26_candidate,
    parameter_count,
)

from development_data_r2 import (
    load_development_train_val,
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


DEVICE = torch.device(
    "cuda:0"
)

DEVELOPMENT_DATASETS = [
    "UCI_HAR",
    "DSADS",
]

DEVELOPMENT_SEEDS = [
    42,
    123,
    456,
]

EXPECTED_RUNS = 24

BATCH_SIZE = 64
MAX_EPOCHS = 100
PATIENCE = 15

LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4
GRADIENT_CLIP = 1.0

PARAMETER_CEILING = 60000

V25_BASELINE_MODEL = (
    "ReliabilityCNN_v25"
)

V25_ARCH_CANDIDATE = (
    "V26A_V25_PhysCE"
)


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

    with path.open("rb") as f:

        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):

            h.update(block)

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


def load_direct_state_dict(
    path: Path,
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
            f"{path}: checkpoint is not dict"
        )


    if not state:

        raise RuntimeError(
            f"{path}: empty checkpoint"
        )


    if not all(
        torch.is_tensor(
            value
        )
        for value in state.values()
    ):

        raise RuntimeError(
            f"{path}: checkpoint is not "
            "direct tensor state_dict"
        )


    return state


def save_state_dict_cpu(
    model,
    path: Path,
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


print("=" * 118)
print("V26 DEVELOPMENT SCREENING R3")
print("VALIDATION-ONLY MODEL SELECTION")
print("NO TEST INFERENCE / NO STORM SELECTION")
print("=" * 118)


if not torch.cuda.is_available():

    raise RuntimeError(
        "CUDA unavailable. "
        "Classify environment failure "
        "before changing protocol."
    )


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


torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True


# ============================================================
# 1. Frozen protocol receipts
# ============================================================

protocol_receipt = json.loads(
    (
        PROTO
        / "v26_development_protocol_receipt_r1.json"
    ).read_text()
)

implementation_receipt = json.loads(
    (
        IMPL
        / "v26_implementation_integrity_receipt_r2.json"
    ).read_text()
)


if (
    protocol_receipt.get(
        "status"
    )
    !=
    "FROZEN_BEFORE_NEW_MODEL_TRAINING"
):

    raise RuntimeError(
        "V26 protocol prerequisite failed"
    )


if (
    implementation_receipt.get(
        "status"
    )
    !=
    "PASS"
):

    raise RuntimeError(
        "V26 implementation prerequisite failed"
    )


if (
    protocol_receipt.get(
        "maximum_screening_runs"
    )
    !=
    24
):

    raise RuntimeError(
        "Frozen screening run count changed"
    )


if (
    protocol_receipt.get(
        "candidate_selection_uses_test_data"
    )
    is not False
):

    raise RuntimeError(
        "Test-access policy mismatch"
    )


if (
    protocol_receipt.get(
        "candidate_selection_uses_storm"
    )
    is not False
):

    raise RuntimeError(
        "STORM-access policy mismatch"
    )


print(
    "FROZEN_PROTOCOL_IMPLEMENTATION_PREREQUISITES_PASS=True"
)


# ============================================================
# 2. Bind six frozen V25 development checkpoints
# ============================================================

bank_path = (
    STAGE25_R3
    / "frozen_model_bank_200.csv"
)


with bank_path.open(
    newline="",
    encoding="utf-8",
) as f:

    bank = list(
        csv.DictReader(f)
    )


baseline_rows = []


for dataset in DEVELOPMENT_DATASETS:

    for seed in DEVELOPMENT_SEEDS:

        matches = [
            row
            for row in bank
            if (
                row[
                    "dataset"
                ]
                ==
                dataset
                and
                row[
                    "model"
                ]
                ==
                V25_BASELINE_MODEL
                and
                int(
                    row[
                        "seed"
                    ]
                )
                ==
                seed
            )
        ]


        if len(
            matches
        ) != 1:

            raise RuntimeError(
                f"Expected unique frozen V25 "
                f"checkpoint for "
                f"{dataset}/seed_{seed}; "
                f"found {len(matches)}"
            )


        row = matches[0]

        checkpoint = (
            ROOT
            / row[
                "checkpoint"
            ]
        )


        if not checkpoint.exists():

            raise FileNotFoundError(
                checkpoint
            )


        actual_sha = sha256_file(
            checkpoint
        )


        if (
            actual_sha
            !=
            row[
                "checkpoint_sha256"
            ]
        ):

            raise RuntimeError(
                f"Frozen V25 checkpoint SHA changed: "
                f"{dataset}/seed_{seed}"
            )


        baseline_rows.append({
            "dataset":
                dataset,

            "seed":
                seed,

            "checkpoint":
                row[
                    "checkpoint"
                ],

            "checkpoint_sha256":
                row[
                    "checkpoint_sha256"
                ],
        })


if len(
    baseline_rows
) != 6:

    raise RuntimeError(
        "Expected six frozen V25 development checkpoints"
    )


print(
    "FROZEN_V25_DEVELOPMENT_BASELINE_BOUND_6_OF_6=True"
)


# ============================================================
# 3. Cache development train/validation data
#
# This loader physically cannot access test_idx.
# ============================================================

data_cache = {}


for dataset in DEVELOPMENT_DATASETS:

    data_cache[
        dataset
    ] = load_development_train_val(
        dataset
    )


print(
    "DEVELOPMENT_DATA_LOADED_TRAIN_VAL_ONLY_2_OF_2=True"
)


# ============================================================
# 4. Evaluate frozen V25 baseline on EXACT new validation
#    protocol.
#
# This is validation-only inference.
# ============================================================

baseline_validation = []


for baseline in baseline_rows:

    dataset = baseline[
        "dataset"
    ]

    seed = baseline[
        "seed"
    ]

    data = data_cache[
        dataset
    ]

    num_classes = int(
        data[
            "num_classes"
        ]
    )


    model = create_v26_candidate(
        V25_ARCH_CANDIDATE,
        num_classes,
        input_channels=6,
    )


    state = load_direct_state_dict(
        ROOT
        / baseline[
            "checkpoint"
        ]
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
            "Frozen V25 baseline strict load failed"
        )


    model = model.to(
        DEVICE
    )

    model.eval()


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


    baseline_validation.append({
        "dataset":
            dataset,

        "seed":
            seed,

        "checkpoint":
            baseline[
                "checkpoint"
            ],

        "checkpoint_sha256":
            baseline[
                "checkpoint_sha256"
            ],

        "parameter_count":
            parameter_count(
                model
            ),

        "clean_macro_f1":
            metrics[
                "clean_macro_f1"
            ],

        "all_recoverable_fault_macro_f1":
            metrics[
                "all_recoverable_fault_macro_f1"
            ],

        "family_balanced_macro_f1":
            metrics[
                "family_balanced_macro_f1"
            ],

        "selection_score":
            metrics[
                "selection_score"
            ],
    })


    run_dir = (
        OUT
        / "v25_validation_baseline"
        / dataset
        / f"seed_{seed}"
    )

    run_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    write_csv(
        run_dir
        / "condition_metrics_16.csv",
        metrics[
            "condition_rows"
        ],
    )


    print(
        "V25_BASELINE_VALIDATION:",
        dataset,
        seed,
        "CLEAN_F1=",
        f"{metrics['clean_macro_f1']:.9f}",
        "RECOVERABLE_F1=",
        f"{metrics['all_recoverable_fault_macro_f1']:.9f}",
        "FAMILY_BAL_F1=",
        f"{metrics['family_balanced_macro_f1']:.9f}",
        "SCORE=",
        f"{metrics['selection_score']:.9f}",
        flush=True,
    )


    del state
    del model

    gc.collect()
    torch.cuda.empty_cache()


write_csv(
    OUT
    / "frozen_v25_validation_baseline_6.csv",
    baseline_validation,
)


if len(
    baseline_validation
) != 6:

    raise RuntimeError(
        "Frozen V25 validation baseline count != 6"
    )


print(
    "FROZEN_V25_VALIDATION_BASELINE_PASS_6_OF_6=True"
)


baseline_lookup = {
    (
        row[
            "dataset"
        ],
        int(
            row[
                "seed"
            ]
        ),
    ):
        row

    for row in baseline_validation
}


# ============================================================
# 5. Train one preregistered development run
# ============================================================

def train_one_run(
    candidate_id,
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
        / candidate_id
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
        candidate_id,
        num_classes,
        input_channels=6,
    )


    params = parameter_count(
        model
    )


    if params > PARAMETER_CEILING:

        raise RuntimeError(
            f"{candidate_id}/{dataset}: "
            f"parameter ceiling exceeded: "
            f"{params}"
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


    run_start = time.perf_counter()


    for epoch in range(
        1,
        MAX_EPOCHS + 1,
    ):

        epoch_start = (
            time.perf_counter()
        )


        model.train()


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


            # Frozen R3 choice:
            # separate clean and fault forwards.
            # Both contribute gradients.
            clean_logits = model(
                clean_x
            )

            fault_logits = model(
                fault_x
            )


            losses = candidate_training_loss(
                candidate_id,
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
                    f"Non-finite loss: "
                    f"{candidate_id}/"
                    f"{dataset}/seed_{seed}/"
                    f"epoch_{epoch}"
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


            samples_seen += batch_n


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
                "Training sample-count mismatch"
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
                / "best_condition_metrics_16.csv",
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
            "V26_EPOCH:",
            candidate_id,
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
            "Best checkpoint was never saved"
        )


    if (
        best_epoch is None
        or
        best_metrics is None
    ):

        raise RuntimeError(
            "Best validation metrics missing"
        )


    # --------------------------------------------------------
    # Exact best-checkpoint validation reproduction
    # --------------------------------------------------------

    best_state = load_direct_state_dict(
        best_path
    )


    incompatible = model.load_state_dict(
        best_state,
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
            "Saved best checkpoint strict reload failed"
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
                f"Best validation reproduction failed: "
                f"{candidate_id}/{dataset}/seed_{seed}/"
                f"{metric}; error={error}"
            )


    baseline = baseline_lookup[
        (
            dataset,
            seed,
        )
    ]


    elapsed = (
        time.perf_counter()
        -
        run_start
    )


    result = {
        "candidate_id":
            candidate_id,

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

        "clean_macro_f1":
            best_metrics[
                "clean_macro_f1"
            ],

        "all_recoverable_fault_macro_f1":
            best_metrics[
                "all_recoverable_fault_macro_f1"
            ],

        "family_balanced_macro_f1":
            best_metrics[
                "family_balanced_macro_f1"
            ],

        "selection_score":
            best_metrics[
                "selection_score"
            ],

        "baseline_v25_clean_macro_f1":
            baseline[
                "clean_macro_f1"
            ],

        "baseline_v25_all_recoverable_fault_macro_f1":
            baseline[
                "all_recoverable_fault_macro_f1"
            ],

        "baseline_v25_family_balanced_macro_f1":
            baseline[
                "family_balanced_macro_f1"
            ],

        "baseline_v25_selection_score":
            baseline[
                "selection_score"
            ],

        "delta_clean_macro_f1_vs_v25":
            (
                best_metrics[
                    "clean_macro_f1"
                ]
                -
                baseline[
                    "clean_macro_f1"
                ]
            ),

        "delta_all_recoverable_fault_macro_f1_vs_v25":
            (
                best_metrics[
                    "all_recoverable_fault_macro_f1"
                ]
                -
                baseline[
                    "all_recoverable_fault_macro_f1"
                ]
            ),

        "delta_family_balanced_macro_f1_vs_v25":
            (
                best_metrics[
                    "family_balanced_macro_f1"
                ]
                -
                baseline[
                    "family_balanced_macro_f1"
                ]
            ),

        "delta_selection_score_vs_v25":
            (
                best_metrics[
                    "selection_score"
                ]
                -
                baseline[
                    "selection_score"
                ]
            ),

        "training_elapsed_seconds":
            elapsed,

        "best_checkpoint_validation_reproduced":
            True,

        "test_inference_performed":
            False,

        "storm_used_for_selection":
            False,
    }


    write_json(
        run_dir
        / "run_receipt.json",
        result,
    )


    print(
        "V26_RUN_COMPLETE:",
        candidate_id,
        dataset,
        seed,
        "BEST_EPOCH=",
        best_epoch,
        "CLEAN_F1=",
        f"{best_metrics['clean_macro_f1']:.9f}",
        "REC_F1=",
        f"{best_metrics['all_recoverable_fault_macro_f1']:.9f}",
        "FB_F1=",
        f"{best_metrics['family_balanced_macro_f1']:.9f}",
        "SCORE=",
        f"{best_metrics['selection_score']:.9f}",
        "D_CLEAN=",
        f"{result['delta_clean_macro_f1_vs_v25']:+.9f}",
        "D_REC=",
        f"{result['delta_all_recoverable_fault_macro_f1_vs_v25']:+.9f}",
        "D_FB=",
        f"{result['delta_family_balanced_macro_f1_vs_v25']:+.9f}",
        flush=True,
    )


    del best_state
    del optimizer
    del model

    gc.collect()
    torch.cuda.empty_cache()


    return result


# ============================================================
# 6. Execute exactly 24 development runs
# ============================================================

screening_results = []

run_index = 0


for candidate_id in CANDIDATE_IDS:

    for dataset in DEVELOPMENT_DATASETS:

        for seed in DEVELOPMENT_SEEDS:

            run_index += 1


            print()
            print("=" * 118)

            print(
                f"V26_SCREENING_RUN={run_index}/{EXPECTED_RUNS}",
                "CANDIDATE=",
                candidate_id,
                "DATASET=",
                dataset,
                "SEED=",
                seed,
                flush=True,
            )

            print("=" * 118)


            result = train_one_run(
                candidate_id,
                dataset,
                seed,
            )


            screening_results.append(
                result
            )


            write_csv(
                OUT
                / "screening_runs_partial.csv",
                screening_results,
            )


if run_index != EXPECTED_RUNS:

    raise RuntimeError(
        f"Expected 24 screening runs, "
        f"executed {run_index}"
    )


if len(
    screening_results
) != EXPECTED_RUNS:

    raise RuntimeError(
        "Screening result count != 24"
    )


write_csv(
    OUT
    / "screening_runs_24.csv",
    screening_results,
)


partial = (
    OUT
    / "screening_runs_partial.csv"
)

if partial.exists():

    partial.unlink()


print(
    "V26_SCREENING_TRAINING_RUNS_COMPLETE_24_OF_24=True"
)


# ============================================================
# 7. Frozen candidate promotion analysis
# ============================================================

summary_rows = []


for candidate_id in CANDIDATE_IDS:

    rows = [
        row
        for row in screening_results
        if row[
            "candidate_id"
        ]
        ==
        candidate_id
    ]


    if len(rows) != 6:

        raise RuntimeError(
            f"{candidate_id}: expected six "
            f"development runs"
        )


    mean_clean = float(
        np.mean(
            [
                row[
                    "clean_macro_f1"
                ]
                for row in rows
            ]
        )
    )

    mean_recoverable = float(
        np.mean(
            [
                row[
                    "all_recoverable_fault_macro_f1"
                ]
                for row in rows
            ]
        )
    )

    mean_family = float(
        np.mean(
            [
                row[
                    "family_balanced_macro_f1"
                ]
                for row in rows
            ]
        )
    )

    mean_score = float(
        np.mean(
            [
                row[
                    "selection_score"
                ]
                for row in rows
            ]
        )
    )


    delta_clean = float(
        np.mean(
            [
                row[
                    "delta_clean_macro_f1_vs_v25"
                ]
                for row in rows
            ]
        )
    )

    delta_recoverable = float(
        np.mean(
            [
                row[
                    "delta_all_recoverable_fault_macro_f1_vs_v25"
                ]
                for row in rows
            ]
        )
    )

    delta_family = float(
        np.mean(
            [
                row[
                    "delta_family_balanced_macro_f1_vs_v25"
                ]
                for row in rows
            ]
        )
    )

    delta_score = float(
        np.mean(
            [
                row[
                    "delta_selection_score_vs_v25"
                ]
                for row in rows
            ]
        )
    )


    max_params = int(
        max(
            row[
                "parameter_count"
            ]
            for row in rows
        )
    )


    parameter_pass = (
        max_params
        <=
        60000
    )

    clean_pass = (
        delta_clean
        >=
        -0.015
    )

    family_pass = (
        delta_family
        >=
        0.015
    )

    recoverable_pass = (
        delta_recoverable
        >=
        0.010
    )


    eligible = (
        parameter_pass
        and
        clean_pass
        and
        family_pass
        and
        recoverable_pass
    )


    summary_rows.append({
        "candidate_id":
            candidate_id,

        "n_development_runs":
            6,

        "mean_clean_macro_f1":
            mean_clean,

        "mean_all_recoverable_fault_macro_f1":
            mean_recoverable,

        "mean_family_balanced_macro_f1":
            mean_family,

        "mean_selection_score":
            mean_score,

        "mean_delta_clean_macro_f1_vs_v25":
            delta_clean,

        "mean_delta_all_recoverable_fault_macro_f1_vs_v25":
            delta_recoverable,

        "mean_delta_family_balanced_macro_f1_vs_v25":
            delta_family,

        "mean_delta_selection_score_vs_v25":
            delta_score,

        "max_parameter_count":
            max_params,

        "parameter_gate_pass":
            parameter_pass,

        "clean_delta_gate_pass":
            clean_pass,

        "recoverable_delta_gate_pass":
            recoverable_pass,

        "family_balanced_delta_gate_pass":
            family_pass,

        "promotion_eligible":
            eligible,
    })


write_csv(
    OUT
    / "candidate_development_summary_4.csv",
    summary_rows,
)


eligible = [
    row
    for row in summary_rows
    if row[
        "promotion_eligible"
    ]
]


if not eligible:

    promoted = None

    decision_reason = (
        "PROMOTE_NONE: no candidate met all "
        "preregistered minimum requirements."
    )

else:

    top_score = max(
        row[
            "mean_selection_score"
        ]
        for row in eligible
    )


    tied = [
        row
        for row in eligible
        if abs(
            row[
                "mean_selection_score"
            ]
            -
            top_score
        )
        <
        0.002
    ]


    if len(tied) == 1:

        promoted = tied[0]

        decision_reason = (
            "Highest eligible mean validation "
            "selection score."
        )

    else:

        tied = sorted(
            tied,
            key=lambda row: (
                row[
                    "max_parameter_count"
                ],
                -
                row[
                    "mean_selection_score"
                ],
                row[
                    "candidate_id"
                ],
            ),
        )

        promoted = tied[0]

        decision_reason = (
            "Eligible candidates were within "
            "the preregistered 0.002 score tie "
            "window; lower parameter count "
            "applied as tie-breaker."
        )


promotion = {
    "stage":
        "V26_DEVELOPMENT_SCREENING_R3",

    "status":
        "PASS",

    "candidate_count":
        4,

    "development_runs":
        24,

    "development_datasets": [
        "UCI_HAR",
        "DSADS",
    ],

    "development_seeds": [
        42,
        123,
        456,
    ],

    "v25_matched_validation_baselines":
        6,

    "promotion_requirements": {
        "parameter_count_max":
            60000,

        "mean_clean_macro_f1_delta_vs_v25_min":
            -0.015,

        "mean_family_balanced_macro_f1_delta_vs_v25_min":
            0.015,

        "mean_all_recoverable_fault_macro_f1_delta_vs_v25_min":
            0.010,
    },

    "eligible_candidates": [
        row[
            "candidate_id"
        ]
        for row in eligible
    ],

    "promoted_candidate": (
        None
        if promoted is None
        else
        promoted[
            "candidate_id"
        ]
    ),

    "promotion_decision":
        (
            "PROMOTE_NONE"
            if promoted is None
            else
            "PROMOTE_ONE"
        ),

    "decision_reason":
        decision_reason,

    "test_inference_performed":
        False,

    "heldout_seed_inference_performed":
        False,

    "pamap_motionsense_inference_performed":
        False,

    "storm_used_for_selection":
        False,

    "storm_inference_performed":
        False,

    "candidate_training_runs":
        24,

    "training_performed":
        True,

    "next_gate": (
        "If PROMOTE_ONE: freeze the promoted architecture "
        "and training protocol, then perform the predeclared "
        "14-checkpoint primary confirmation without further "
        "candidate tuning. "
        "If PROMOTE_NONE: freeze the negative result and "
        "preregister a new development round before any "
        "additional architecture changes."
    ),
}


write_json(
    OUT
    / "promotion_decision_r3.json",
    promotion,
)


print()
print("=" * 118)
print("V26 DEVELOPMENT CANDIDATE SUMMARY")
print("=" * 118)


for row in summary_rows:

    print(
        "V26_CANDIDATE_SUMMARY:",
        row[
            "candidate_id"
        ],
        "CLEAN_F1=",
        f"{row['mean_clean_macro_f1']:.9f}",
        "REC_F1=",
        f"{row['mean_all_recoverable_fault_macro_f1']:.9f}",
        "FB_F1=",
        f"{row['mean_family_balanced_macro_f1']:.9f}",
        "SCORE=",
        f"{row['mean_selection_score']:.9f}",
        "D_CLEAN=",
        f"{row['mean_delta_clean_macro_f1_vs_v25']:+.9f}",
        "D_REC=",
        f"{row['mean_delta_all_recoverable_fault_macro_f1_vs_v25']:+.9f}",
        "D_FB=",
        f"{row['mean_delta_family_balanced_macro_f1_vs_v25']:+.9f}",
        "PARAMS_MAX=",
        row[
            "max_parameter_count"
        ],
        "ELIGIBLE=",
        row[
            "promotion_eligible"
        ],
        flush=True,
    )


print()
print(
    "V26_PROMOTION_DECISION=",
    promotion[
        "promotion_decision"
    ],
)

print(
    "V26_PROMOTED_CANDIDATE=",
    promotion[
        "promoted_candidate"
    ],
)

print(
    "V26_ELIGIBLE_CANDIDATES=",
    ",".join(
        promotion[
            "eligible_candidates"
        ]
    )
    if promotion[
        "eligible_candidates"
    ]
    else
    "NONE",
)


# ============================================================
# 8. Final receipt
# ============================================================

receipt = {
    "stage":
        "V26_DEVELOPMENT_SCREENING_R3",

    "status":
        "PASS",

    "frozen_v25_validation_baseline":
        "PASS_6_OF_6",

    "candidate_training_runs":
        "PASS_24_OF_24",

    "candidate_summary_rows":
        4,

    "promotion_rule_applied":
        True,

    "promotion_decision":
        promotion[
            "promotion_decision"
        ],

    "promoted_candidate":
        promotion[
            "promoted_candidate"
        ],

    "training_datasets":
        [
            "UCI_HAR",
            "DSADS",
        ],

    "training_seeds":
        [
            42,
            123,
            456,
        ],

    "validation_only_model_selection":
        True,

    "test_inference_performed":
        False,

    "heldout_seed_inference_performed":
        False,

    "pamap_motionsense_inference_performed":
        False,

    "storm_used_for_selection":
        False,

    "storm_inference_performed":
        False,

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

    "candidate_training_performed":
        True,

    "candidate_checkpoints_saved":
        24,
}


write_json(
    OUT
    / "v26_development_screening_receipt_r3.json",
    receipt,
)


print()
print("=" * 118)
print("V26 DEVELOPMENT SCREENING R3 FINAL RECEIPT")
print("=" * 118)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)

print()
print(
    "V26_DEVELOPMENT_SCREENING_R3_PASS=True"
)

print(
    "FROZEN_V25_VALIDATION_BASELINE_PASS_6_OF_6=True"
)

print(
    "CANDIDATE_TRAINING_RUNS_PASS_24_OF_24=True"
)

print(
    "VALIDATION_ONLY_MODEL_SELECTION=True"
)

print(
    "TEST_INFERENCE_PERFORMED=False"
)

print(
    "HELDOUT_SEED_INFERENCE_PERFORMED=False"
)

print(
    "PAMAP_MOTIONSENSE_INFERENCE_PERFORMED=False"
)

print(
    "STORM_USED_FOR_SELECTION=False"
)
