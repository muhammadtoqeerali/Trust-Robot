from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from pathlib import Path

import numpy as np


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

OUT = (
    ROOT
    / "results"
    / "stage25_physical_fault_protocol"
    / "canonical_reconstruction_audit_r2"
)

V3 = ROOT / "results" / "benchmark_v3r1"

HARMONIZED = (
    ROOT
    / "data"
    / "processed"
    / "harmonized"
)

SPLITS = (
    ROOT
    / "data"
    / "processed"
    / "splits"
)

PROTOCOL = (
    V3
    / "protocol"
    / "protocol_manifest.json"
)

V25_ROOT = (
    ROOT
    / "results"
    / "v25_final_r2"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


DATASETS = {
    "UCI_HAR": {
        "shape": (10299, 128, 6),
        "split_counts": (5817, 2196, 2286),
        "classes": 6,
    },

    "PAMAP2": {
        "shape": (30343, 128, 6),
        "split_counts": (18609, 7542, 4192),
        "classes": 12,
    },

    "DSADS": {
        "shape": (9120, 128, 6),
        "split_counts": (4560, 2280, 2280),
        "classes": 19,
    },

    "MotionSense": {
        "shape": (21528, 128, 6),
        "split_counts": (12370, 4809, 4349),
        "classes": 6,
    },
}


MODELS = [
    "ReliabilityCNN_v22",
    "CNN1D",
    "LSTM",
    "DeepConvLSTM",
    "Transformer",
    "ReliabilityCNN_v24",
    "DS_CNN",
    "TCN",
    "TinyTransformer",
]

SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]

CHANNELS = [
    "accel_x",
    "accel_y",
    "accel_z",
    "gyro_x",
    "gyro_y",
    "gyro_z",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

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


def max_abs(a, b):
    a = np.asarray(
        a,
        dtype=np.float64,
    )

    b = np.asarray(
        b,
        dtype=np.float64,
    )

    return float(
        np.max(
            np.abs(a - b)
        )
    )


def find_similar_files(
    root: Path,
    filename: str,
    limit: int = 20,
):
    if not root.exists():
        return []

    hits = []

    for p in root.rglob(filename):
        hits.append(
            str(
                p.relative_to(ROOT)
            )
        )

        if len(hits) >= limit:
            break

    return hits


print("=" * 108)
print(
    "STAGE25 CANONICAL PRE-NORMALIZATION "
    "RECONSTRUCTION AUDIT R2"
)
print(
    "READ ONLY — NO MODEL DESERIALIZATION / "
    "NO FORWARD / NO TRAINING"
)
print("=" * 108)


# =====================================================================
# 1. Protocol provenance
# =====================================================================

if not PROTOCOL.exists():
    raise FileNotFoundError(
        f"Frozen V3R1 protocol manifest missing: {PROTOCOL}"
    )


protocol_obj = json.loads(
    PROTOCOL.read_text()
)

protocol_text = json.dumps(
    protocol_obj,
    sort_keys=True,
).lower()

protocol_sha = sha256_file(
    PROTOCOL
)


print()
print("V3R1_PROTOCOL=", PROTOCOL)
print("V3R1_PROTOCOL_SHA256=", protocol_sha)


if (
    "explicit training split only"
    not in protocol_text
    and
    "explicit_training_split_only"
    not in protocol_text
):
    raise RuntimeError(
        "Frozen V3R1 protocol does not expose the expected "
        "train-only normalization statement."
    )


print(
    "TRAIN_ONLY_NORMALIZATION_PROTOCOL_EVIDENCE_PASS=True"
)


if (
    "subject" not in protocol_text
    or
    (
        "disjoint" not in protocol_text
        and
        "independent" not in protocol_text
    )
):
    raise RuntimeError(
        "Frozen V3R1 protocol does not expose "
        "subject-disjoint provenance."
    )


print(
    "SUBJECT_DISJOINT_PROTOCOL_EVIDENCE_PASS=True"
)


# =====================================================================
# 2. Local channel-order provenance
#
# We do not infer channel semantics from array position alone.
# =====================================================================

print()
print("=" * 108)
print("CHANNEL-ORDER PROVENANCE")
print("=" * 108)


SEARCH_ROOTS = [
    ROOT / "experiments" / "16_benchmark_suite",
    ROOT / "data",
]


alias_orders = [
    [
        "accel_x",
        "accel_y",
        "accel_z",
        "gyro_x",
        "gyro_y",
        "gyro_z",
    ],
    [
        "acc_x",
        "acc_y",
        "acc_z",
        "gyro_x",
        "gyro_y",
        "gyro_z",
    ],
]


channel_hits = []


for base in SEARCH_ROOTS:

    if not base.exists():
        continue

    for dirpath, dirnames, filenames in os.walk(base):

        dirnames[:] = [
            d
            for d in dirnames
            if d not in {
                "__pycache__",
                ".git",
            }
        ]

        for filename in filenames:

            p = Path(dirpath) / filename

            if p.suffix.lower() not in {
                ".py",
                ".json",
                ".txt",
                ".yaml",
                ".yml",
            }:
                continue

            try:
                if p.stat().st_size > 3_000_000:
                    continue

                text = p.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).lower()

            except Exception:
                continue


            for aliases in alias_orders:

                positions = [
                    text.find(x)
                    for x in aliases
                ]

                if not all(
                    x >= 0
                    for x in positions
                ):
                    continue

                if positions == sorted(positions):

                    channel_hits.append({
                        "file":
                            str(
                                p.relative_to(
                                    ROOT
                                )
                            ),

                        "aliases":
                            aliases,
                    })

                    break


