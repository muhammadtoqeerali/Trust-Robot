from __future__ import annotations

import csv
import gc
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

SUITE = ROOT / "experiments/16_benchmark_suite"
SCREEN = ROOT / "experiments/17_v25_screening"

R2 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "canonical_reconstruction_audit_r2"
)

R3 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "protocol_preregistration_r3"
)

R4A = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "transform_provenance_preflight_r4a"
)

R4B1B = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "exact_constructor_mapping_r4b1b"
)

R4B2 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "clean_reproduction_r4b2"
)

OUT = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "paired_domain_evaluation_r5"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


DATA_ROOT = ROOT / "data/processed/harmonized"
SPLIT_ROOT = ROOT / "data/processed/splits"

DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]

DOMAINS = [
    "pre_normalization_sensor_domain",
    "post_normalization_domain",
]

V25_MODEL = "ReliabilityCNN_v25"

BATCH_SIZE = 64

EXPECTED_TOTAL_ROWS = 7000
EXPECTED_CLEAN_ROWS = 200
EXPECTED_CORRUPTED_ROWS = 6800
EXPECTED_TENSOR_HASHES = 140


def sha256_file(path: Path) -> str:

    h = hashlib.sha256()

    with path.open("rb") as f:

        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def sha256_array(arr: np.ndarray) -> str:

    arr = np.ascontiguousarray(arr)

    h = hashlib.sha256()

    h.update(
        str(arr.shape).encode("utf-8")
    )

    h.update(
        str(arr.dtype).encode("utf-8")
    )

    h.update(
        arr.tobytes(order="C")
    )

    return h.hexdigest()


def sha256_int64(values) -> str:

    arr = np.ascontiguousarray(
        np.asarray(
            values,
            dtype=np.int64,
        )
    )

    h = hashlib.sha256()

    h.update(
        str(arr.shape).encode("utf-8")
    )

    h.update(arr.tobytes())

    return h.hexdigest()


def write_json(path: Path, obj):

    path.write_text(
        json.dumps(
            obj,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n"
    )


def write_csv(path: Path, rows):

    if not rows:
        return

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
        )

        writer.writeheader()
        writer.writerows(rows)


def normalize(raw, mean, std):

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


def apply_stuck(
    x,
    channels,
    tau,
):

    out = np.array(
        x,
        copy=True,
    )

    for i in range(
        out.shape[0]
    ):

        t = int(
            tau[i]
        )

        stuck_value = np.asarray(
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
        ] = stuck_value.reshape(
            1,
            -1,
        )

    return out


# ============================================================
# Controlled imports
# ============================================================

os.chdir(ROOT)

sys.path.insert(
    0,
    str(SUITE),
)

sys.path.insert(
    0,
    str(SCREEN),
)

import torch

from sklearn.metrics import (
    accuracy_score,
    f1_score,
)

from torch.utils.data import (
    DataLoader,
    TensorDataset,
)

from engine.dataset_v3r1 import (
    load_dataset_v3r1,
)

from engine.model_registry import (
    create_model,
)

from engine.model_forward import (
    model_forward,
)

from v25_candidates import (
    create_candidate,
)


print("=" * 118)
print("STAGE25 R5 FROZEN PAIRED-DOMAIN EVALUATION")
print("200 CLEAN BASELINES + 6800 CORRUPTED FORWARDS")
print("NO TRAINING / NO TUNING / NO CONDITION CHANGES")
print("=" * 118)

print("PYTHON_VERSION=", sys.version.replace("\n", " "))
print("TORCH_VERSION=", torch.__version__)
print("CUDA_AVAILABLE=", torch.cuda.is_available())


if not torch.cuda.is_available():

    raise RuntimeError(
        "CUDA unavailable. Classify environment failure "
        "before modifying evaluator."
    )


device = torch.device(
    "cuda:0"
)

print("DEVICE=", device)
print(
    "GPU_NAME=",
    torch.cuda.get_device_name(0),
)


torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True


# ============================================================
# 1. Frozen prerequisite receipts
# ============================================================

r3_receipt = json.loads(
    (
        R3
        / "stage25_protocol_preregistration_receipt_r3.json"
    ).read_text()
)

r4a_receipt = json.loads(
    (
        R4A
        / "stage25_transform_provenance_preflight_receipt_r4a.json"
    ).read_text()
)

r4b2_receipt = json.loads(
    (
        R4B2
        / "stage25_clean_reproduction_receipt_r4b2.json"
    ).read_text()
)


if (
    r3_receipt.get("status") != "PASS"
    or
    r3_receipt.get(
        "protocol_frozen_before_corrupted_inference"
    )
    is not True
):
    raise RuntimeError(
        "R3 frozen protocol prerequisite failed"
    )


if (
    r4a_receipt.get("status") != "PASS"
    or
    r4a_receipt.get(
        "dataset_condition_tensor_manifest"
    )
    !=
    "PASS_140"
    or
    r4a_receipt.get(
        "commutation_controls"
    )
    !=
    "PASS_16_OF_16"
):
    raise RuntimeError(
        "R4A transform prerequisite failed"
    )


if (
    r4b2_receipt.get("status") != "PASS"
    or
    r4b2_receipt.get(
        "clean_reproduction"
    )
    !=
    "PASS_200_OF_200"
    or
    float(
        r4b2_receipt.get(
            "max_accuracy_abs_error"
        )
    )
    != 0.0
    or
    float(
        r4b2_receipt.get(
            "max_macro_f1_abs_error"
        )
    )
    != 0.0
):
    raise RuntimeError(
        "R4B2 exact clean reproduction prerequisite failed"
    )


print(
    "R5_PREREQUISITE_RECEIPTS_PASS=True"
)


# ============================================================
# 2. Frozen protocol + normalization + seeds
# ============================================================

