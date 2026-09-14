from __future__ import annotations

import csv
import gc
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from sklearn.metrics import (
    accuracy_score,
    f1_score,
)

from torch.utils.data import (
    DataLoader,
    TensorDataset,
)


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
    / "results/v26_primary_confirmation_protocol_r4"
)

R5 = (
    ROOT
    / "results/v26_primary_confirmation_training_r5"
)

R6A = (
    ROOT
    / "results/v26_primary_confirmation_test_preflight_r6a"
)

R6B0 = (
    ROOT
    / "results/v26_primary_confirmation_evaluator_source_binding_r6b0"
)

S25_R2 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "canonical_reconstruction_audit_r2"
)

S25_R3 = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "protocol_preregistration_r3"
)

S25_R4A = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "transform_provenance_preflight_r4a"
)

OUT = (
    ROOT
    / "results/v26_primary_confirmation_test_r6b"
)

DATA_ROOT = (
    ROOT
    / "data/processed/harmonized"
)

SPLIT_ROOT = (
    ROOT
    / "data/processed/splits"
)

OUT.mkdir(
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


PROMOTED = "V26C_DualGateLiteCons"

PRE = "pre_normalization_sensor_domain"

DEVICE = torch.device(
    "cuda:0"
)

BATCH_SIZE = 64


DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]


EXPECTED_N_TEST = {
    "UCI_HAR":
        2286,

    "PAMAP2":
        4192,

    "DSADS":
        2280,

    "MotionSense":
        4349,
}


EXPECTED_NUM_CLASSES = {
    "UCI_HAR":
        6,

    "PAMAP2":
        12,

    "DSADS":
        19,

    "MotionSense":
        6,
}


PRIMARY_METRICS = [
    "all_fault_macro_f1",
    "family_balanced_macro_f1",
]


ALL_METRICS = [
    "clean_accuracy",
    "clean_macro_f1",
    "all_fault_accuracy",
    "all_fault_macro_f1",
    "recoverable_fault_accuracy",
    "recoverable_fault_macro_f1",
    "family_balanced_accuracy",
    "family_balanced_macro_f1",
]


# ============================================================
# Generic helpers
# ============================================================

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


# EXACT Stage25 R5 hash semantics.
def sha256_array(
    arr: np.ndarray,
) -> str:

    arr = np.ascontiguousarray(
        arr
    )

    h = hashlib.sha256()

    h.update(
        str(
            arr.shape
        ).encode(
            "utf-8"
        )
    )

    h.update(
        str(
            arr.dtype
        ).encode(
            "utf-8"
        )
    )

    h.update(
        arr.tobytes(
            order="C"
        )
    )

    return h.hexdigest()