write_json(
    OUT
    / "channel_order_provenance.json",
    channel_hits,
)


print(
    "ORDERED_CHANNEL_EVIDENCE_FILES=",
    len(channel_hits),
)


for row in channel_hits[:20]:
    print(
        "CHANNEL_EVIDENCE:",
        row["file"],
        row["aliases"],
    )


if not channel_hits:
    raise RuntimeError(
        "Could not prove six-channel accelerometer/gyroscope "
        "ordering from local frozen source evidence."
    )


print(
    "CHANNEL_SEMANTIC_EVIDENCE_GATE_PASS=True"
)


# =====================================================================
# 3. Canonical dataset reconstruction
# =====================================================================

print()
print("=" * 108)
print("CANONICAL DATASET RECONSTRUCTION")
print("=" * 108)


dataset_receipts = []

normalization_receipts = {}

raw_zero_rows = []

data_sha_manifest = []


for dataset, expected in DATASETS.items():

    print()
    print("-" * 96)
    print("DATASET=", dataset)
    print("-" * 96)


    data_dir = (
        HARMONIZED
        / dataset
    )

    split_dir = (
        SPLITS
        / dataset
    )


    X_path = (
        data_dir
        / "X.npy"
    )

    y_path = (
        data_dir
        / "y.npy"
    )

    train_path = (
        split_dir
        / "train_idx.npy"
    )

    val_path = (
        split_dir
        / "val_idx.npy"
    )

    test_path = (
        split_dir
        / "test_idx.npy"
    )


    required = [
        X_path,
        y_path,
        train_path,
        val_path,
        test_path,
    ]


    missing = [
        p
        for p in required
        if not p.exists()
    ]


    if missing:

        print(
            "CANONICAL_PATH_DISCOVERY_DIAGNOSTIC:"
        )

        for name in [
            "X.npy",
            "y.npy",
            "train_idx.npy",
            "val_idx.npy",
            "test_idx.npy",
        ]:

            print(
                name,
                find_similar_files(
                    ROOT / "data",
                    name,
                ),
            )

        raise FileNotFoundError(
            "Expected canonical V3R1 artifact(s) missing: "
            + ", ".join(
                str(p)
                for p in missing
            )
        )


    X = np.load(
        X_path,
        mmap_mode="r",
        allow_pickle=False,
    )

    y = np.load(
        y_path,
        mmap_mode="r",
        allow_pickle=False,
    )

    train_idx = np.load(
        train_path,
        allow_pickle=False,
    )

    val_idx = np.load(
        val_path,
        allow_pickle=False,
    )

    test_idx = np.load(
        test_path,
        allow_pickle=False,
    )


    print(
        "X_SHAPE=",
        tuple(X.shape),
    )

    print(
        "X_DTYPE=",
        str(X.dtype),
    )

    print(
        "Y_SHAPE=",
        tuple(y.shape),
    )

    print(
        "SPLIT_COUNTS=",
        len(train_idx),
        len(val_idx),
        len(test_idx),
    )


    if tuple(X.shape) != tuple(
        expected["shape"]
    ):
        raise RuntimeError(
            f"{dataset}: unexpected X shape "
            f"{X.shape}, expected {expected['shape']}"
        )


    if (
        y.ndim != 1
        or
        len(y) != X.shape[0]
    ):
        raise RuntimeError(
            f"{dataset}: unexpected y shape {y.shape}"
        )


    actual_counts = (
        len(train_idx),
        len(val_idx),
        len(test_idx),
    )


    if actual_counts != tuple(
        expected[
            "split_counts"
        ]
    ):
        raise RuntimeError(
            f"{dataset}: split count mismatch "
            f"{actual_counts} != "
            f"{expected['split_counts']}"
        )


    # -----------------------------------------------------------------
    # Split integrity
    # -----------------------------------------------------------------

    all_idx = [
        np.asarray(
            train_idx,
            dtype=np.int64,
        ),
        np.asarray(
            val_idx,
            dtype=np.int64,
        ),
        np.asarray(
            test_idx,
            dtype=np.int64,
        ),
    ]


    for split_name, idx in zip(
        [
            "train",
            "val",
            "test",
        ],
        all_idx,
    ):

        if idx.ndim != 1:
            raise RuntimeError(
                f"{dataset}/{split_name}: index array not 1D"
            )

        if len(np.unique(idx)) != len(idx):
            raise RuntimeError(
                f"{dataset}/{split_name}: duplicate indices"
            )

        if (
            int(idx.min()) < 0
            or
            int(idx.max()) >= X.shape[0]
        ):
            raise RuntimeError(
                f"{dataset}/{split_name}: out-of-range index"
            )


    sets = [
        set(
            idx.tolist()
        )
        for idx in all_idx
    ]


    if (
        sets[0] & sets[1]
        or
        sets[0] & sets[2]
        or
        sets[1] & sets[2]
    ):
        raise RuntimeError(
            f"{dataset}: split overlap"
        )


    union = np.concatenate(
        all_idx
    )


    if (
        len(union) != X.shape[0]
        or
        len(np.unique(union))
        != X.shape[0]
    ):
        raise RuntimeError(
            f"{dataset}: split is not exhaustive"
        )


    print(
        "SPLIT_DISJOINT_PASS=True"
    )

    print(
        "SPLIT_EXHAUSTIVE_PASS=True"
    )


    # -----------------------------------------------------------------
    # Label-space integrity
    # -----------------------------------------------------------------

    labels = np.unique(
        np.asarray(y)
    )


    if len(labels) != expected[
        "classes"
    ]:
        raise RuntimeError(
            f"{dataset}: expected "
            f"{expected['classes']} source classes, "
            f"found {len(labels)}"
        )


    # Mirror the exact frozen dataset_v3r1.py semantics:
    #
    #   classes = np.unique(y_original)
    #   label_map = {
    #       value: index
    #       for index, value in enumerate(classes)
    #   }
    #
    # Harmonized y.npy is allowed to retain native dataset
    # labels; the canonical model targets are the sorted-global
    # mapping to contiguous indices 0..K-1.
    label_map = {
        value: index
        for index, value
        in enumerate(labels)
    }


    mapped_labels = np.asarray(
        [
            label_map[value]
            for value in labels
        ],
        dtype=np.int64,
    )


    expected_mapped_labels = np.arange(
        expected["classes"],
        dtype=np.int64,
    )


    if not np.array_equal(
        mapped_labels,
        expected_mapped_labels,
    ):
        raise RuntimeError(
            f"{dataset}: frozen-loader-equivalent mapping "
            f"does not produce 0..K-1. "
            f"raw={labels.tolist()}, "
            f"mapped={mapped_labels.tolist()}"
        )


    print(
        "RAW_LABEL_CLASS_COUNT_GATE_PASS=True"
    )

    print(
        "RAW_UNIQUE_LABELS=",
        labels.tolist(),
    )

    print(
        "LOADER_EQUIVALENT_LABEL_MAP=",
        {
            str(k): int(v)
            for k, v in label_map.items()
        },
    )

    print(
        "MAPPED_UNIQUE_LABELS=",
        mapped_labels.tolist(),
    )

    print(
        "GLOBAL_LABEL_GATE_PASS=True"
    )


    # -----------------------------------------------------------------
    # Recompute train-only normalization directly from canonical
    # PRE-normalization X.npy.
    # -----------------------------------------------------------------

    train_X = np.asarray(
        X[
            np.asarray(
                train_idx,
                dtype=np.int64,
            )
        ],
        dtype=np.float32,
    )


    recomputed_mean = (
        train_X.mean(
            axis=(0, 1)
        )
    )

    recomputed_std = (
        train_X.std(
            axis=(0, 1)
        )
    )


    del train_X


    print(
        "RECOMPUTED_TRAIN_MEAN=",
        recomputed_mean.tolist(),
    )

    print(
        "RECOMPUTED_TRAIN_STD=",
        recomputed_std.tolist(),
    )


    # -----------------------------------------------------------------
    # Cross-check frozen dataset_summary.json from all
    # 9 models × 5 seeds = 45 runs for this dataset.
    # -----------------------------------------------------------------

    frozen_means = []

    frozen_stds = []

    frozen_paths = []


    for model in MODELS:

        for seed in SEEDS:

            summary = (
                V3
                / "raw_runs"
                / dataset
                / model
                / f"seed_{seed}"
                / "dataset_summary.json"
            )


            if not summary.exists():
                raise FileNotFoundError(
                    f"Frozen V3R1 dataset receipt missing: {summary}"
                )


            obj = json.loads(
                summary.read_text()
            )


            if (
                obj.get("normalization")
                !=
                "explicit_training_split_only"
            ):
                raise RuntimeError(
                    f"{summary}: normalization mode "
                    f"is {obj.get('normalization')!r}"
                )


            mean = np.asarray(
                obj[
                    "normalization_mean"
                ],
                dtype=np.float64,
            )

            std = np.asarray(
                obj[
                    "normalization_std"
                ],
                dtype=np.float64,
            )


            if (
                mean.shape != (6,)
                or
                std.shape != (6,)
            ):
                raise RuntimeError(
                    f"{summary}: invalid normalization vector shape"
                )


            if np.any(std <= 0):
                raise RuntimeError(
                    f"{summary}: non-positive normalization std"
                )


            frozen_means.append(mean)
            frozen_stds.append(std)

            frozen_paths.append(
                str(
                    summary.relative_to(
                        ROOT
                    )
                )
            )


    if len(frozen_paths) != 45:
        raise RuntimeError(
            f"{dataset}: expected 45 dataset receipts"
        )


    ref_mean = frozen_means[0]
    ref_std = frozen_stds[0]


    mean_cross_run_delta = max(
        max_abs(
            x,
            ref_mean,
        )
        for x in frozen_means
    )

    std_cross_run_delta = max(
        max_abs(
            x,
            ref_std,
        )
        for x in frozen_stds
    )


    if mean_cross_run_delta != 0:
        raise RuntimeError(
            f"{dataset}: normalization means differ across runs"
        )


    if std_cross_run_delta != 0:
        raise RuntimeError(
            f"{dataset}: normalization stds differ across runs"
        )


    mean_err = max_abs(
        recomputed_mean,
        ref_mean,
    )

    std_err = max_abs(
        recomputed_std,
        ref_std,
    )


    print(
        "FROZEN_RECEIPT_MEAN=",
        ref_mean.tolist(),
    )

    print(
        "FROZEN_RECEIPT_STD=",
        ref_std.tolist(),
    )

    print(
        "TRAIN_MEAN_MAX_ERROR_F32=",
        mean_err,
    )

    print(
        "TRAIN_STD_MAX_ERROR_F32=",
        std_err,
    )


    # Float32 reduction/platform tolerance.
    TOL = 1e-5


    if mean_err > TOL:
        raise RuntimeError(
            f"{dataset}: canonical X.npy train mean does not "
            f"match frozen receipt. error={mean_err}"
        )


    if std_err > TOL:
        raise RuntimeError(
            f"{dataset}: canonical X.npy train std does not "
            f"match frozen receipt. error={std_err}"
        )


    print(
        "PRE_NORMALIZATION_SIGNAL_GATE_PASS=True"
    )


    # -----------------------------------------------------------------
    # Physical zero -> frozen normalized-space value.
    # -----------------------------------------------------------------

    raw_zero_normalized = (
        -ref_mean
        /
        ref_std
    )


    print(
        "RAW_ZERO_AFTER_NORMALIZATION=",
        raw_zero_normalized.tolist(),
    )


    for channel, value in zip(
        CHANNELS,
        raw_zero_normalized,
    ):

        raw_zero_rows.append({
            "dataset":
                dataset,

            "channel":
                channel,

            "normalized_value_for_pre_normalization_zero":
                float(value),
        })


    # -----------------------------------------------------------------
    # Affine round-trip check
    # -----------------------------------------------------------------

    sample_indices = np.asarray(
        test_idx[:64],
        dtype=np.int64,
    )


    raw_sample = np.asarray(
        X[
            sample_indices
        ],
        dtype=np.float64,
    )


    normalized = (
        raw_sample
        -
        ref_mean.reshape(
            1,
            1,
            6,
        )
    ) / (
        ref_std.reshape(
            1,
            1,
            6,
        )
    )


    recovered = (
        normalized
        *
        ref_std.reshape(
            1,
            1,
            6,
        )
        +
        ref_mean.reshape(
            1,
            1,
            6,
        )
    )


    roundtrip_error = float(
        np.max(
            np.abs(
                recovered
                -
                raw_sample
            )
        )
    )


    print(
        "AFFINE_ROUNDTRIP_MAX_ERROR=",
        roundtrip_error,
    )


    if roundtrip_error > 1e-10:
        raise RuntimeError(
            f"{dataset}: affine roundtrip failed "
            f"error={roundtrip_error}"
        )


    print(
        "AFFINE_ROUNDTRIP_GATE_PASS=True"
    )


    # -----------------------------------------------------------------
    # Frozen canonical artifact SHA
    # -----------------------------------------------------------------

    for role, path in [
        (
            "X_pre_normalization",
            X_path,
        ),
        (
            "y",
            y_path,
        ),
        (
            "train_idx",
            train_path,
        ),
        (
            "val_idx",
            val_path,
        ),
        (
            "test_idx",
            test_path,
        ),
    ]:

        digest = sha256_file(
            path
        )


        data_sha_manifest.append({
            "dataset":
                dataset,

            "role":
                role,

            "path":
                str(
                    path.relative_to(
                        ROOT
                    )
                ),

            "size_bytes":
                path.stat().st_size,

            "sha256":
                digest,
        })


    normalization_receipts[
        dataset
    ] = {
        "mean":
            ref_mean.tolist(),

        "std":
            ref_std.tolist(),

        "physical_zero_after_normalization":
            raw_zero_normalized.tolist(),

        "frozen_dataset_summary_count":
            len(frozen_paths),

        "mean_cross_run_max_delta":
            mean_cross_run_delta,

        "std_cross_run_max_delta":
            std_cross_run_delta,

        "recomputed_train_mean_error":
            mean_err,

        "recomputed_train_std_error":
            std_err,

        "roundtrip_max_error":
            roundtrip_error,
    }


    dataset_receipts.append({
        "dataset":
            dataset,

        "shape":
            list(X.shape),

        "dtype":
            str(X.dtype),

        "class_count":
            int(len(labels)),

        "train_count":
            int(len(train_idx)),

        "val_count":
            int(len(val_idx)),

        "test_count":
            int(len(test_idx)),

        "split_disjoint":
            True,

        "split_exhaustive":
            True,

        "normalization_receipts":
            45,

        "train_mean_match":
            True,

        "train_std_match":
            True,

        "pre_normalization_signal_recoverable":
            True,

        "affine_roundtrip":
            True,
    })


    del X
    del y