protocol = json.loads(
    (
        R3
        / "stage25_physical_fault_protocol_r3.json"
    ).read_text()
)

normalization = json.loads(
    (
        R2
        / "dataset_normalization_receipts.json"
    ).read_text()
)

faults = protocol[
    "fault_conditions"
]


if len(faults) != 17:

    raise RuntimeError(
        f"Expected 17 frozen faults, found {len(faults)}"
    )


with (
    R3
    / "stochastic_fault_seed_manifest_24.csv"
).open(
    newline="",
    encoding="utf-8",
) as f:

    seed_rows = list(
        csv.DictReader(f)
    )


seed_lookup = {
    (
        row["dataset"],
        row["condition"],
    ):
        int(row["seed"])

    for row in seed_rows
}


if len(seed_lookup) != 24:

    raise RuntimeError(
        "Frozen stochastic seed binding count changed"
    )


print(
    "FROZEN_FAULT_PROTOCOL_BOUND_17=True"
)

print(
    "FROZEN_STOCHASTIC_BINDINGS_BOUND_24=True"
)


# ============================================================
# 3. Frozen R4A tensor hashes
# ============================================================

with (
    R4A
    / "dataset_condition_tensor_manifest_140.csv"
).open(
    newline="",
    encoding="utf-8",
) as f:

    tensor_manifest = list(
        csv.DictReader(f)
    )


if len(tensor_manifest) != 140:

    raise RuntimeError(
        f"Expected 140 frozen tensor hashes, "
        f"found {len(tensor_manifest)}"
    )


expected_tensor_sha = {
    (
        row["dataset"],
        row["condition"],
        row["domain"],
    ):
        row["tensor_sha256"]

    for row in tensor_manifest
}


if len(expected_tensor_sha) != 140:

    raise RuntimeError(
        "Duplicate frozen tensor identity"
    )


print(
    "R4A_TENSOR_HASH_MANIFEST_BOUND_140=True"
)


# ============================================================
# 4. Frozen 200-checkpoint plan + exact clean rows
# ============================================================

with (
    R4B1B
    / "clean_reproduction_plan_200.csv"
).open(
    newline="",
    encoding="utf-8",
) as f:

    model_plan = list(
        csv.DictReader(f)
    )


with (
    R4B2
    / "clean_reproduction_cases_200.csv"
).open(
    newline="",
    encoding="utf-8",
) as f:

    clean_cases = list(
        csv.DictReader(f)
    )


if len(model_plan) != 200:

    raise RuntimeError(
        "Frozen model plan is not 200"
    )


if len(clean_cases) != 200:

    raise RuntimeError(
        "Frozen exact-clean result set is not 200"
    )


clean_lookup = {
    (
        row["dataset"],
        row["model"],
        int(row["seed"]),
    ):
        row

    for row in clean_cases
}


if len(clean_lookup) != 200:

    raise RuntimeError(
        "Duplicate R4B2 clean identity"
    )


for row in model_plan:

    key = (
        row["dataset"],
        row["model"],
        int(row["seed"]),
    )

    if key not in clean_lookup:

        raise RuntimeError(
            f"Missing R4B2 clean case: {key}"
        )


print(
    "R5_MODEL_BANK_BOUND_200_OF_200=True"
)

print(
    "R5_EXACT_CLEAN_BASELINES_BOUND_200_OF_200=True"
)


# ============================================================
# 5. Re-verify checkpoint and constructor SHAs
# ============================================================

for row in model_plan:

    checkpoint = (
        ROOT
        / row["checkpoint"]
    )

    constructor_source = (
        ROOT
        / row["constructor_source_file"]
    )


    if (
        sha256_file(checkpoint)
        !=
        row["checkpoint_sha256"]
    ):

        raise RuntimeError(
            f"Checkpoint changed: {checkpoint}"
        )


    if (
        sha256_file(
            constructor_source
        )
        !=
        row[
            "constructor_source_sha256"
        ]
    ):

        raise RuntimeError(
            f"Constructor source changed: "
            f"{constructor_source}"
        )


print(
    "R5_CHECKPOINT_CONSTRUCTOR_SHA_PASS_200_OF_200=True"
)


# ============================================================
# 6. Strict model helpers
# ============================================================

def load_state(
    checkpoint: Path,
):

    try:

        state = torch.load(
            checkpoint,
            map_location="cpu",
            weights_only=True,
        )

    except TypeError:

        state = torch.load(
            checkpoint,
            map_location="cpu",
        )


    if not isinstance(
        state,
        dict,
    ):

        raise RuntimeError(
            f"{checkpoint}: checkpoint not dict"
        )


    if not state:

        raise RuntimeError(
            f"{checkpoint}: empty checkpoint"
        )


    if not all(
        torch.is_tensor(x)
        for x in state.values()
    ):

        raise RuntimeError(
            f"{checkpoint}: not direct tensor state_dict"
        )


    return state


def forward_case(
    model,
    x,
    model_name,
):

    if model_name == V25_MODEL:

        logits = model(x)

    else:

        logits = model_forward(
            model,
            x,
        )


    if isinstance(
        logits,
        (
            tuple,
            list,
        ),
    ):

        logits = logits[0]


    if not torch.is_tensor(logits):

        raise RuntimeError(
            f"{model_name}: forward returned "
            f"{type(logits)}"
        )


    return logits


