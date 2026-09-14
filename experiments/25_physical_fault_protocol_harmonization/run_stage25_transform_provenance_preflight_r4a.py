from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

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

OUT = (
    ROOT
    / "results/stage25_physical_fault_protocol"
    / "transform_provenance_preflight_r4a"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


DATA_ROOT = (
    ROOT
    / "data/processed/harmonized"
)

SPLIT_ROOT = (
    ROOT
    / "data/processed/splits"
)


DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]


MODEL_NAMES = [
    "ReliabilityCNN_v22",
    "CNN1D",
    "LSTM",
    "DeepConvLSTM",
    "Transformer",
    "ReliabilityCNN_v24",
    "DS_CNN",
    "TCN",
    "TinyTransformer",
    "ReliabilityCNN_v25",
]


CHANNELS = [
    "accel_x",
    "accel_y",
    "accel_z",
    "gyro_x",
    "gyro_y",
    "gyro_z",
]


R3_SHA = (
    "a881b660145b4601ddf08444c4479eebb2935510d4be4c377d5e1896d930dba6"
)


# ============================================================
# Helpers
# ============================================================

def sha256_file(
    path: Path,
) -> str:

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
            h.update(block)

    return h.hexdigest()


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


def walk_scalars(
    obj,
    prefix="",
):

    rows = []

    if isinstance(
        obj,
        dict,
    ):

        for key, value in obj.items():

            kp = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            if isinstance(
                value,
                (
                    bool,
                    int,
                    float,
                    str,
                ),
            ) or value is None:

                rows.append(
                    (
                        kp,
                        value,
                    )
                )

            else:

                rows.extend(
                    walk_scalars(
                        value,
                        kp,
                    )
                )


    elif isinstance(
        obj,
        list,
    ):

        # Do not recursively enumerate long epoch histories.
        if len(obj) <= 10:

            for i, value in enumerate(
                obj
            ):

                rows.extend(
                    walk_scalars(
                        value,
                        f"{prefix}[{i}]",
                    )
                )


    return rows