# EXACT Stage25 R5 prediction-hash semantics.
def sha256_int64(
    values,
) -> str:

    arr = np.ascontiguousarray(
        np.asarray(
            values,
            dtype=np.int64,
        )
    )

    h = hashlib.sha256()

    h.update(
        str(
            arr.shape
        ).encode(
            "utf-8"
        )
    )

    h.update(
        arr.tobytes()
    )

    return h.hexdigest()


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

        raise RuntimeError(
            f"No rows for {path}"
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

        writer.writerows(
            rows
        )


# EXACT Stage25 R5 normalization.
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


# EXACT Stage25 R5 P2 stuck-value implementation.
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


# ============================================================
# Frozen metadata
# ============================================================

r6b0_receipt = json.loads(
    (
        R6B0
        / "v26_primary_confirmation_evaluator_source_binding_receipt_r6b0.json"
    ).read_text()
)


if r6b0_receipt.get(
    "status"
) != "PASS":

    raise RuntimeError(
        "R6B0 source-binding prerequisite failed"
    )


if (
    r6b0_receipt.get(
        "stage25_r5_runner_sha256"
    )
    !=
    "604df94e1f5f01ba546347102505781d900512818c48528faecf55a16dd3d3d5"
):

    raise RuntimeError(
        "Frozen Stage25 R5 source identity changed"
    )


normalization = json.loads(
    (
        S25_R2
        / "dataset_normalization_receipts.json"
    ).read_text()
)


protocol = json.loads(
    (
        S25_R3
        / "stage25_physical_fault_protocol_r3.json"
    ).read_text()
)


faults = protocol[
    "fault_conditions"
]


if len(
    faults
) != 17:

    raise RuntimeError(
        "Frozen Stage25 fault count != 17"
    )


fault_lookup = {
    fault[
        "name"
    ]:
        fault

    for fault in faults
}


seed_manifest_path = (
    S25_R3
    / "stochastic_fault_seed_manifest_24.csv"
)


with seed_manifest_path.open(
    newline="",
    encoding="utf-8",
) as f:

    seed_rows = list(
        csv.DictReader(f)
    )


if len(
    seed_rows
) != 24:

    raise RuntimeError(
        "Frozen stochastic seed count != 24"
    )


seed_lookup = {
    (
        row[
            "dataset"
        ],
        row[
            "condition"
        ],
    ):
        int(
            row[
                "seed"
            ]
        )

    for row in seed_rows
}


tensor_manifest_path = (
    S25_R4A
    / "dataset_condition_tensor_manifest_140.csv"
)


with tensor_manifest_path.open(
    newline="",
    encoding="utf-8",
) as f:

    tensor_manifest = list(
        csv.DictReader(f)
    )


if len(
    tensor_manifest
) != 140:

    raise RuntimeError(
        "Frozen R4A tensor count != 140"
    )


expected_tensor_sha = {
    (
        row[
            "dataset"
        ],
        row[
            "condition"
        ],
        row[
            "domain"
        ],
    ):
        row[
            "tensor_sha256"
        ]

    for row in tensor_manifest
}


protected_manifest_path = (
    R6A
    / "protected_stage25_tensor_identity_manifest_72.csv"
)


with protected_manifest_path.open(
    newline="",
    encoding="utf-8",
) as f:

    protected_rows = list(
        csv.DictReader(f)
    )


if len(
    protected_rows
) != 72:

    raise RuntimeError(
        "R6A protected tensor count != 72"
    )


protected_lookup = {
    (
        row[
            "dataset"
        ],
        row[
            "condition"
        ],
        row[
            "domain"
        ],
    ):
        row[
            "input_tensor_sha256"
        ]

    for row in protected_rows
}


checkpoint_manifest_path = (
    R5
    / "frozen_confirmation_checkpoint_manifest_14.csv"
)


with checkpoint_manifest_path.open(
    newline="",
    encoding="utf-8",
) as f:

    checkpoint_rows = list(
        csv.DictReader(f)
    )


if len(
    checkpoint_rows
) != 14:

    raise RuntimeError(
        "Frozen confirmation checkpoint count != 14"
    )


# ============================================================
# Verify checkpoint SHAs again before test access
# ============================================================

for row in checkpoint_rows:

    if row[
        "candidate_id"
    ] != PROMOTED:

        raise RuntimeError(
            "Non-promoted model in frozen checkpoint manifest"
        )


    checkpoint = (
        ROOT
        / row[
            "checkpoint"
        ]
    )


    actual_sha = sha256_file(
        checkpoint
    )


    if actual_sha != row[
        "checkpoint_sha256"
    ]:

        raise RuntimeError(
            f"Frozen checkpoint SHA mismatch: "
            f"{row['dataset']}/seed_{row['seed']}"
        )


print(
    "R6B_FROZEN_CHECKPOINT_SHA_PASS_14_OF_14=True"
)


# ============================================================
# EXACT Stage25 R5 dataset transformation implementation.
#
# Both PRE and POST tensors are rebuilt so the full original
# R4A 140-SHA contract is reproduced. Only clean + PRE are
# later exposed to V26C.
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

        name = fault[
            "name"
        ]

        family = fault[
            "family"
        ]

        channels = [
            int(x)
            for x
            in fault[
                "channels"
            ]
        ]


        mask = None
        epsilon = None
        tau = None

        gaussian_pre_selected = None
        gaussian_post_selected = None


        if fault[
            "stochastic"
        ]:

            key = (
                dataset,
                name,
            )


            if key not in seed_lookup:

                raise RuntimeError(
                    f"Missing frozen seed {key}"
                )


            rng = np.random.RandomState(
                seed_lookup[
                    key
                ]
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
                        len(
                            channels
                        ),
                    ),
                ).astype(
                    np.float32
                )


            elif family == "stuck_value":

                tau = rng.randint(
                    low=(
                        raw.shape[1]
                        //
                        4
                    ),
                    high=(
                        3
                        *
                        raw.shape[1]
                        //
                        4
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
                    mean[
                        channel
                    ]
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
                    std[
                        channel
                    ]
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
                    "Gaussian mathematical commutation failed"
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
                PRE,
            )
        ] = pre_norm


        tensors[
            (
                name,
                "post_normalization_domain",
            )
        ] = post_norm


    if len(
        tensors
    ) != 35:

        raise RuntimeError(
            f"{dataset}: expected 35 tensors, "
            f"found {len(tensors)}"
        )


    # EXACT R4A SHA gate.
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
                f"expected={expected}; actual={actual}"
            )


    return tensors


# ============================================================
# Canonical frozen label mapping:
# sorted global native labels -> contiguous [0..K-1].
# ============================================================

def load_test_labels(
    dataset,
):

    y = np.load(
        DATA_ROOT
        / dataset
        / "y.npy",
        mmap_mode="r",
        allow_pickle=False,
    )


    test_idx = np.load(
        SPLIT_ROOT
        / dataset
        / "test_idx.npy",
        allow_pickle=False,
    )


    native_classes = np.sort(
        np.unique(
            y
        )
    )


    if len(
        native_classes
    ) != EXPECTED_NUM_CLASSES[
        dataset
    ]:

        raise RuntimeError(
            f"{dataset}: class-count mismatch"
        )


    mapping = {
        value:
            i

        for i, value in enumerate(
            native_classes.tolist()
        )
    }


    native_test = np.asarray(
        y[
            np.asarray(
                test_idx,
                dtype=np.int64,
            )
        ]
    )


    mapped = np.asarray(
        [
            mapping[
                value
            ]
            for value
            in native_test.tolist()
        ],
        dtype=np.int64,
    )


    if len(
        mapped
    ) != EXPECTED_N_TEST[
        dataset
    ]:

        raise RuntimeError(
            f"{dataset}: test cardinality mismatch"
        )


    return (
        mapped,
        len(
            native_classes
        ),
    )