def evaluate_loader(
    model,
    model_name,
    loader,
    num_classes,
):

    predictions = []
    labels = []


    with torch.inference_mode():

        for x, y in loader:

            x = x.to(
                device,
                non_blocking=True,
            )

            logits = forward_case(
                model,
                x,
                model_name,
            )


            if (
                logits.ndim != 2
                or
                logits.shape[1]
                != num_classes
            ):

                raise RuntimeError(
                    f"{model_name}: invalid logits "
                    f"{tuple(logits.shape)}"
                )


            pred = torch.argmax(
                logits,
                dim=1,
            )


            predictions.extend(
                pred.detach()
                .cpu()
                .numpy()
                .astype(
                    np.int64,
                    copy=False,
                )
                .tolist()
            )

            labels.extend(
                y.detach()
                .cpu()
                .numpy()
                .astype(
                    np.int64,
                    copy=False,
                )
                .tolist()
            )


    y_true = np.asarray(
        labels,
        dtype=np.int64,
    )

    y_pred = np.asarray(
        predictions,
        dtype=np.int64,
    )


    accuracy = float(
        accuracy_score(
            y_true,
            y_pred,
        )
    )

    macro_f1 = float(
        f1_score(
            y_true,
            y_pred,
            labels=list(
                range(num_classes)
            ),
            average="macro",
            zero_division=0,
        )
    )


    return (
        accuracy,
        macro_f1,
        sha256_int64(y_pred),
        len(y_true),
    )


# ============================================================
# 7. Build exact R4A tensors for one dataset
# ============================================================

def build_dataset_tensors(
    dataset,
):

    X_path = (
        DATA_ROOT
        / dataset
        / "X.npy"
    )

    test_idx_path = (
        SPLIT_ROOT
        / dataset
        / "test_idx.npy"
    )


    X = np.load(
        X_path,
        mmap_mode="r",
        allow_pickle=False,
    )

    test_idx = np.load(
        test_idx_path,
        allow_pickle=False,
    )


    raw = np.asarray(
        X[
            np.asarray(
                test_idx,
                dtype=np.int64,
            )
        ],
        dtype=np.float32,
    )


    mean = np.asarray(
        normalization[
            dataset
        ]["mean"],
        dtype=np.float32,
    )

    std = np.asarray(
        normalization[
            dataset
        ]["std"],
        dtype=np.float32,
    )


    clean = normalize(
        raw,
        mean,
        std,
    )


    tensors = {
        (
            "baseline",
            "shared_clean",
        ):
            clean
    }


    for fault in faults:

        name = fault["name"]
        family = fault["family"]

        channels = [
            int(x)
            for x in fault["channels"]
        ]


        mask = None
        epsilon = None
        tau = None

        gaussian_pre_selected = None
        gaussian_post_selected = None


        if fault["stochastic"]:

            key = (
                dataset,
                name,
            )


            if key not in seed_lookup:

                raise RuntimeError(
                    f"Missing frozen seed {key}"
                )


            rng = np.random.RandomState(
                seed_lookup[key]
            )


            if family == "intermittent_dropout":

                mask = (
                    rng.rand(
                        raw.shape[0],
                        raw.shape[1],
                    )
                    <
                    float(
                        fault[
                            "drop_probability"
                        ]
                    )
                )


            elif family == "gaussian_noise":

                epsilon = rng.normal(
                    loc=0.0,
                    scale=1.0,
                    size=(
                        raw.shape[0],
                        raw.shape[1],
                        len(channels),
                    ),
                ).astype(
                    np.float32
                )


            elif family == "stuck_value":

                tau = rng.randint(
                    low=(
                        raw.shape[1]
                        // 4
                    ),
                    high=(
                        3
                        *
                        raw.shape[1]
                        // 4
                    ),
                    size=raw.shape[0],
                )


            else:

                raise RuntimeError(
                    f"Unexpected stochastic family "
                    f"{family}"
                )


        # ----------------------------------------------------
        # PRE-normalization domain
        # ----------------------------------------------------

        pre_raw = np.array(
            raw,
            copy=True,
        )


        if family in {
            "modality_outage",
            "single_axis_outage",
        }:

            pre_raw[
                :,
                :,
                channels,
            ] = 0.0


        elif family == "intermittent_dropout":

            for channel in channels:

                channel_view = pre_raw[
                    :,
                    :,
                    channel,
                ]

                channel_view[
                    mask
                ] = 0.0


        elif family == "gaussian_noise":

            selected_raw64 = np.stack(
                [
                    raw[
                        :,
                        :,
                        channel,
                    ].astype(
                        np.float64
                    )
                    for channel in channels
                ],
                axis=-1,
            )

            selected_mean64 = np.asarray(
                [
                    mean[channel]
                    for channel in channels
                ],
                dtype=np.float64,
            ).reshape(
                1,
                1,
                -1,
            )

            selected_std64 = np.asarray(
                [
                    std[channel]
                    for channel in channels
                ],
                dtype=np.float64,
            ).reshape(
                1,
                1,
                -1,
            )

            epsilon64 = epsilon.astype(
                np.float64
            )

            gaussian_pre64 = (
                (
                    selected_raw64
                    +
                    0.5
                    *
                    selected_std64
                    *
                    epsilon64
                )
                -
                selected_mean64
            ) / selected_std64

            gaussian_post64 = (
                (
                    selected_raw64
                    -
                    selected_mean64
                )
                /
                selected_std64
            ) + (
                0.5
                *
                epsilon64
            )


            if float(
                np.max(
                    np.abs(
                        gaussian_pre64
                        -
                        gaussian_post64
                    )
                )
            ) > 1e-12:

                raise RuntimeError(
                    f"{dataset}/{name}: "
                    "Gaussian mathematical commutation "
                    "failed"
                )


            gaussian_pre_selected = (
                gaussian_pre64.astype(
                    np.float32
                )
            )

            gaussian_post_selected = (
                gaussian_post64.astype(
                    np.float32
                )
            )


        elif family == "stuck_value":

            pre_raw = apply_stuck(
                pre_raw,
                channels,
                tau,
            )


        elif family == "scale_drift":

            factor = np.linspace(
                float(
                    fault[
                        "start_factor"
                    ]
                ),
                float(
                    fault[
                        "end_factor"
                    ]
                ),
                raw.shape[1],
                dtype=np.float32,
            )


            for channel in channels:

                pre_raw[
                    :,
                    :,
                    channel,
                ] *= factor.reshape(
                    1,
                    -1,
                )


        else:

            raise RuntimeError(
                f"Unknown family {family}"
            )


        pre_norm = normalize(
            pre_raw,
            mean,
            std,
        )


        if family == "gaussian_noise":

            for local_i, channel in enumerate(
                channels
            ):

                pre_norm[
                    :,
                    :,
                    channel,
                ] = gaussian_pre_selected[
                    :,
                    :,
                    local_i,
                ]


        # ----------------------------------------------------
        # POST-normalization domain
        # ----------------------------------------------------

        post_norm = np.array(
            clean,
            copy=True,
        )


        if family in {
            "modality_outage",
            "single_axis_outage",
        }:

            post_norm[
                :,
                :,
                channels,
            ] = 0.0


        elif family == "intermittent_dropout":

            for channel in channels:

                channel_view = post_norm[
                    :,
                    :,
                    channel,
                ]

                channel_view[
                    mask
                ] = 0.0


        elif family == "gaussian_noise":

            for local_i, channel in enumerate(
                channels
            ):

                post_norm[
                    :,
                    :,
                    channel,
                ] = gaussian_post_selected[
                    :,
                    :,
                    local_i,
                ]


        elif family == "stuck_value":

            post_norm = apply_stuck(
                post_norm,
                channels,
                tau,
            )


        elif family == "scale_drift":

            factor = np.linspace(
                float(
                    fault[
                        "start_factor"
                    ]
                ),
                float(
                    fault[
                        "end_factor"
                    ]
                ),
                clean.shape[1],
                dtype=np.float32,
            )


            for channel in channels:

                post_norm[
                    :,
                    :,
                    channel,
                ] *= factor.reshape(
                    1,
                    -1,
                )


        tensors[
            (
                name,
                "pre_normalization_sensor_domain",
            )
        ] = pre_norm

        tensors[
            (
                name,
                "post_normalization_domain",
            )
        ] = post_norm


    if len(tensors) != 35:

        raise RuntimeError(
            f"{dataset}: expected 35 tensors, "
            f"found {len(tensors)}"
        )


    # --------------------------------------------------------
    # Exact R4A SHA gate BEFORE any model sees this dataset
    # --------------------------------------------------------

    for (
        condition,
        domain,
    ), tensor in tensors.items():

        key = (
            dataset,
            condition,
            domain,
        )


        if key not in expected_tensor_sha:

            raise RuntimeError(
                f"Missing frozen R4A tensor SHA: {key}"
            )


        actual = sha256_array(
            tensor
        )

        expected = expected_tensor_sha[
            key
        ]


        if actual != expected:

            raise RuntimeError(
                f"R4A TENSOR SHA MISMATCH: {key}; "
                f"expected={expected}, "
                f"actual={actual}"
            )


    return tensors