def normalize(
    raw: np.ndarray,
    mean: np.ndarray,
    std: np.ndarray,
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


def apply_stuck(
    x: np.ndarray,
    channels,
    tau: np.ndarray,
):

    out = np.array(
        x,
        copy=True,
    )

    n = out.shape[0]

    for i in range(n):

        t = int(
            tau[i]
        )

        # Work through an explicit [time, channel] view.
        # NumPy mixed slicing + advanced channel indexing in
        # out[i, t:, channels] produces a transposed advanced-
        # indexing layout and cannot broadcast the [channels]
        # stuck-value vector correctly.
        #
        # Scientific semantics remain unchanged:
        # from tau onward, repeat each selected channel's own
        # value at tau.
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


def array_stats(
    arr: np.ndarray,
):

    a = np.asarray(
        arr,
        dtype=np.float64,
    )

    return {
        "min":
            float(
                np.min(a)
            ),

        "max":
            float(
                np.max(a)
            ),

        "mean":
            float(
                np.mean(a)
            ),

        "std":
            float(
                np.std(a)
            ),
    }


# ============================================================
# Header
# ============================================================

print(
    "=" * 112
)

print(
    "STAGE25 R4A TRANSFORM + CLEAN-REFERENCE "
    "PROVENANCE PREFLIGHT"
)

print(
    "NO MODEL DESERIALIZATION / NO MODEL FORWARD / NO TRAINING"
)

print(
    "=" * 112
)


# ============================================================
# 1. Verify R3 receipt
# ============================================================

r3_receipt_path = (
    R3
    / "stage25_protocol_preregistration_receipt_r3.json"
)

if not r3_receipt_path.exists():

    raise FileNotFoundError(
        r3_receipt_path
    )


r3_receipt = json.loads(
    r3_receipt_path.read_text()
)


required_r3 = {
    "status":
        "PASS",

    "protocol_frozen_before_corrupted_inference":
        True,

    "model_bank_frozen":
        "PASS_200_OF_200",

    "fault_conditions":
        17,

    "condition_domain_cases_per_checkpoint":
        35,

    "expected_case_rows":
        7000,

    "corrupted_inference_performed":
        False,
}


for key, expected in required_r3.items():

    actual = r3_receipt.get(
        key
    )

    if actual != expected:

        raise RuntimeError(
            f"R3 prerequisite mismatch: "
            f"{key}={actual!r}, "
            f"expected={expected!r}"
        )


print(
    "R3_PROTOCOL_PREREQUISITES_PASS=True"
)


# ============================================================
# 2. Frozen model bank
# ============================================================

bank_path = (
    R3
    / "frozen_model_bank_200.csv"
)

if not bank_path.exists():

    raise FileNotFoundError(
        bank_path
    )


with bank_path.open(
    newline="",
    encoding="utf-8",
) as f:

    model_bank = list(
        csv.DictReader(f)
    )


if len(
    model_bank
) != 200:

    raise RuntimeError(
        f"Expected 200 frozen checkpoints, "
        f"found {len(model_bank)}"
    )


for row in model_bank:

    ckpt = (
        ROOT
        / row[
            "checkpoint"
        ]
    )

    if not ckpt.exists():

        raise FileNotFoundError(
            ckpt
        )

    actual_sha = (
        sha256_file(
            ckpt
        )
    )

    if actual_sha != row[
        "checkpoint_sha256"
    ]:

        raise RuntimeError(
            "Checkpoint SHA changed after R3: "
            f"{ckpt}"
        )


print(
    "R4A_MODEL_BANK_SHA_PASS_200_OF_200=True"
)


# ============================================================
# 3. Model-source provenance audit
#
# Search source only.
# Do NOT import modules.
# ============================================================

print()
print(
    "=" * 112
)

print(
    "MODEL SOURCE PROVENANCE"
)

print(
    "=" * 112
)


source_roots = [
    ROOT
    / "experiments/16_benchmark_suite",

    ROOT
    / "experiments/17_v25_screening",

    ROOT
    / "experiments/18_v25_training_ablation",

    ROOT
    / "experiments/19_v25_final_confirmation",
]


python_files = []


for base in source_roots:

    if not base.exists():
        continue

    for path in base.rglob(
        "*.py"
    ):

        if "__pycache__" in path.parts:
            continue

        python_files.append(
            path
        )


source_hits = []


for model_name in MODEL_NAMES:

    hits = []

    class_hits = []

    for path in python_files:

        try:

            if path.stat().st_size > 3_000_000:
                continue

            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

        except Exception:
            continue


        if model_name not in text:
            continue


        hits.append(
            str(
                path.relative_to(
                    ROOT
                )
            )
        )


        try:

            tree = ast.parse(
                text
            )

            for node in ast.walk(
                tree
            ):

                if isinstance(
                    node,
                    ast.ClassDef,
                ):

                    if (
                        node.name
                        ==
                        model_name
                    ):

                        class_hits.append({
                            "file":
                                str(
                                    path.relative_to(
                                        ROOT
                                    )
                                ),

                            "class":
                                node.name,

                            "line":
                                node.lineno,
                        })

        except Exception:
            pass


    hits = sorted(
        set(hits)
    )


    if not hits:

        raise RuntimeError(
            f"No frozen source evidence found "
            f"for model {model_name}"
        )


    source_hits.append({
        "model":
            model_name,

        "source_file_hits":
            hits,

        "exact_class_definitions":
            class_hits,
    })


    print(
        "MODEL_SOURCE_PASS:",
        model_name,
        "FILES=",
        len(hits),
        "CLASS_DEFS=",
        len(class_hits),
    )


write_json(
    OUT
    / "model_source_provenance_10.json",
    source_hits,
)


print(
    "MODEL_SOURCE_EVIDENCE_PASS_10_OF_10=True"
)


# ============================================================
# 4. Clean-reference provenance inventory
#
# Important:
# We do NOT choose metric fields yet.
# We inventory direct per-run evidence so the clean-gate
# source can be selected without guessing.
# ============================================================

print()
print(
    "=" * 112
)

print(
    "CLEAN REFERENCE PROVENANCE INVENTORY"
)

print(
    "=" * 112
)


candidate_rows = []

run_inventory = []

signature_counts = Counter()

runs_with_json = 0

runs_with_metric_candidates = 0


metric_rx = re.compile(
    r"acc|accuracy|macro.?f1|f1",
    re.I,
)

clean_context_rx = re.compile(
    r"clean|test|final|best",
    re.I,
)


for row in model_bank:

    checkpoint = (
        ROOT
        / row[
            "checkpoint"
        ]
    )

    run_dir = (
        checkpoint.parent
    )


    json_files = sorted(
        run_dir.glob(
            "*.json"
        )
    )


    if json_files:

        runs_with_json += 1


    run_candidates = []


    for path in json_files:

        try:

            if path.stat().st_size > 5_000_000:
                continue

            obj = json.loads(
                path.read_text()
            )

        except Exception:
            continue


        for key, value in walk_scalars(
            obj
        ):

            if isinstance(
                value,
                bool,
            ):
                continue

            if not isinstance(
                value,
                (
                    int,
                    float,
                ),
            ):
                continue


            if not metric_rx.search(
                key
            ):
                continue


            strong_context = bool(
                clean_context_rx.search(
                    key
                )
                or
                clean_context_rx.search(
                    path.name
                )
            )


            candidate = {
                "bank_source":
                    row[
                        "bank_source"
                    ],

                "dataset":
                    row[
                        "dataset"
                    ],

                "model":
                    row[
                        "model"
                    ],

                "seed":
                    int(
                        row[
                            "seed"
                        ]
                    ),

                "checkpoint_sha256":
                    row[
                        "checkpoint_sha256"
                    ],

                "json_file":
                    str(
                        path.relative_to(
                            ROOT
                        )
                    ),

                "metric_key":
                    key,

                "metric_value":
                    float(
                        value
                    ),

                "strong_clean_test_context":
                    strong_context,
            }


            run_candidates.append(
                candidate
            )

            candidate_rows.append(
                candidate
            )


            signature = (
                f"{path.name}"
                f"::{key}"
            )

            signature_counts[
                signature
            ] += 1


    if run_candidates:

        runs_with_metric_candidates += 1


    run_inventory.append({
        "bank_source":
            row[
                "bank_source"
            ],

        "dataset":
            row[
                "dataset"
            ],

        "model":
            row[
                "model"
            ],

        "seed":
            int(
                row[
                    "seed"
                ]
        ),

        "checkpoint":
            row[
                "checkpoint"
            ],

        "checkpoint_sha256":
            row[
                "checkpoint_sha256"
            ],

        "json_files":
            [
                p.name
                for p in json_files
            ],

        "metric_candidate_count":
            len(
                run_candidates
            ),

        "strong_context_candidate_count":
            sum(
                bool(
                    x[
                        "strong_clean_test_context"
                    ]
                )
                for x in run_candidates
            ),
    })


with (
    OUT
    / "clean_reference_metric_candidates.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "bank_source",
        "dataset",
        "model",
        "seed",
        "checkpoint_sha256",
        "json_file",
        "metric_key",
        "metric_value",
        "strong_clean_test_context",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()
    writer.writerows(
        candidate_rows
    )


write_json(
    OUT
    / "clean_reference_run_inventory_200.json",
    run_inventory,
)


signature_table = [
    {
        "signature":
            signature,

        "count":
            count,
    }

    for signature, count in sorted(
        signature_counts.items(),
        key=lambda x: (
            -x[1],
            x[0],
        ),
    )
]


write_json(
    OUT
    / "clean_reference_metric_signature_counts.json",
    signature_table,
)


print(
    "CLEAN_REFERENCE_RUNS_INVENTORIED=",
    len(
        run_inventory
    ),
)

print(
    "RUNS_WITH_DIRECT_JSON=",
    runs_with_json,
)

print(
    "RUNS_WITH_METRIC_CANDIDATES=",
    runs_with_metric_candidates,
)

print(
    "TOTAL_SCALAR_METRIC_CANDIDATES=",
    len(
        candidate_rows
    ),
)


print()
print(
    "TOP CLEAN-REFERENCE METRIC SIGNATURES"
)


for row in signature_table[:60]:

    print(
        row[
            "count"
        ],
        row[
            "signature"
        ],
    )


print(
    "CLEAN_REFERENCE_PROVENANCE_INVENTORY_COMPLETE_200_OF_200=True"
)


# ============================================================
# 5. Load frozen transform protocol
# ============================================================

protocol_path = (
    R3
    / "stage25_physical_fault_protocol_r3.json"
)

seed_manifest_path = (
    R3
    / "stochastic_fault_seed_manifest_24.csv"
)

normalization_path = (
    R2
    / "dataset_normalization_receipts.json"
)


for path in [
    protocol_path,
    seed_manifest_path,
    normalization_path,
]:

    if not path.exists():

        raise FileNotFoundError(
            path
        )


protocol = json.loads(
    protocol_path.read_text()
)

normalization = json.loads(
    normalization_path.read_text()
)


faults = protocol[
    "fault_conditions"
]


if len(
    faults
) != 17:

    raise RuntimeError(
        "Frozen R3 fault count changed"
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
        "Frozen stochastic seed manifest changed"
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


print()
print(
    "FROZEN_TRANSFORM_PROTOCOL_BOUND=True"
)


# ============================================================
# 6. Transform-only paired-domain preflight
#
# Generate transient arrays only.
# Nothing is fed into a model.
# ============================================================

print()
print(
    "=" * 112
)

print(
    "PAIRED-DOMAIN TRANSFORM PREFLIGHT"
)

print(
    "=" * 112
)


tensor_rows = []

pair_rows = []


commuting_conditions = {
    "acc_noise_sigma0.5",
    "gyro_noise_sigma0.5",
    "acc_stuck_value",
    "gyro_stuck_value",
}


expected_noncommuting = {
    fault[
        "name"
    ]
    for fault in faults
    if fault[
        "name"
    ]
    not in commuting_conditions
}


commuting_pass = 0

commuting_total = 0


for dataset in DATASETS:

    print()
    print(
        "-" * 100
    )

    print(
        "DATASET=",
        dataset
    )

    print(
        "-" * 100
    )


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


    if not X_path.exists():

        raise FileNotFoundError(
            X_path
        )


    if not test_idx_path.exists():

        raise FileNotFoundError(
            test_idx_path
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
        ][
            "mean"
        ],
        dtype=np.float32,
    )

    std = np.asarray(
        normalization[
            dataset
        ][
            "std"
        ],
        dtype=np.float32,
    )


    clean = normalize(
        raw,
        mean,
        std,
    )


    clean_sha = (
        sha256_array(
            clean
        )
    )


    clean_stats = (
        array_stats(
            clean
        )
    )


    tensor_rows.append({
        "dataset":
            dataset,

        "condition":
            "baseline",

        "domain":
            "shared_clean",

        "family":
            "baseline",

        "tensor_sha256":
            clean_sha,

        "shape":
            str(
                tuple(
                    clean.shape
                )
            ),

        "dtype":
            str(
                clean.dtype
            ),

        "min":
            clean_stats[
                "min"
            ],

        "max":
            clean_stats[
                "max"
            ],

        "mean":
            clean_stats[
                "mean"
            ],

        "std":
            clean_stats[
                "std"
            ],
    })


    print(
        "BASELINE_TENSOR_SHA256=",
        clean_sha,
    )


    for fault in faults:

        name = fault[
            "name"
        ]

        family = fault[
            "family"
        ]

        channels = [
            int(x)
            for x in fault[
                "channels"
            ]
        ]


        # --------------------------------------------------------
        # Shared stochastic objects
        # --------------------------------------------------------

        mask = None
        epsilon = None
        tau = None

        # Gaussian-only numerical-harness buffers.
        #
        # These do NOT change the frozen Gaussian mathematics.
        # They allow the mathematically equivalent pre- and
        # post-normalization operators to be evaluated with
        # higher-precision intermediates and rounded exactly
        # once to the canonical model-input dtype.
        gaussian_pre_selected = None
        gaussian_post_selected = None
        gaussian_math_max_diff = None


        if fault[
            "stochastic"
        ]:

            key = (
                dataset,
                name,
            )


            if key not in seed_lookup:

                raise RuntimeError(
                    f"Missing frozen stochastic seed: {key}"
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
                    f"Unexpected stochastic family: {family}"
                )


        # --------------------------------------------------------
        # PRE-normalization domain
        # --------------------------------------------------------

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

                channel_view = (
                    pre_raw[
                        :,
                        :,
                        channel,
                    ]
                )

                channel_view[
                    mask
                ] = 0.0


        elif family == "gaussian_noise":

            # R4A-N1 proved that direct float32 evaluation of
            # the two mathematically equivalent Gaussian paths
            # differs by several ulps on some datasets because
            # of operation ordering.
            #
            # Preserve the exact frozen operator:
            #
            # PRE:
            #   ((x + 0.5*sigma*eps) - mu) / sigma
            #
            # POST:
            #   ((x - mu) / sigma) + 0.5*eps
            #
            # using the SAME frozen float32 x/mu/sigma/epsilon
            # values, promoted only for intermediate arithmetic.
            # Each result is rounded once to float32.
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

            gaussian_math_max_diff = float(
                np.max(
                    np.abs(
                        gaussian_pre64
                        -
                        gaussian_post64
                    )
                )
            )

            if gaussian_math_max_diff > 1e-12:
                raise RuntimeError(
                    "Gaussian mathematical commutation failed "
                    f"before float32 cast: "
                    f"{dataset}/{name}, "
                    f"max_diff={gaussian_math_max_diff}"
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

            cast_pair_max_diff = float(
                np.max(
                    np.abs(
                        gaussian_pre_selected.astype(
                            np.float64
                        )
                        -
                        gaussian_post_selected.astype(
                            np.float64
                        )
                    )
                )
            )

            if cast_pair_max_diff > 1e-6:
                raise RuntimeError(
                    "Gaussian one-round float32 commutation "
                    "failed frozen 1e-6 gate: "
                    f"{dataset}/{name}, "
                    f"max_diff={cast_pair_max_diff}"
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
                f"Unknown family: {family}"
            )


        pre_norm = normalize(
            pre_raw,
            mean,
            std,
        )


        if family == "gaussian_noise":

            if gaussian_pre_selected is None:
                raise RuntimeError(
                    "Gaussian pre-normalization selected tensor "
                    "was not constructed"
                )

            # Preserve canonical float32 normalization on every
            # uncorrupted channel. Replace ONLY selected Gaussian
            # channels with the one-round high-precision result.
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


        # --------------------------------------------------------
        # POST-normalization domain
        # --------------------------------------------------------

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

                channel_view = (
                    post_norm[
                        :,
                        :,
                        channel,
                    ]
                )

                channel_view[
                    mask
                ] = 0.0


        elif family == "gaussian_noise":

            if gaussian_post_selected is None:
                raise RuntimeError(
                    "Gaussian post-normalization selected tensor "
                    "was not constructed"
                )

            # As above, all unselected channels remain byte-for-
            # byte the canonical clean float32 normalization.
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


        else:

            raise RuntimeError(
                f"Unknown family: {family}"
            )


        # --------------------------------------------------------
        # Hash/stats only; tensors are not saved.
        # --------------------------------------------------------

        pre_sha = (
            sha256_array(
                pre_norm
            )
        )

        post_sha = (
            sha256_array(
                post_norm
            )
        )


        pre_stats = (
            array_stats(
                pre_norm
            )
        )

        post_stats = (
            array_stats(
                post_norm
            )
        )


        for domain, tensor, digest, stats in [
            (
                "pre_normalization_sensor_domain",
                pre_norm,
                pre_sha,
                pre_stats,
            ),

            (
                "post_normalization_domain",
                post_norm,
                post_sha,
                post_stats,
            ),
        ]:

            tensor_rows.append({
                "dataset":
                    dataset,

                "condition":
                    name,

                "domain":
                    domain,

                "family":
                    family,

                "tensor_sha256":
                    digest,

                "shape":
                    str(
                        tuple(
                            tensor.shape
                        )
                    ),

                "dtype":
                    str(
                        tensor.dtype
                    ),

                "min":
                    stats[
                        "min"
                    ],

                "max":
                    stats[
                        "max"
                    ],

                "mean":
                    stats[
                        "mean"
                    ],

                "std":
                    stats[
                        "std"
                    ],
            })


        max_diff = float(
            np.max(
                np.abs(
                    pre_norm.astype(
                        np.float64
                    )
                    -
                    post_norm.astype(
                        np.float64
                    )
                )
            )
        )


        mean_diff = float(
            np.mean(
                np.abs(
                    pre_norm.astype(
                        np.float64
                    )
                    -
                    post_norm.astype(
                        np.float64
                    )
                )
            )
        )


        is_commuting = (
            name
            in
            commuting_conditions
        )


        pair_pass = None


        if is_commuting:

            commuting_total += 1

            pair_pass = (
                max_diff
                <=
                1e-6
            )


            if not pair_pass:

                raise RuntimeError(
                    "Commutation control failed: "
                    f"{dataset}/{name}, "
                    f"max_diff={max_diff}"
                )


            commuting_pass += 1


        pair_rows.append({
            "dataset":
                dataset,

            "condition":
                name,

            "family":
                family,

            "expected_commuting":
                is_commuting,

            "max_abs_domain_difference":
                max_diff,

            "mean_abs_domain_difference":
                mean_diff,

            "pre_tensor_sha256":
                pre_sha,

            "post_tensor_sha256":
                post_sha,

            "commutation_gate_pass":
                pair_pass,
        })


        print(
            "PAIR:",
            name,
            "family=",
            family,
            "commuting=",
            is_commuting,
            "max_diff=",
            f"{max_diff:.9g}",
            "mean_diff=",
            f"{mean_diff:.9g}",
        )


        del pre_raw
        del pre_norm
        del post_norm


    del raw
    del clean
    del X


# ============================================================
# 7. Cardinality checks
# ============================================================

if len(
    tensor_rows
) != 140:

    raise RuntimeError(
        f"Expected 140 dataset-condition-domain tensors, "
        f"found {len(tensor_rows)}"
    )


if len(
    pair_rows
) != 68:

    raise RuntimeError(
        f"Expected 68 paired fault comparisons, "
        f"found {len(pair_rows)}"
    )


# 4 datasets × 4 commuting conditions
if commuting_total != 16:

    raise RuntimeError(
        f"Expected 16 commuting controls, "
        f"found {commuting_total}"
    )


if commuting_pass != 16:

    raise RuntimeError(
        f"Expected all 16 commuting controls to pass, "
        f"got {commuting_pass}"
    )


print()
print(
    "DATASET_CONDITION_TENSOR_MANIFEST_PASS_140=True"
)

print(
    "PAIRED_FAULT_COMPARISONS_PASS_68=True"
)

print(
    "COMMUTATION_CONTROLS_PASS_16_OF_16=True"
)


# ============================================================
# 8. Write transform manifests
# ============================================================

with (
    OUT
    / "dataset_condition_tensor_manifest_140.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "dataset",
        "condition",
        "domain",
        "family",
        "tensor_sha256",
        "shape",
        "dtype",
        "min",
        "max",
        "mean",
        "std",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()

    writer.writerows(
        tensor_rows
    )


with (
    OUT
    / "paired_domain_transform_comparison_68.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "dataset",
        "condition",
        "family",
        "expected_commuting",
        "max_abs_domain_difference",
        "mean_abs_domain_difference",
        "pre_tensor_sha256",
        "post_tensor_sha256",
        "commutation_gate_pass",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()

    writer.writerows(
        pair_rows
    )


# ============================================================
# 9. Summarize noncommuting domain effects
#
# No model results here.
# This is purely transformed-input geometry.
# ============================================================

family_diff = defaultdict(
    list
)


for row in pair_rows:

    if row[
        "expected_commuting"
    ]:

        continue

    family_diff[
        row[
            "family"
        ]
    ].append(
        float(
            row[
                "mean_abs_domain_difference"
            ]
        )
    )


print()
print(
    "=" * 112
)

print(
    "TRANSFORM-ONLY DOMAIN DIFFERENCE BY FAMILY"
)

print(
    "=" * 112
)


family_rows = []


for family in sorted(
    family_diff
):

    values = np.asarray(
        family_diff[
            family
        ],
        dtype=np.float64,
    )


    item = {
        "family":
            family,

        "n_dataset_conditions":
            int(
                len(values)
            ),

        "mean_abs_domain_difference_mean":
            float(
                np.mean(values)
            ),

        "mean_abs_domain_difference_min":
            float(
                np.min(values)
            ),

        "mean_abs_domain_difference_max":
            float(
                np.max(values)
            ),
    }


    family_rows.append(
        item
    )


    print(
        family,
        item
    )


write_json(
    OUT
    / "transform_only_family_domain_difference.json",
    family_rows,
)


# ============================================================
# 10. Final R4A receipt
# ============================================================

receipt = {
    "audit":
        "STAGE25_TRANSFORM_PROVENANCE_PREFLIGHT_R4A",

    "status":
        "PASS",

    "r3_sha256sums_sha256":
        R3_SHA,

    "model_bank_sha_verified":
        "PASS_200_OF_200",

    "model_source_evidence":
        "PASS_10_OF_10",

    "clean_reference_runs_inventoried":
        200,

    "clean_reference_metric_candidates_found":
        len(
            candidate_rows
        ),

    "clean_reference_selection_finalized":
        False,

    "dataset_condition_tensor_manifest":
        "PASS_140",

    "paired_fault_transform_comparisons":
        "PASS_68",

    "commutation_controls":
        "PASS_16_OF_16",

    "commuting_families": [
        "gaussian_noise",
        "stuck_value",
    ],

    "expected_noncommuting_families": [
        "modality_outage",
        "single_axis_outage",
        "intermittent_dropout",
        "scale_drift",
    ],

    "full_corrupted_tensors_saved":
        False,

    "tensor_hashes_saved":
        True,

    "clean_model_inference_performed":
        False,

    "corrupted_model_inference_performed":
        False,

    "model_deserialization_performed":
        False,

    "training_performed":
        False,

    "checkpoint_modified":
        False,

    "dataset_modified":
        False,

    "v3r1_results_modified":
        False,

    "v25_results_modified":
        False,

    "next_gate": (
        "Resolve exactly one canonical clean accuracy and "
        "macro-F1 reference per frozen checkpoint from the "
        "provenance inventory; audit exact model constructors; "
        "then run clean-only reproduction for 200/200 checkpoints."
    ),
}


write_json(
    OUT
    / "stage25_transform_provenance_preflight_receipt_r4a.json",
    receipt,
)


print()
print(
    "=" * 112
)

print(
    "STAGE25 R4A FINAL RECEIPT"
)

print(
    "=" * 112
)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print(
    "STAGE25_TRANSFORM_PROVENANCE_PREFLIGHT_R4A_PASS=True"
)

print(
    "R4A_MODEL_BANK_SHA_PASS_200_OF_200=True"
)

print(
    "MODEL_SOURCE_EVIDENCE_PASS_10_OF_10=True"
)

print(
    "CLEAN_REFERENCE_PROVENANCE_INVENTORY_COMPLETE_200_OF_200=True"
)

print(
    "DATASET_CONDITION_TENSOR_MANIFEST_PASS_140=True"
)

print(
    "PAIRED_FAULT_COMPARISONS_PASS_68=True"
)

print(
    "COMMUTATION_CONTROLS_PASS_16_OF_16=True"
)

print(
    "CLEAN_MODEL_INFERENCE_PERFORMED=False"
)

print(
    "CORRUPTED_MODEL_INFERENCE_PERFORMED=False"
)

print(
    "MODEL_DESERIALIZATION_PERFORMED=False"
)

print(
    "TRAINING_PERFORMED=False"
)

print(
    "CHECKPOINTS_MODIFIED=False"
)

print(
    "DATASET_ARRAYS_MODIFIED=False"
)