print("=" * 118)
print("V26 R6B PROTECTED PRIMARY CONFIRMATION")
print("NO TRAINING — FROZEN V26C")
print("=" * 118)


if not torch.cuda.is_available():

    raise RuntimeError(
        "CUDA unavailable. "
        "Classify environment failure; "
        "do not change scientific protocol."
    )


torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True


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
# PHASE 1 — GLOBAL TENSOR SHA PREFLIGHT
#
# Crucial:
# No model construction.
# No checkpoint deserialization.
# No model forward.
#
# All four protected test splits are opened here, but no model
# sees any tensor until every frozen SHA has passed.
# ============================================================

r4a_sha_pass = 0
protected_sha_pass = 0


for dataset in DATASETS:

    tensors = build_dataset_tensors(
        dataset
    )


    # Independently recount all 35 frozen R4A identities.
    for (
        condition,
        domain,
    ), tensor in tensors.items():

        key = (
            dataset,
            condition,
            domain,
        )


        actual = sha256_array(
            tensor
        )


        if actual != expected_tensor_sha[
            key
        ]:

            raise RuntimeError(
                f"Second R4A SHA gate failed: {key}"
            )


        r4a_sha_pass += 1


    # Protected 18 = clean + 17 physical PRE conditions.
    protected_keys = [
        (
            "baseline",
            "shared_clean",
        )
    ] + [
        (
            fault[
                "name"
            ],
            PRE,
        )
        for fault in faults
    ]


    if len(
        protected_keys
    ) != 18:

        raise RuntimeError(
            "Protected condition cardinality != 18"
        )


    for (
        condition,
        domain,
    ) in protected_keys:

        key = (
            dataset,
            condition,
            domain,
        )


        actual = sha256_array(
            tensors[
                (
                    condition,
                    domain,
                )
            ]
        )


        if key not in protected_lookup:

            raise RuntimeError(
                f"R6A protected SHA missing: {key}"
            )


        if actual != protected_lookup[
            key
        ]:

            raise RuntimeError(
                f"R6A PROTECTED SHA MISMATCH: {key}; "
                f"expected={protected_lookup[key]}; "
                f"actual={actual}"
            )


        protected_sha_pass += 1


    del tensors

    gc.collect()


if r4a_sha_pass != 140:

    raise RuntimeError(
        f"Expected 140/140 R4A SHA passes, "
        f"got {r4a_sha_pass}"
    )


if protected_sha_pass != 72:

    raise RuntimeError(
        f"Expected 72/72 protected SHA passes, "
        f"got {protected_sha_pass}"
    )


print(
    "ALL_R4A_TENSOR_SHA_PREFLIGHT_PASS_140_OF_140=True"
)

print(
    "ALL_PROTECTED_TENSOR_SHA_PREFLIGHT_PASS_72_OF_72=True"
)

print(
    "ALL_72_PROTECTED_TENSORS_VERIFIED_BEFORE_FIRST_MODEL_FORWARD=True"
)


preforward_receipt = {
    "stage":
        "V26_R6B_PRE_FORWARD_TENSOR_GATE",

    "r4a_tensor_sha":
        "PASS_140_OF_140",

    "protected_tensor_sha":
        "PASS_72_OF_72",

    "test_split_loaded":
        True,

    "test_tensor_regenerated":
        True,

    "model_constructed":
        False,

    "checkpoint_deserialized":
        False,

    "model_forward_performed":
        False,
}


write_json(
    OUT
    / "pre_forward_tensor_sha_gate_receipt.json",
    preforward_receipt,
)


(
    OUT
    / "ALL_72_TENSORS_VERIFIED_BEFORE_FORWARD"
).write_text(
    "PASS\n"
)


# ============================================================
# PHASE 2 — ONE-TIME MODEL EVALUATION
# ============================================================

case_rows = []

model_construction_count = 0
checkpoint_deserialization_count = 0
model_batch_forward_count = 0

forward_started = False


def evaluate_tensor(
    model,
    x,
    y_true,
    num_classes,
):

    global model_batch_forward_count, forward_started


    ds = TensorDataset(
        torch.from_numpy(
            np.asarray(
                x,
                dtype=np.float32,
            )
        ),
        torch.from_numpy(
            np.asarray(
                y_true,
                dtype=np.int64,
            )
        ),
    )


    loader = DataLoader(
        ds,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
        drop_last=False,
    )


    predictions = []


    with torch.inference_mode():

        for batch_x, _ in loader:

            if not forward_started:

                (
                    OUT
                    / "MODEL_FORWARD_STARTED"
                ).write_text(
                    "V26 R6B protected forward started\n"
                )

                forward_started = True

                print(
                    "PROTECTED_MODEL_FORWARD_STARTED=True",
                    flush=True,
                )


            batch_x = batch_x.to(
                DEVICE,
                non_blocking=True,
            )


            logits = model(
                batch_x
            )


            model_batch_forward_count += 1


            if isinstance(
                logits,
                (
                    tuple,
                    list,
                ),
            ):

                logits = logits[
                    0
                ]


            if (
                logits.ndim != 2
                or
                logits.shape[1]
                != num_classes
            ):

                raise RuntimeError(
                    f"Invalid logits shape "
                    f"{tuple(logits.shape)}"
                )


            prediction = torch.argmax(
                logits,
                dim=1,
            )


            predictions.extend(
                prediction.detach()
                .cpu()
                .numpy()
                .astype(
                    np.int64,
                    copy=False,
                )
                .tolist()
            )


    y_pred = np.asarray(
        predictions,
        dtype=np.int64,
    )


    if len(
        y_pred
    ) != len(
        y_true
    ):

        raise RuntimeError(
            "Prediction cardinality mismatch"
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
                range(
                    num_classes
                )
            ),
            average="macro",
            zero_division=0,
        )
    )


    return (
        accuracy,
        macro_f1,
        sha256_int64(
            y_pred
        ),
    )