# ============================================================
# 8. Output writer
# ============================================================

partial_path = (
    OUT
    / "paired_domain_cases_partial.csv"
)

final_path = (
    OUT
    / "paired_domain_cases_7000.csv"
)


fields = [
    "row_index",
    "dataset",
    "model",
    "seed",
    "v25_analysis_stratum",
    "checkpoint",
    "checkpoint_sha256",
    "parameter_count",
    "condition",
    "domain",
    "family",
    "input_tensor_sha256",
    "accuracy",
    "macro_f1",
    "clean_accuracy",
    "clean_macro_f1",
    "accuracy_drop_from_clean",
    "macro_f1_drop_from_clean",
    "accuracy_retention",
    "macro_f1_retention",
    "prediction_sha256",
    "n_test",
    "inference_source",
]


rows = []

partial_file = partial_path.open(
    "w",
    newline="",
    encoding="utf-8",
)

writer = csv.DictWriter(
    partial_file,
    fieldnames=fields,
)

writer.writeheader()
partial_file.flush()


def record(row):

    row["row_index"] = (
        len(rows) + 1
    )

    rows.append(row)

    writer.writerow(row)
    partial_file.flush()


# ============================================================
# 9. Evaluate dataset by dataset
# ============================================================

corrupted_forward_count = 0
model_construction_count = 0
checkpoint_deserialization_count = 0
tensor_hash_pass_count = 0
clean_tensor_loader_identity_pass = 0

start_time = time.perf_counter()


fault_lookup = {
    fault["name"]:
        fault

    for fault in faults
}