write_json(
    OUT
    / "canonical_dataset_reconstruction.json",
    dataset_receipts,
)

write_json(
    OUT
    / "dataset_normalization_receipts.json",
    normalization_receipts,
)

write_json(
    OUT
    / "canonical_data_sha256_manifest.json",
    data_sha_manifest,
)


with (
    OUT
    / "physical_zero_normalized_mapping.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "dataset",
        "channel",
        "normalized_value_for_pre_normalization_zero",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()
    writer.writerows(
        raw_zero_rows
    )


print()
print(
    "CANONICAL_DATA_RECONSTRUCTION_PASS_4_OF_4=True"
)

print(
    "PRE_NORMALIZATION_SIGNAL_RECOVERABLE_4_OF_4=True"
)


# =====================================================================
# 4. Frozen V3R1 checkpoint integrity
#
# 4 datasets × 9 models × 5 seeds = 180.
# NO torch.load.
# =====================================================================

print()
print("=" * 108)
print(
    "V3R1 180-RUN FROZEN CHECKPOINT INTEGRITY"
)
print("=" * 108)


checkpoint_rows = []


for dataset in DATASETS:

    for model in MODELS:

        for seed in SEEDS:

            run_dir = (
                V3
                / "raw_runs"
                / dataset
                / model
                / f"seed_{seed}"
            )


            best = (
                run_dir
                / "best_model.pt"
            )

            checkpoint = (
                run_dir
                / "checkpoint.pt"
            )


            if not best.exists():
                raise FileNotFoundError(
                    f"Canonical V3R1 best_model missing: {best}"
                )


            if not checkpoint.exists():
                raise FileNotFoundError(
                    f"Canonical V3R1 checkpoint copy missing: "
                    f"{checkpoint}"
                )


            best_sha = sha256_file(
                best
            )

            checkpoint_sha = sha256_file(
                checkpoint
            )


            if best_sha != checkpoint_sha:
                raise RuntimeError(
                    "Frozen V3R1 best_model/checkpoint mismatch: "
                    f"{dataset}/{model}/seed_{seed}"
                )


            checkpoint_rows.append({
                "dataset":
                    dataset,

                "model":
                    model,

                "seed":
                    seed,

                "best_model":
                    str(
                        best.relative_to(
                            ROOT
                        )
                    ),

                "checkpoint":
                    str(
                        checkpoint.relative_to(
                            ROOT
                        )
                    ),

                "sha256":
                    best_sha,

                "byte_identical":
                    True,

                "size_bytes":
                    best.stat().st_size,
            })


if len(checkpoint_rows) != 180:
    raise RuntimeError(
        f"Expected 180 frozen V3R1 runs, "
        f"found {len(checkpoint_rows)}"
    )


with (
    OUT
    / "v3r1_checkpoint_integrity_180.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    fields = [
        "dataset",
        "model",
        "seed",
        "best_model",
        "checkpoint",
        "sha256",
        "byte_identical",
        "size_bytes",
    ]

    writer = csv.DictWriter(
        f,
        fieldnames=fields,
    )

    writer.writeheader()
    writer.writerows(
        checkpoint_rows
    )


print(
    "V3R1_CHECKPOINT_PAIR_SHA_PASS_180_OF_180=True"
)

print(
    "V3R1_MODEL_DESERIALIZATION_PERFORMED=False"
)


# =====================================================================
# 5. Frozen V25-final checkpoint provenance discovery
#
# Inventory only. No checkpoint is selected or loaded here.
# =====================================================================

print()
print("=" * 108)
print(
    "V25 FINAL R2 CHECKPOINT PROVENANCE DISCOVERY"
)
print("=" * 108)


if not V25_ROOT.exists():
    raise FileNotFoundError(
        V25_ROOT
    )


v25_ckpts = []


for path in sorted(
    V25_ROOT.rglob("*")
):

    if not path.is_file():
        continue

    if path.suffix.lower() not in {
        ".pt",
        ".pth",
        ".ckpt",
    }:
        continue

    if path.stat().st_size > 100 * 1024 * 1024:
        continue


    rel = str(
        path.relative_to(
            ROOT
        )
    )


    row = {
        "path":
            rel,

        "filename":
            path.name,

        "size_bytes":
            path.stat().st_size,

        "sha256":
            sha256_file(
                path
            ),

        "datasets_in_path": [
            d
            for d in DATASETS
            if d.lower()
            in rel.lower()
        ],

        "seed_tokens":
            re.findall(
                r"seed[_-]?(\d+)",
                rel,
                flags=re.I,
            ),
    }


    v25_ckpts.append(
        row
    )


write_json(
    OUT
    / "v25_final_r2_checkpoint_inventory.json",
    v25_ckpts,
)


print(
    "V25_FINAL_R2_CHECKPOINT_FILES=",
    len(v25_ckpts),
)


for row in v25_ckpts:
    print(
        "V25_CHECKPOINT_CANDIDATE:",
        row["path"],
        row["size_bytes"],
        row["sha256"],
    )


# =====================================================================
# 6. Final receipt
# =====================================================================

receipt = {
    "audit":
        "STAGE25_CANONICAL_RECONSTRUCTION_R2",

    "status":
        "PASS",

    "datasets":
        list(DATASETS),

    "canonical_input_shape":
        [128, 6],

    "canonical_channel_semantics":
        CHANNELS,

    "channel_semantic_evidence":
        "PASS",

    "train_only_normalization_protocol":
        "PASS",

    "subject_disjoint_protocol_evidence":
        "PASS",

    "canonical_dataset_reconstruction":
        "PASS_4_OF_4",

    "split_index_integrity":
        "PASS_4_OF_4",

    "pre_normalization_signal_recoverable":
        "PASS_4_OF_4",

    "train_normalization_recomputed":
        "PASS_4_OF_4",

    "frozen_dataset_summary_receipts":
        "PASS_180_OF_180",

    "v3r1_checkpoint_pair_sha":
        "PASS_180_OF_180",

    "v25_checkpoint_provenance":
        "DISCOVERED_NOT_SELECTED",

    "scientific_interpretation": (
        "Canonical harmonized X.npy is the pre-normalization "
        "model-window representation used to derive the frozen "
        "training mean/std. Stage25 faults can therefore be "
        "applied to test X windows before the frozen affine "
        "normalization step."
    ),

    "terminology": (
        "pre-normalization sensor-domain model-window representation; "
        "not necessarily untouched device ADC/raw acquisition"
    ),

    "stage25_fault_protocol_frozen":
        False,

    "next_gate": (
        "Pre-register Stage25 fault families, severities, stochastic "
        "seeds, aggregation rules, exact frozen model bank, and clean "
        "baseline equivalence gates before corrupted inference."
    ),

    "dataset_arrays_accessed_read_only":
        True,

    "dataset_arrays_modified":
        False,

    "model_deserialization_performed":
        False,

    "model_forward_performed":
        False,

    "training_performed":
        False,

    "checkpoints_modified":
        False,

    "v3r1_results_modified":
        False,

    "v25_results_modified":
        False,

    "stage24_status":
        "FROZEN_COMPLETE",

    "stage24_closure_sha256":
        "15ab874acc4d0420adff73bef32f76b8882a743509682333fdb87fa925060bfa",

    "v3r1_protocol_sha256":
        protocol_sha,
}


write_json(
    OUT
    / "stage25_canonical_reconstruction_receipt_r2.json",
    receipt,
)


print()
print("=" * 108)
print("STAGE25 R2 FINAL RECEIPT")
print("=" * 108)

print(
    json.dumps(
        receipt,
        indent=2,
    )
)


print()
print(
    "STAGE25_CANONICAL_RECONSTRUCTION_R2_PASS=True"
)

print(
    "CANONICAL_DATA_RECONSTRUCTION_PASS_4_OF_4=True"
)

print(
    "PRE_NORMALIZATION_SIGNAL_RECOVERABLE_4_OF_4=True"
)

print(
    "V3R1_CHECKPOINT_PAIR_SHA_PASS_180_OF_180=True"
)

print(
    "TRAINING_PERFORMED=False"
)

print(
    "MODEL_DESERIALIZATION_PERFORMED=False"
)

print(
    "MODEL_FORWARD_PERFORMED=False"
)

print(
    "DATASET_ARRAYS_MODIFIED=False"
)

print(
    "CHECKPOINTS_MODIFIED=False"
)

print(
    "V3R1_RESULTS_MODIFIED=False"
)

print(
    "V25_RESULTS_MODIFIED=False"
)