row_index = 0


for dataset in DATASETS:

    print()
    print("=" * 118)

    print(
        "PROTECTED_DATASET_START=",
        dataset,
        flush=True,
    )

    print("=" * 118)


    # Rebuild and re-SHA gate again for inference phase.
    tensors = build_dataset_tensors(
        dataset
    )


    y_test, num_classes = (
        load_test_labels(
            dataset
        )
    )


    dataset_checkpoints = [
        row
        for row in checkpoint_rows
        if row[
            "dataset"
        ]
        ==
        dataset
    ]


    dataset_checkpoints.sort(
        key=lambda row:
            int(
                row[
                    "seed"
                ]
            )
    )


    expected_seed_count = (
        2
        if dataset
        in {
            "UCI_HAR",
            "DSADS",
        }
        else
        5
    )


    if len(
        dataset_checkpoints
    ) != expected_seed_count:

        raise RuntimeError(
            f"{dataset}: confirmation checkpoint "
            f"count mismatch"
        )


    for checkpoint_row in dataset_checkpoints:

        seed = int(
            checkpoint_row[
                "seed"
            ]
        )


        checkpoint = (
            ROOT
            / checkpoint_row[
                "checkpoint"
            ]
        )


        actual_checkpoint_sha = (
            sha256_file(
                checkpoint
            )
        )


        if (
            actual_checkpoint_sha
            !=
            checkpoint_row[
                "checkpoint_sha256"
            ]
        ):

            raise RuntimeError(
                f"Checkpoint changed before inference: "
                f"{dataset}/seed_{seed}"
            )


        model = create_v26_candidate(
            PROMOTED,
            num_classes,
            input_channels=6,
        )


        model_construction_count += 1


        params = parameter_count(
            model
        )


        if params != int(
            checkpoint_row[
                "parameter_count"
            ]
        ):

            raise RuntimeError(
                f"{dataset}/seed_{seed}: "
                "parameter-count mismatch"
            )


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
                f"{dataset}/seed_{seed}: "
                "strict checkpoint load failed"
            )


        model = model.to(
            DEVICE
        )

        model.eval()


        # ----------------------------------------------------
        # Clean baseline first
        # ----------------------------------------------------

        clean_tensor = tensors[
            (
                "baseline",
                "shared_clean",
            )
        ]


        clean_sha = sha256_array(
            clean_tensor
        )


        protected_clean_key = (
            dataset,
            "baseline",
            "shared_clean",
        )


        if (
            clean_sha
            !=
            protected_lookup[
                protected_clean_key
            ]
        ):

            raise RuntimeError(
                "Protected clean SHA changed "
                "immediately before forward"
            )


        (
            clean_accuracy,
            clean_macro_f1,
            clean_prediction_sha,
        ) = evaluate_tensor(
            model,
            clean_tensor,
            y_test,
            num_classes,
        )


        row_index += 1


        case_rows.append({
            "row_index":
                row_index,

            "dataset":
                dataset,

            "model":
                PROMOTED,

            "seed":
                seed,

            "analysis_stratum":
                "primary_confirmation_14",

            "checkpoint":
                checkpoint_row[
                    "checkpoint"
                ],

            "checkpoint_sha256":
                actual_checkpoint_sha,

            "parameter_count":
                params,

            "condition":
                "baseline",

            "domain":
                "shared_clean",

            "family":
                "baseline",

            "input_tensor_sha256":
                clean_sha,

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
                clean_prediction_sha,

            "n_test":
                len(
                    y_test
                ),

            "inference_source":
                "V26_R6B_PROTECTED_PRIMARY_CONFIRMATION",
        })


        # ----------------------------------------------------
        # Exact 17 physical PRE-normalization faults
        # ----------------------------------------------------

        for fault in faults:

            condition = fault[
                "name"
            ]

            family = fault[
                "family"
            ]


            tensor = tensors[
                (
                    condition,
                    PRE,
                )
            ]


            tensor_sha = sha256_array(
                tensor
            )


            protected_key = (
                dataset,
                condition,
                PRE,
            )


            if (
                tensor_sha
                !=
                protected_lookup[
                    protected_key
                ]
            ):

                raise RuntimeError(
                    f"Protected tensor SHA changed "
                    f"immediately before forward: "
                    f"{protected_key}"
                )


            (
                accuracy,
                macro_f1,
                prediction_sha,
            ) = evaluate_tensor(
                model,
                tensor,
                y_test,
                num_classes,
            )


            row_index += 1


            case_rows.append({
                "row_index":
                    row_index,

                "dataset":
                    dataset,

                "model":
                    PROMOTED,

                "seed":
                    seed,

                "analysis_stratum":
                    "primary_confirmation_14",

                "checkpoint":
                    checkpoint_row[
                        "checkpoint"
                    ],

                "checkpoint_sha256":
                    actual_checkpoint_sha,

                "parameter_count":
                    params,

                "condition":
                    condition,

                "domain":
                    PRE,

                "family":
                    family,

                "input_tensor_sha256":
                    tensor_sha,

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
                        != 0
                        else float(
                            "nan"
                        )
                    ),

                "macro_f1_retention":
                    (
                        macro_f1
                        /
                        clean_macro_f1
                        if clean_macro_f1
                        != 0
                        else float(
                            "nan"
                        )
                    ),

                "prediction_sha256":
                    prediction_sha,

                "n_test":
                    len(
                        y_test
                    ),

                "inference_source":
                    "V26_R6B_PROTECTED_PRIMARY_CONFIRMATION",
            })


        write_csv(
            OUT
            / "protected_confirmation_cases_partial.csv",
            case_rows,
        )


        print(
            "V26_PROTECTED_CHECKPOINT_COMPLETE:",
            dataset,
            seed,
            "CLEAN_ACC=",
            f"{clean_accuracy:.9f}",
            "CLEAN_F1=",
            f"{clean_macro_f1:.9f}",
            "CASE_ROWS_SO_FAR=",
            len(
                case_rows
            ),
            flush=True,
        )


        del state
        del model

        gc.collect()

        torch.cuda.empty_cache()


    del tensors

    gc.collect()