for dataset in DATASETS:

    print()
    print("=" * 118)
    print("R5_DATASET=", dataset)
    print("=" * 118)


    # --------------------------------------------------------
    # Generate + verify all 35 exact R4A tensors first
    # --------------------------------------------------------

    tensors = build_dataset_tensors(
        dataset
    )

    tensor_hash_pass_count += len(
        tensors
    )


    print(
        "R4A_TENSOR_SHA_PASS:",
        dataset,
        "35_OF_35",
    )


    # --------------------------------------------------------
    # Canonical labels and exact clean input identity
    # --------------------------------------------------------

    data = load_dataset_v3r1(
        dataset,
        batch_size=BATCH_SIZE,
        reliability_training=False,
    )


    loader_x = []
    loader_y = []


    for x, y in data[
        "test_loader"
    ]:

        loader_x.append(
            x.detach()
            .cpu()
            .numpy()
            .astype(
                np.float32,
                copy=False,
            )
        )

        loader_y.append(
            y.detach()
            .cpu()
            .numpy()
            .astype(
                np.int64,
                copy=False,
            )
        )


    canonical_clean = np.concatenate(
        loader_x,
        axis=0,
    )

    y_true = np.concatenate(
        loader_y,
        axis=0,
    )


    r5_clean = tensors[
        (
            "baseline",
            "shared_clean",
        )
    ]


    if not np.array_equal(
        canonical_clean,
        r5_clean,
    ):

        max_error = float(
            np.max(
                np.abs(
                    canonical_clean.astype(
                        np.float64
                    )
                    -
                    r5_clean.astype(
                        np.float64
                    )
                )
            )
        )

        raise RuntimeError(
            f"{dataset}: canonical loader clean tensor "
            f"does not exactly equal R4A baseline; "
            f"max_error={max_error}"
        )


    clean_tensor_loader_identity_pass += 1


    print(
        "CANONICAL_CLEAN_TENSOR_IDENTITY_PASS:",
        dataset,
    )


    # --------------------------------------------------------
    # Build reusable fault loaders
    # --------------------------------------------------------

    fault_loaders = {}


    for fault in faults:

        name = fault[
            "name"
        ]


        for domain in DOMAINS:

            tensor = tensors[
                (
                    name,
                    domain,
                )
            ]


            dataset_object = TensorDataset(
                torch.from_numpy(
                    tensor
                ),
                torch.from_numpy(
                    y_true
                ),
            )


            fault_loaders[
                (
                    name,
                    domain,
                )
            ] = DataLoader(
                dataset_object,
                batch_size=BATCH_SIZE,
                shuffle=False,
                num_workers=0,
                pin_memory=True,
                drop_last=False,
            )


    # --------------------------------------------------------
    # Exactly 50 checkpoint cases per dataset
    # --------------------------------------------------------

    dataset_plan = [
        row
        for row in model_plan
        if row[
            "dataset"
        ]
        ==
        dataset
    ]


    if len(dataset_plan) != 50:

        raise RuntimeError(
            f"{dataset}: expected 50 checkpoints, "
            f"found {len(dataset_plan)}"
        )


    dataset_plan = sorted(
        dataset_plan,
        key=lambda row: (
            row["model"],
            int(row["seed"]),
        ),
    )


    for model_index, plan_row in enumerate(
        dataset_plan,
        1,
    ):

        model_name = plan_row[
            "model"
        ]

        seed = int(
            plan_row[
                "seed"
            ]
        )

        num_classes = int(
            plan_row[
                "num_classes"
            ]
        )

        checkpoint = (
            ROOT
            / plan_row[
                "checkpoint"
            ]
        )


        print()
        print(
            "R5_MODEL:",
            dataset,
            f"{model_index}/50",
            model_name,
            seed,
        )


        # ----------------------------------------------------
        # Exact constructor
        # ----------------------------------------------------

        if model_name == V25_MODEL:

            model = create_candidate(
                "V25Dense64",
                num_classes,
                input_channels=6,
            )

        else:

            model = create_model(
                model_name,
                num_classes,
                input_channels=6,
            )


        model_construction_count += 1


        state = load_state(
            checkpoint
        )

        checkpoint_deserialization_count += 1


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
                f"{dataset}/{model_name}/seed_{seed}: "
                "strict checkpoint incompatibility"
            )


        parameter_count = int(
            sum(
                p.numel()
                for p in model.parameters()
            )
        )


        model = model.to(
            device
        )

        model.eval()


        clean_key = (
            dataset,
            model_name,
            seed,
        )

        clean_case = clean_lookup[
            clean_key
        ]


        clean_accuracy = float(
            clean_case[
                "reproduced_accuracy"
            ]
        )

        clean_macro_f1 = float(
            clean_case[
                "reproduced_macro_f1"
            ]
        )


        # ----------------------------------------------------
        # Reuse exact R4B2 clean baseline.
        # NO duplicate clean forward in R5.
        # ----------------------------------------------------

        record({
            "dataset":
                dataset,

            "model":
                model_name,

            "seed":
                seed,

            "v25_analysis_stratum":
                plan_row[
                    "v25_analysis_stratum"
                ],

            "checkpoint":
                plan_row[
                    "checkpoint"
                ],

            "checkpoint_sha256":
                plan_row[
                    "checkpoint_sha256"
                ],

            "parameter_count":
                parameter_count,

            "condition":
                "baseline",

            "domain":
                "shared_clean",

            "family":
                "baseline",

            "input_tensor_sha256":
                expected_tensor_sha[
                    (
                        dataset,
                        "baseline",
                        "shared_clean",
                    )
                ],

            "accuracy":
                clean_accuracy,

            "macro_f1":
                clean_macro_f1,

            "clean_accuracy":
                clean_accuracy,

            "clean_macro_f1":
                clean_macro_f1,

            "accuracy_drop_from_clean":
                0.0,

            "macro_f1_drop_from_clean":
                0.0,

            "accuracy_retention":
                1.0,

            "macro_f1_retention":
                1.0,

            "prediction_sha256":
                clean_case[
                    "prediction_sha256"
                ],

            "n_test":
                int(
                    clean_case[
                        "n_test"
                    ]
                ),

            "inference_source":
                "R4B2_exact_clean_reuse",
        })


        # ----------------------------------------------------
        # 34 frozen corrupted conditions
        # ----------------------------------------------------

        for fault in faults:

            name = fault[
                "name"
            ]

            family = fault[
                "family"
            ]


            for domain in DOMAINS:

                loader = fault_loaders[
                    (
                        name,
                        domain,
                    )
                ]


                (
                    accuracy,
                    macro_f1,
                    prediction_sha,
                    n_test,
                ) = evaluate_loader(
                    model,
                    model_name,
                    loader,
                    num_classes,
                )


                corrupted_forward_count += 1


                record({
                    "dataset":
                        dataset,

                    "model":
                        model_name,

                    "seed":
                        seed,

                    "v25_analysis_stratum":
                        plan_row[
                            "v25_analysis_stratum"
                        ],

                    "checkpoint":
                        plan_row[
                            "checkpoint"
                        ],

                    "checkpoint_sha256":
                        plan_row[
                            "checkpoint_sha256"
                        ],

                    "parameter_count":
                        parameter_count,

                    "condition":
                        name,

                    "domain":
                        domain,

                    "family":
                        family,

                    "input_tensor_sha256":
                        expected_tensor_sha[
                            (
                                dataset,
                                name,
                                domain,
                            )
                        ],

                    "accuracy":
                        accuracy,

                    "macro_f1":
                        macro_f1,

                    "clean_accuracy":
                        clean_accuracy,

                    "clean_macro_f1":
                        clean_macro_f1,

                    "accuracy_drop_from_clean":
                        (
                            clean_accuracy
                            -
                            accuracy
                        ),

                    "macro_f1_drop_from_clean":
                        (
                            clean_macro_f1
                            -
                            macro_f1
                        ),

                    "accuracy_retention":
                        (
                            accuracy
                            /
                            clean_accuracy
                            if clean_accuracy
                            else np.nan
                        ),

                    "macro_f1_retention":
                        (
                            macro_f1
                            /
                            clean_macro_f1
                            if clean_macro_f1
                            else np.nan
                        ),

                    "prediction_sha256":
                        prediction_sha,

                    "n_test":
                        n_test,

                    "inference_source":
                        "R5_corrupted_forward",
                })


                if (
                    corrupted_forward_count
                    % 100
                    ==
                    0
                ):

                    print(
                        "R5_CORRUPTED_PROGRESS=",
                        corrupted_forward_count,
                        "/6800",
                    )


        del state
        del model

        gc.collect()
        torch.cuda.empty_cache()


    del fault_loaders
    del tensors
    del canonical_clean
    del y_true

    gc.collect()

    print(
        "R5_DATASET_COMPLETE=",
        dataset,
    )


partial_file.close()


# ============================================================
# 10. Cardinality gates
# ============================================================

if tensor_hash_pass_count != 140:

    raise RuntimeError(
        f"Expected 140 tensor SHA passes, "
        f"got {tensor_hash_pass_count}"
    )


if clean_tensor_loader_identity_pass != 4:

    raise RuntimeError(
        "Clean tensor loader identity did not pass 4/4"
    )


if model_construction_count != 200:

    raise RuntimeError(
        f"Expected 200 model constructions, "
        f"got {model_construction_count}"
    )


if checkpoint_deserialization_count != 200:

    raise RuntimeError(
        "Expected 200 checkpoint deserializations"
    )


if corrupted_forward_count != 6800:

    raise RuntimeError(
        f"Expected 6800 corrupted forwards, "
        f"got {corrupted_forward_count}"
    )


if len(rows) != 7000:

    raise RuntimeError(
        f"Expected 7000 rows, got {len(rows)}"
    )


clean_rows_count = sum(
    row["condition"] == "baseline"
    for row in rows
)

corrupted_rows_count = (
    len(rows)
    -
    clean_rows_count
)


if clean_rows_count != 200:

    raise RuntimeError(
        f"Expected 200 clean rows, "
        f"got {clean_rows_count}"
    )


if corrupted_rows_count != 6800:

    raise RuntimeError(
        f"Expected 6800 corrupted rows, "
        f"got {corrupted_rows_count}"
    )


# Move partial -> canonical only after full cardinality pass.
partial_path.replace(
    final_path
)


print()
print(
    "R5_TENSOR_SHA_PASS_140_OF_140=True"
)

print(
    "R5_CANONICAL_CLEAN_TENSOR_IDENTITY_PASS_4_OF_4=True"
)

print(
    "R5_MODEL_CONSTRUCTION_COUNT=200"
)

print(
    "R5_CHECKPOINT_DESERIALIZATION_COUNT=200"
)

print(
    "R5_CORRUPTED_FORWARD_COUNT=6800"
)

print(
    "R5_TOTAL_ANALYSIS_ROWS=7000"
)


# ============================================================
# 11. Per-checkpoint/domain summaries = 400
# ============================================================

fault_rows = [
    row
    for row in rows
    if row[
        "condition"
    ]
    !=
    "baseline"
]


grouped = defaultdict(
    list
)


for row in fault_rows:

    grouped[
        (
            row["dataset"],
            row["model"],
            int(row["seed"]),
            row["domain"],
        )
    ].append(row)


checkpoint_domain = []