if len(
    case_rows
) != 252:

    raise RuntimeError(
        f"Expected 252 protected case rows, "
        f"found {len(case_rows)}"
    )


if row_index != 252:

    raise RuntimeError(
        "Protected row index count != 252"
    )


write_csv(
    OUT
    / "protected_confirmation_cases_252.csv",
    case_rows,
)


partial_path = (
    OUT
    / "protected_confirmation_cases_partial.csv"
)


if partial_path.exists():

    partial_path.unlink()


print(
    "V26_PROTECTED_CONFIRMATION_CASE_ROWS_PASS_252_OF_252=True"
)


# ============================================================
# Aggregate checkpoint-level metrics
# ============================================================

checkpoint_summary = []


identities = sorted({
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
    for row in case_rows
})


if len(
    identities
) != 14:

    raise RuntimeError(
        "Protected checkpoint identity count != 14"
    )


for dataset, seed in identities:

    rows = [
        row
        for row in case_rows
        if (
            row[
                "dataset"
            ]
            ==
            dataset
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
        rows
    ) != 18:

        raise RuntimeError(
            f"{dataset}/seed_{seed}: "
            f"expected 18 rows"
        )


    clean_rows = [
        row
        for row in rows
        if row[
            "condition"
        ]
        ==
        "baseline"
    ]


    if len(
        clean_rows
    ) != 1:

        raise RuntimeError(
            "Expected one clean row"
        )


    clean = clean_rows[
        0
    ]


    fault_rows = [
        row
        for row in rows
        if row[
            "condition"
        ]
        !=
        "baseline"
    ]


    if len(
        fault_rows
    ) != 17:

        raise RuntimeError(
            "Expected 17 fault rows"
        )


    recoverable = [
        row
        for row in fault_rows
        if row[
            "condition"
        ]
        !=
        "all_sensors_failure"
    ]


    if len(
        recoverable
    ) != 16:

        raise RuntimeError(
            "Expected 16 recoverable fault rows"
        )


    family_groups = defaultdict(
        list
    )


    for row in fault_rows:

        family_groups[
            row[
                "family"
            ]
        ].append(
            row
        )


    if set(
        family_groups
    ) != {
        "modality_outage",
        "single_axis_outage",
        "intermittent_dropout",
        "gaussian_noise",
        "stuck_value",
        "scale_drift",
    }:

        raise RuntimeError(
            "Fault-family set mismatch"
        )


    family_accuracy = [
        float(
            np.mean(
                [
                    row[
                        "accuracy"
                    ]
                    for row in values
                ]
            )
        )
        for values
        in family_groups.values()
    ]


    family_f1 = [
        float(
            np.mean(
                [
                    row[
                        "macro_f1"
                    ]
                    for row in values
                ]
            )
        )
        for values
        in family_groups.values()
    ]


    checkpoint_summary.append({
        "dataset":
            dataset,

        "seed":
            seed,

        "model":
            PROMOTED,

        "parameter_count":
            int(
                clean[
                    "parameter_count"
                ]
            ),

        "clean_accuracy":
            float(
                clean[
                    "accuracy"
                ]
            ),

        "clean_macro_f1":
            float(
                clean[
                    "macro_f1"
                ]
            ),

        "all_fault_accuracy":
            float(
                np.mean(
                    [
                        row[
                            "accuracy"
                        ]
                        for row
                        in fault_rows
                    ]
                )
            ),

        "all_fault_macro_f1":
            float(
                np.mean(
                    [
                        row[
                            "macro_f1"
                        ]
                        for row
                        in fault_rows
                    ]
                )
            ),

        "recoverable_fault_accuracy":
            float(
                np.mean(
                    [
                        row[
                            "accuracy"
                        ]
                        for row
                        in recoverable
                    ]
                )
            ),

        "recoverable_fault_macro_f1":
            float(
                np.mean(
                    [
                        row[
                            "macro_f1"
                        ]
                        for row
                        in recoverable
                    ]
                )
            ),

        "family_balanced_accuracy":
            float(
                np.mean(
                    family_accuracy
                )
            ),

        "family_balanced_macro_f1":
            float(
                np.mean(
                    family_f1
                )
            ),
    })


write_csv(
    OUT
    / "checkpoint_physical_summary_14.csv",
    checkpoint_summary,
)


print(
    "V26_CHECKPOINT_PHYSICAL_SUMMARY_PASS_14=True"
)


# ============================================================
# Dataset-level mean across confirmation seeds
# ============================================================

dataset_summary = []


for dataset in DATASETS:

    rows = [
        row
        for row in checkpoint_summary
        if row[
            "dataset"
        ]
        ==
        dataset
    ]


    expected_n = (
        2
        if dataset
        in {
            "UCI_HAR",
            "DSADS",
        }
        else
        5
    )


    if len(
        rows
    ) != expected_n:

        raise RuntimeError(
            f"{dataset}: dataset summary seed count mismatch"
        )


    result = {
        "dataset":
            dataset,

        "model":
            PROMOTED,

        "n_confirmation_seeds":
            len(
                rows
            ),
    }


    for metric in ALL_METRICS:

        result[
            metric
        ] = float(
            np.mean(
                [
                    row[
                        metric
                    ]
                    for row in rows
                ]
            )
        )


    dataset_summary.append(
        result
    )


write_csv(
    OUT
    / "dataset_physical_summary_4.csv",
    dataset_summary,
)


# ============================================================
# Equal-dataset primary summary
# ============================================================

v26_equal = {
    "model":
        PROMOTED,

    "domain":
        PRE,

    "n_datasets":
        4,

    "n_checkpoints":
        14,

    "max_parameter_count":
        max(
            int(
                row[
                    "parameter_count"
                ]
            )
            for row in checkpoint_summary
        ),
}


for metric in ALL_METRICS:

    v26_equal[
        metric
    ] = float(
        np.mean(
            [
                row[
                    metric
                ]
                for row in dataset_summary
            ]
        )
    )


write_csv(
    OUT
    / "v26c_equal_dataset_physical_summary.csv",
    [
        v26_equal
    ],
)


print(
    "V26_EQUAL_DATASET_PHYSICAL_SUMMARY_PASS=True"
)


# ============================================================
# Equal-dataset V26C fault-family summary
# ============================================================

family_checkpoint_rows = []


for dataset, seed in identities:

    rows = [
        row
        for row in case_rows
        if (
            row[
                "dataset"
            ]
            ==
            dataset
            and
            int(
                row[
                    "seed"
                ]
            )
            ==
            seed
            and
            row[
                "condition"
            ]
            !=
            "baseline"
        )
    ]


    by_family = defaultdict(
        list
    )


    for row in rows:

        by_family[
            row[
                "family"
            ]
        ].append(
            row
        )


    for family, values in by_family.items():

        family_checkpoint_rows.append({
            "dataset":
                dataset,

            "seed":
                seed,

            "family":
                family,

            "accuracy":
                float(
                    np.mean(
                        [
                            row[
                                "accuracy"
                            ]
                            for row in values
                        ]
                    )
                ),

            "macro_f1":
                float(
                    np.mean(
                        [
                            row[
                                "macro_f1"
                            ]
                            for row in values
                        ]
                    )
                ),
        })


family_dataset_rows = []


families = sorted({
    row[
        "family"
    ]
    for row in family_checkpoint_rows
})


if len(
    families
) != 6:

    raise RuntimeError(
        "Expected six fault families"
    )


for dataset in DATASETS:

    for family in families:

        rows = [
            row
            for row
            in family_checkpoint_rows
            if (
                row[
                    "dataset"
                ]
                ==
                dataset
                and
                row[
                    "family"
                ]
                ==
                family
            )
        ]


        if not rows:

            raise RuntimeError(
                f"Missing family rows "
                f"{dataset}/{family}"
            )


        family_dataset_rows.append({
            "dataset":
                dataset,

            "family":
                family,

            "accuracy":
                float(
                    np.mean(
                        [
                            row[
                                "accuracy"
                            ]
                            for row in rows
                        ]
                    )
                ),

            "macro_f1":
                float(
                    np.mean(
                        [
                            row[
                                "macro_f1"
                            ]
                            for row in rows
                        ]
                    )
                ),
        })


family_equal_rows = []


for family in families:

    rows = [
        row
        for row in family_dataset_rows
        if row[
            "family"
        ]
        ==
        family
    ]


    if len(
        rows
    ) != 4:

        raise RuntimeError(
            f"{family}: expected four dataset rows"
        )


    family_equal_rows.append({
        "model":
            PROMOTED,

        "family":
            family,

        "accuracy":
            float(
                np.mean(
                    [
                        row[
                            "accuracy"
                        ]
                        for row in rows
                    ]
                )
            ),

        "macro_f1":
            float(
                np.mean(
                    [
                        row[
                            "macro_f1"
                        ]
                        for row in rows
                    ]
                )
            ),
    })


write_csv(
    OUT
    / "v26c_equal_dataset_fault_family_summary_6.csv",
    family_equal_rows,
)


# ============================================================
# Frozen 10-model comparison
# ============================================================

baseline_path = (
    R6A
    / "frozen_primary_baseline_summary_10.csv"
)


with baseline_path.open(
    newline="",
    encoding="utf-8",
) as f:

    baseline_rows = list(
        csv.DictReader(f)
    )


if len(
    baseline_rows
) != 10:

    raise RuntimeError(
        "Frozen primary baseline count != 10"
    )


def baseline_metric(
    row,
    metric,
):

    candidates = [
        metric,
        metric
        +
        "_mean",
        "mean_"
        +
        metric,
    ]


    for candidate in candidates:

        if (
            candidate in row
            and
            row[
                candidate
            ]
            not in {
                None,
                "",
            }
        ):

            return float(
                row[
                    candidate
                ]
            )


    raise RuntimeError(
        f"Cannot find baseline metric "
        f"{metric}; columns={list(row)}"
    )


baseline_models = {
    row[
        "model"
    ]:
        row

    for row in baseline_rows
}


if len(
    baseline_models
) != 10:

    raise RuntimeError(
        "Frozen baseline model names not unique"
    )


if "ReliabilityCNN_v25" not in baseline_models:

    raise RuntimeError(
        "Frozen V25 baseline row missing"
    )


comparison_long = []

v26_ranks = {}


for metric in ALL_METRICS:

    values = []


    for row in baseline_rows:

        values.append(
            (
                row[
                    "model"
                ],
                baseline_metric(
                    row,
                    metric,
                ),
            )
        )


    values.append(
        (
            PROMOTED,
            float(
                v26_equal[
                    metric
                ]
            ),
        )
    )


    values.sort(
        key=lambda pair: (
            -
            pair[
                1
            ],
            pair[
                0
            ],
        )
    )


    if len(
        values
    ) != 11:

        raise RuntimeError(
            "Comparison model count != 11"
        )


    for rank, (
        model,
        value,
    ) in enumerate(
        values,
        start=1,
    ):

        comparison_long.append({
            "metric":
                metric,

            "rank":
                rank,

            "model":
                model,

            "value":
                value,
        })


        if model == PROMOTED:

            v26_ranks[
                metric
            ] = rank


write_csv(
    OUT
    / "primary_comparison_rankings_88.csv",
    comparison_long,
)


if len(
    comparison_long
) != 88:

    raise RuntimeError(
        "Expected 88 comparison ranking rows"
    )


if len(
    v26_ranks
) != 8:

    raise RuntimeError(
        "V26 rank map incomplete"
    )


v25_row = baseline_models[
    "ReliabilityCNN_v25"
]


v25_metrics = {
    metric:
        baseline_metric(
            v25_row,
            metric,
        )

    for metric in ALL_METRICS
}


delta_vs_v25 = {
    metric:
        (
            float(
                v26_equal[
                    metric
                ]
            )
            -
            float(
                v25_metrics[
                    metric
                ]
            )
        )

    for metric in ALL_METRICS
}


# ============================================================
# Predeclared claim-tier interpretation
# ============================================================

claim_criteria = json.loads(
    (
        R4
        / "primary_confirmation_claim_criteria.json"
    ).read_text()
)


clean_delta = delta_vs_v25[
    "clean_macro_f1"
]

max_params = int(
    v26_equal[
        "max_parameter_count"
    ]
)

all_fault_rank = int(
    v26_ranks[
        "all_fault_macro_f1"
    ]
)

family_balanced_rank = int(
    v26_ranks[
        "family_balanced_macro_f1"
    ]
)


tier_a = (
    all_fault_rank
    <=
    1
    and
    family_balanced_rank
    <=
    1
    and
    clean_delta
    >=
    -0.015
    and
    max_params
    <=
    30000
)


tier_b = (
    (
        all_fault_rank
        ==
        1
        or
        family_balanced_rank
        ==
        1
    )
    and
    max(
        all_fault_rank,
        family_balanced_rank,
    )
    <=
    2
    and
    clean_delta
    >=
    -0.015
    and
    max_params
    <=
    30000
)


if tier_a:

    claim_tier = (
        "TIER_A_STRONG_INTERNAL_BENCHMARK_SUPERIORITY"
    )

elif tier_b:

    claim_tier = (
        "TIER_B_STRONG_ROBUSTNESS_EFFICIENCY_TRADEOFF"
    )

else:

    claim_tier = (
        "NO_PREDECLARED_STRONG_TIER"
    )


decision = {
    "candidate":
        PROMOTED,

    "comparison_model_count":
        11,

    "primary_metric_ranks": {
        "all_fault_macro_f1":
            all_fault_rank,

        "family_balanced_macro_f1":
            family_balanced_rank,
    },

    "all_metric_ranks":
        v26_ranks,

    "v26c_equal_dataset_metrics": {
        metric:
            float(
                v26_equal[
                    metric
                ]
            )

        for metric in ALL_METRICS
    },

    "delta_vs_frozen_v25": (
        delta_vs_v25
    ),

    "max_parameter_count":
        max_params,

    "clean_macro_f1_delta_vs_v25":
        clean_delta,

    "tier_a_pass":
        tier_a,

    "tier_b_pass":
        tier_b,

    "claim_tier":
        claim_tier,

    "universal_sota_claim_allowed":
        False,

    "storm_superiority_claim_allowed_here":
        False,

    "candidate_retraining_after_confirmation_allowed":
        False,

    "candidate_hyperparameter_change_after_confirmation_allowed":
        False,
}


write_json(
    OUT
    / "primary_confirmation_decision.json",
    decision,
)


# ============================================================
# Print scientific result
# ============================================================

print()
print("=" * 118)
print("V26C PROTECTED PRIMARY CONFIRMATION — EQUAL DATASET")
print("=" * 118)


for metric in ALL_METRICS:

    print(
        "V26C_PRIMARY:",
        metric,
        "=",
        f"{float(v26_equal[metric]):.9f}",
        "RANK=",
        v26_ranks[
            metric
        ],
        "/11",
        "DELTA_V25=",
        f"{delta_vs_v25[metric]:+.9f}",
    )


print()
print("=" * 118)
print("V26C PHYSICAL FAULT-FAMILY SUMMARY")
print("=" * 118)


for row in sorted(
    family_equal_rows,
    key=lambda x:
        x[
            "family"
        ],
):

    print(
        "V26C_FAMILY:",
        row[
            "family"
        ],
        "ACC=",
        f"{row['accuracy']:.9f}",
        "F1=",
        f"{row['macro_f1']:.9f}",
    )


print()
print(
    "V26C_PRIMARY_ALL_FAULT_F1_RANK=",
    all_fault_rank,
    "/11",
)

print(
    "V26C_PRIMARY_FAMILY_BALANCED_F1_RANK=",
    family_balanced_rank,
    "/11",
)

print(
    "V26C_CLEAN_F1_DELTA_VS_V25=",
    f"{clean_delta:+.9f}",
)

print(
    "V26C_MAX_PARAMETER_COUNT=",
    max_params,
)

print(
    "V26C_PREDECLARED_CLAIM_TIER=",
    claim_tier,
)


# ============================================================
# Final receipt
# ============================================================

(
    OUT
    / "PROTECTED_TEST_CONSUMED"
).write_text(
    "V26 R6B protected confirmation completed.\n"
)


receipt = {
    "stage":
        "V26_PRIMARY_CONFIRMATION_TEST_R6B",

    "status":
        "PASS",

    "promoted_candidate":
        PROMOTED,

    "evaluation_domain":
        PRE,

    "frozen_checkpoint_sha":
        "PASS_14_OF_14",

    "r4a_tensor_sha_preflight":
        "PASS_140_OF_140",

    "protected_tensor_sha_preflight":
        "PASS_72_OF_72",

    "all_protected_tensors_verified_before_first_forward":
        True,

    "protected_confirmation_checkpoints":
        14,

    "conditions_per_checkpoint":
        18,

    "protected_test_case_rows":
        252,

    "checkpoint_physical_summary_rows":
        14,

    "dataset_summary_rows":
        4,

    "comparison_model_count":
        11,

    "comparison_ranking_rows":
        88,

    "model_construction_count":
        model_construction_count,

    "checkpoint_deserialization_count":
        checkpoint_deserialization_count,

    "model_batch_forward_count":
        model_batch_forward_count,

    "protected_test_split_loaded":
        True,

    "protected_test_tensor_loaded":
        True,

    "protected_test_inference_performed":
        True,

    "training_performed":
        False,

    "optimizer_created":
        False,

    "backward_performed":
        False,

    "candidate_modified":
        False,

    "training_protocol_modified":
        False,

    "fault_protocol_modified":
        False,

    "checkpoint_modified":
        False,

    "storm_used":
        False,

    "candidate_retraining_after_confirmation_allowed":
        False,

    "claim_tier":
        claim_tier,

    "v26c_all_fault_macro_f1_rank":
        all_fault_rank,

    "v26c_family_balanced_macro_f1_rank":
        family_balanced_rank,

    "v26c_clean_macro_f1_delta_vs_v25":
        clean_delta,

    "v26c_max_parameter_count":
        max_params,

    "next_gate":
        (
            "Freeze R6B permanently. "
            "Perform read-only confirmation analysis/statistics, "
            "fault-family diagnosis, efficiency profiling, and only "
            "after the internal model is fully frozen may external "
            "STORM evaluation be opened. No V26C retraining or "
            "hyperparameter changes are permitted."
        ),
}


write_json(
    OUT
    / "v26_primary_confirmation_test_receipt_r6b.json",
    receipt,
)


print()
print("=" * 118)
print("V26 R6B FINAL RECEIPT")
print("=" * 118)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print(
    "V26_PRIMARY_CONFIRMATION_TEST_R6B_PASS=True"
)

print(
    "ALL_R4A_TENSOR_SHA_PREFLIGHT_PASS_140_OF_140=True"
)

print(
    "ALL_PROTECTED_TENSOR_SHA_PREFLIGHT_PASS_72_OF_72=True"
)

print(
    "ALL_72_PROTECTED_TENSORS_VERIFIED_BEFORE_FIRST_MODEL_FORWARD=True"
)

print(
    "V26_PROTECTED_CONFIRMATION_CASE_ROWS_PASS_252_OF_252=True"
)

print(
    "TRAINING_PERFORMED=False"
)

print(
    "CANDIDATE_MODIFIED=False"
)

print(
    "STORM_USED=False"
)

print(
    "PROTECTED_TEST_NOW_CONSUMED=True"
)