for (
    dataset,
    model,
    seed,
    domain,
), cases in sorted(
    grouped.items()
):

    if len(cases) != 17:

        raise RuntimeError(
            f"{dataset}/{model}/{seed}/{domain}: "
            f"expected 17 faults, got {len(cases)}"
        )


    clean = clean_lookup[
        (
            dataset,
            model,
            seed,
        )
    ]


    recoverable = [
        row
        for row in cases
        if row[
            "condition"
        ]
        !=
        "all_sensors_failure"
    ]


    if len(recoverable) != 16:

        raise RuntimeError(
            "Recoverable fault count is not 16"
        )


    families = defaultdict(
        list
    )


    for row in cases:

        families[
            row[
                "family"
            ]
        ].append(row)


    if len(families) != 6:

        raise RuntimeError(
            f"Expected six fault families; "
            f"got {list(families)}"
        )


    family_acc = [
        float(
            np.mean(
                [
                    x["accuracy"]
                    for x in family_cases
                ]
            )
        )
        for family_cases
        in families.values()
    ]


    family_f1 = [
        float(
            np.mean(
                [
                    x["macro_f1"]
                    for x in family_cases
                ]
            )
        )
        for family_cases
        in families.values()
    ]


    checkpoint_domain.append({
        "dataset":
            dataset,

        "model":
            model,

        "seed":
            seed,

        "domain":
            domain,

        "clean_accuracy":
            float(
                clean[
                    "reproduced_accuracy"
                ]
            ),

        "clean_macro_f1":
            float(
                clean[
                    "reproduced_macro_f1"
                ]
            ),

        "all_fault_accuracy":
            float(
                np.mean(
                    [
                        x["accuracy"]
                        for x in cases
                    ]
                )
            ),

        "all_fault_macro_f1":
            float(
                np.mean(
                    [
                        x["macro_f1"]
                        for x in cases
                    ]
                )
            ),

        "recoverable_fault_accuracy":
            float(
                np.mean(
                    [
                        x["accuracy"]
                        for x in recoverable
                    ]
                )
            ),

        "recoverable_fault_macro_f1":
            float(
                np.mean(
                    [
                        x["macro_f1"]
                        for x in recoverable
                    ]
                )
            ),

        "family_balanced_accuracy":
            float(
                np.mean(
                    family_acc
                )
            ),

        "family_balanced_macro_f1":
            float(
                np.mean(
                    family_f1
                )
            ),
    })


if len(checkpoint_domain) != 400:

    raise RuntimeError(
        f"Expected 400 checkpoint/domain summaries, "
        f"got {len(checkpoint_domain)}"
    )


write_csv(
    OUT
    / "checkpoint_domain_summary_400.csv",
    checkpoint_domain,
)


# ============================================================
# 12. Paired domain deltas = 200
# ============================================================

domain_lookup = {
    (
        row["dataset"],
        row["model"],
        int(row["seed"]),
        row["domain"],
    ):
        row

    for row in checkpoint_domain
}


delta_rows = []


for plan_row in model_plan:

    dataset = plan_row["dataset"]
    model = plan_row["model"]
    seed = int(plan_row["seed"])


    pre = domain_lookup[
        (
            dataset,
            model,
            seed,
            "pre_normalization_sensor_domain",
        )
    ]

    post = domain_lookup[
        (
            dataset,
            model,
            seed,
            "post_normalization_domain",
        )
    ]


    delta_rows.append({
        "dataset":
            dataset,

        "model":
            model,

        "seed":
            seed,

        "v25_analysis_stratum":
            plan_row[
                "v25_analysis_stratum"
            ],

        "pre_all_fault_accuracy":
            pre[
                "all_fault_accuracy"
            ],

        "post_all_fault_accuracy":
            post[
                "all_fault_accuracy"
            ],

        "delta_pre_minus_post_all_fault_accuracy":
            (
                pre[
                    "all_fault_accuracy"
                ]
                -
                post[
                    "all_fault_accuracy"
                ]
            ),

        "pre_all_fault_macro_f1":
            pre[
                "all_fault_macro_f1"
            ],

        "post_all_fault_macro_f1":
            post[
                "all_fault_macro_f1"
            ],

        "delta_pre_minus_post_all_fault_macro_f1":
            (
                pre[
                    "all_fault_macro_f1"
                ]
                -
                post[
                    "all_fault_macro_f1"
                ]
            ),

        "pre_recoverable_accuracy":
            pre[
                "recoverable_fault_accuracy"
            ],

        "post_recoverable_accuracy":
            post[
                "recoverable_fault_accuracy"
            ],

        "delta_pre_minus_post_recoverable_accuracy":
            (
                pre[
                    "recoverable_fault_accuracy"
                ]
                -
                post[
                    "recoverable_fault_accuracy"
                ]
            ),

        "pre_recoverable_macro_f1":
            pre[
                "recoverable_fault_macro_f1"
            ],

        "post_recoverable_macro_f1":
            post[
                "recoverable_fault_macro_f1"
            ],

        "delta_pre_minus_post_recoverable_macro_f1":
            (
                pre[
                    "recoverable_fault_macro_f1"
                ]
                -
                post[
                    "recoverable_fault_macro_f1"
                ]
            ),

        "pre_family_balanced_accuracy":
            pre[
                "family_balanced_accuracy"
            ],

        "post_family_balanced_accuracy":
            post[
                "family_balanced_accuracy"
            ],

        "delta_pre_minus_post_family_balanced_accuracy":
            (
                pre[
                    "family_balanced_accuracy"
                ]
                -
                post[
                    "family_balanced_accuracy"
                ]
            ),

        "pre_family_balanced_macro_f1":
            pre[
                "family_balanced_macro_f1"
            ],

        "post_family_balanced_macro_f1":
            post[
                "family_balanced_macro_f1"
            ],

        "delta_pre_minus_post_family_balanced_macro_f1":
            (
                pre[
                    "family_balanced_macro_f1"
                ]
                -
                post[
                    "family_balanced_macro_f1"
                ]
            ),
    })


if len(delta_rows) != 200:

    raise RuntimeError(
        f"Expected 200 domain delta rows, "
        f"got {len(delta_rows)}"
    )


write_csv(
    OUT
    / "checkpoint_domain_delta_200.csv",
    delta_rows,
)


# ============================================================
# 13. Dataset/model/domain means = 80
# ============================================================

dm_group = defaultdict(
    list
)


for row in checkpoint_domain:

    dm_group[
        (
            row["dataset"],
            row["model"],
            row["domain"],
        )
    ].append(row)


dataset_model_domain = []


for (
    dataset,
    model,
    domain,
), cases in sorted(
    dm_group.items()
):

    if len(cases) != 5:

        raise RuntimeError(
            f"{dataset}/{model}/{domain}: "
            f"expected five seeds"
        )


    item = {
        "dataset":
            dataset,

        "model":
            model,

        "domain":
            domain,

        "n_seeds":
            5,
    }


    metric_names = [
        "clean_accuracy",
        "clean_macro_f1",
        "all_fault_accuracy",
        "all_fault_macro_f1",
        "recoverable_fault_accuracy",
        "recoverable_fault_macro_f1",
        "family_balanced_accuracy",
        "family_balanced_macro_f1",
    ]


    for metric in metric_names:

        item[
            metric
        ] = float(
            np.mean(
                [
                    x[metric]
                    for x in cases
                ]
            )
        )


    dataset_model_domain.append(
        item
    )


if len(dataset_model_domain) != 80:

    raise RuntimeError(
        f"Expected 80 dataset/model/domain rows, "
        f"got {len(dataset_model_domain)}"
    )


write_csv(
    OUT
    / "dataset_model_domain_summary_80.csv",
    dataset_model_domain,
)


# ============================================================
# 14. Equal-dataset aggregate = 20
# ============================================================

model_domain_group = defaultdict(
    list
)


for row in dataset_model_domain:

    model_domain_group[
        (
            row["model"],
            row["domain"],
        )
    ].append(row)


equal_dataset = []


for (
    model,
    domain,
), cases in sorted(
    model_domain_group.items()
):

    if len(cases) != 4:

        raise RuntimeError(
            f"{model}/{domain}: "
            "expected four dataset means"
        )


    item = {
        "model":
            model,

        "domain":
            domain,

        "n_datasets":
            4,
    }


    for metric in [
        "clean_accuracy",
        "clean_macro_f1",
        "all_fault_accuracy",
        "all_fault_macro_f1",
        "recoverable_fault_accuracy",
        "recoverable_fault_macro_f1",
        "family_balanced_accuracy",
        "family_balanced_macro_f1",
    ]:

        item[
            metric
        ] = float(
            np.mean(
                [
                    x[metric]
                    for x in cases
                ]
            )
        )


    equal_dataset.append(
        item
    )


if len(equal_dataset) != 20:

    raise RuntimeError(
        f"Expected 20 equal-dataset rows, "
        f"got {len(equal_dataset)}"
    )


write_csv(
    OUT
    / "equal_dataset_model_domain_summary_20.csv",
    equal_dataset,
)


elapsed = (
    time.perf_counter()
    -
    start_time
)


# ============================================================
# 15. Final receipt
# ============================================================

receipt = {
    "audit":
        "STAGE25_PAIRED_DOMAIN_EVALUATION_R5",

    "status":
        "PASS",

    "scientific_protocol":
        "FROZEN_R3_UNCHANGED",

    "r4a_tensor_sha":
        "PASS_140_OF_140",

    "canonical_clean_tensor_identity":
        "PASS_4_OF_4",

    "frozen_model_bank":
        "PASS_200_OF_200",

    "clean_baseline_source":
        "R4B2_EXACT_REPRODUCTION",

    "clean_baseline_rows":
        200,

    "clean_forward_performed_in_r5":
        False,

    "corrupted_forward_rows":
        6800,

    "total_analysis_rows":
        7000,

    "checkpoint_domain_summaries":
        400,

    "paired_domain_delta_rows":
        200,

    "dataset_model_domain_summary_rows":
        80,

    "equal_dataset_model_domain_summary_rows":
        20,

    "model_construction_count":
        model_construction_count,

    "checkpoint_deserialization_count":
        checkpoint_deserialization_count,

    "corrupted_forward_count":
        corrupted_forward_count,

    "training_performed":
        False,

    "optimizer_created":
        False,

    "backward_performed":
        False,

    "checkpoint_modified":
        False,

    "dataset_modified":
        False,

    "fault_definition_modified":
        False,

    "fault_severity_modified":
        False,

    "fault_seed_modified":
        False,

    "aggregation_modified":
        False,

    "v25_retrained":
        False,

    "storm_used_for_tuning":
        False,

    "elapsed_seconds":
        elapsed,

    "next_gate":
        (
            "Freeze R5, then conduct Stage25 R6 "
            "scientific analysis: domain-dependent "
            "robustness, rankings, fault families, "
            "normalization-offset mechanism, statistics, "
            "and V25 development-vs-held-out distinction. "
            "No model retraining until R5/R6 evidence is frozen."
        ),
}


write_json(
    OUT
    / "stage25_paired_domain_evaluation_receipt_r5.json",
    receipt,
)


print()
print("=" * 118)
print("STAGE25 R5 FINAL RECEIPT")
print("=" * 118)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)

print()
print(
    "STAGE25_PAIRED_DOMAIN_EVALUATION_R5_PASS=True"
)

print(
    "R5_TENSOR_SHA_PASS_140_OF_140=True"
)

print(
    "R5_CANONICAL_CLEAN_TENSOR_IDENTITY_PASS_4_OF_4=True"
)

print(
    "R5_CLEAN_BASELINE_ROWS=200"
)

print(
    "R5_CORRUPTED_FORWARD_ROWS=6800"
)

print(
    "R5_TOTAL_ANALYSIS_ROWS=7000"
)

print(
    "R5_CHECKPOINT_DOMAIN_SUMMARY_ROWS=400"
)

print(
    "R5_PAIRED_DOMAIN_DELTA_ROWS=200"
)

print(
    "R5_DATASET_MODEL_DOMAIN_SUMMARY_ROWS=80"
)

print(
    "R5_EQUAL_DATASET_SUMMARY_ROWS=20"
)

print(
    "TRAINING_PERFORMED=False"
)

print(
    "BACKWARD_PERFORMED=False"
)

print(
    "FAULT_PROTOCOL_MODIFIED=False"
)

print(
    "V25_RETRAINED=False"
)

print(
    "STORM_USED_FOR_TUNING=False"
)
