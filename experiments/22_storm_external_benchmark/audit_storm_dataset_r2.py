from pathlib import Path
import hashlib
import json

import numpy as np


REPO = Path.cwd()

ROOT = (
    REPO /
    "results" /
    "storm_external_r2"
)

DATA = (
    ROOT /
    "data" /
    "unified"
)

PROTO = (
    ROOT /
    "protocol" /
    "storm_external_protocol_r2.json"
)

OUT = (
    ROOT /
    "dataset_audit"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)


LABELS = [
    "walking",
    "running",
    "upstairs",
    "downstairs",
    "sitting",
    "standing",
    "lying",
    "other",
]


EXPECTED_GLOBAL_COUNTS = np.array(
    [
        16096,
        5648,
        8164,
        7039,
        15175,
        14371,
        4941,
        16096,
    ],
    dtype=np.int64
)


EXPECTED_TOTAL = 87530


EXPECTED_SOURCE_WINDOWS_PRECAP = {
    "uci": 10299,
    "motionsense": 43612,
    "pamap2": 44720,
}


EXPECTED_UCI_COUNTS = {
    "walking": 1722,
    "running": 0,
    "upstairs": 1544,
    "downstairs": 1406,
    "sitting": 1777,
    "standing": 1906,
    "lying": 1944,
    "other": 0,
}


EXPECTED_MS_COUNTS = {
    "walking": 10651,
    "running": 4122,
    "upstairs": 4809,
    "downstairs": 4011,
    "sitting": 10515,
    "standing": 9504,
    "lying": 0,
    "other": 0,
}


EXPECTED_PAMAP_COUNTS_PRECAP = {
    "walking": 3723,
    "running": 1526,
    "upstairs": 1811,
    "downstairs": 1622,
    "sitting": 2883,
    "standing": 2961,
    "lying": 2997,
    "other": 27197,
}


EXPECTED_SOURCE_SUBJECTS = {
    1: 30,
    2: 24,
    3: 9,
}


EXPECTED_SPLIT_SOURCE_SUBJECTS = {
    "train": {
        1: 21,
        2: 17,
        3: 6,
    },

    "val": {
        1: 4,
        2: 4,
        3: 1,
    },

    "test": {
        1: 5,
        2: 3,
        3: 2,
    },
}


def sha256(path):

    h = hashlib.sha256()

    with Path(path).open("rb") as f:

        for block in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(block)

    return h.hexdigest()


def fail(message):

    raise RuntimeError(
        message
    )


if not PROTO.exists():

    fail(
        f"Missing R2 protocol: {PROTO}"
    )


protocol = json.loads(
    PROTO.read_text()
)


meta_path = (
    DATA /
    "meta.json"
)


if not meta_path.exists():

    fail(
        f"Missing meta.json: {meta_path}"
    )


meta = json.loads(
    meta_path.read_text()
)


# ----------------------------------------------------------
# Protocol-level checks
# ----------------------------------------------------------

if meta.get(
    "labels"
) != LABELS:

    fail(
        f"Label mismatch: {meta.get('labels')}"
    )


if meta.get(
    "unified_label_space"
) != LABELS:

    fail(
        "Unified label space mismatch"
    )


if abs(
    float(
        meta.get(
            "fs_target_Hz"
        )
    )
    -
    50.0
) > 1e-12:

    fail(
        "Sampling-rate mismatch"
    )


if abs(
    float(
        meta.get(
            "win_len_s"
        )
    )
    -
    1.28
) > 1e-12:

    fail(
        "Window-length mismatch"
    )


if abs(
    float(
        meta.get(
            "win_stride_s"
        )
    )
    -
    0.64
) > 1e-12:

    fail(
        "Stride mismatch"
    )


if int(
    meta.get(
        "T"
    )
) != 64:

    fail(
        "Expected T=64"
    )


if int(
    meta.get(
        "C"
    )
) != 6:

    fail(
        "Expected C=6"
    )


if abs(
    float(
        meta.get(
            "min_purity"
        )
    )
    -
    0.8125
) > 1e-15:

    fail(
        "R2 min_purity is not exactly 0.8125"
    )


if abs(
    float(
        meta.get(
            "max_other_ratio"
        )
    )
    -
    1.0
) > 1e-15:

    fail(
        "R2 max_other_ratio is not exactly 1.0"
    )


if (
    meta.get(
        "standardization",
        {}
    ).get(
        "fit_on"
    )
    !=
    "train_split"
):

    fail(
        "Normalization was not fitted on training split"
    )


if (
    meta.get(
        "split_strategy"
    )
    !=
    "stratified_by_source"
):

    fail(
        "Source-stratified split strategy mismatch"
    )


print(
    "MIN_PURITY_EXACT=0.8125"
)

print(
    "MAX_OTHER_RATIO_EXACT=1.0"
)


# ----------------------------------------------------------
# Verify source-level counts before global cap.
# This identifies exactly where R1 -> R2 changed.
# ----------------------------------------------------------

dataset_stats = meta.get(
    "dataset_stats",
    {}
)


for source in [
    "uci",
    "motionsense",
    "pamap2",
]:

    if source not in dataset_stats:

        fail(
            f"Missing source stats: {source}"
        )


source_expected = {
    "uci":
        EXPECTED_UCI_COUNTS,

    "motionsense":
        EXPECTED_MS_COUNTS,

    "pamap2":
        EXPECTED_PAMAP_COUNTS_PRECAP,
}


for source, expected in source_expected.items():

    stats = dataset_stats[
        source
    ]


    actual_n = int(
        stats[
            "N_windows"
        ]
    )


    expected_n = int(
        EXPECTED_SOURCE_WINDOWS_PRECAP[
            source
        ]
    )


    if actual_n != expected_n:

        fail(
            f"{source}: window-count mismatch. "
            f"actual={actual_n}, expected={expected_n}"
        )


    actual_dist = stats[
        "class_distribution"
    ]


    for label in LABELS:

        actual_value = int(
            actual_dist.get(
                label,
                0
            )
        )

        expected_value = int(
            expected[
                label
            ]
        )


        if actual_value != expected_value:

            fail(
                f"{source}/{label}: "
                f"actual={actual_value}, "
                f"expected={expected_value}"
            )


    print(
        "SOURCE_COUNT_PASS:",
        source,
        actual_n
    )


print(
    "UCI_UNCHANGED_FROM_R1=True"
)

print(
    "MOTIONSENSE_UNCHANGED_FROM_R1=True"
)

print(
    "PAMAP_REPRODUCTION_COUNTS_EXACT=True"
)


# ----------------------------------------------------------
# Split files
# ----------------------------------------------------------

subject_sets = {}

all_y = []

all_subj = []

split_summary = {}


for split in [
    "train",
    "val",
    "test",
]:

    path = (
        DATA /
        f"{split}.npz"
    )


    if not path.exists():

        fail(
            f"Missing split: {path}"
        )


    d = np.load(
        path,
        allow_pickle=False
    )


    X = d[
        "X"
    ]

    y = d[
        "y"
    ].astype(
        np.int64
    )

    subj = d[
        "subj"
    ].astype(
        np.int64
    )


    if X.ndim != 3:

        fail(
            f"{split}: X rank mismatch"
        )


    if tuple(
        X.shape[1:]
    ) != (
        64,
        6
    ):

        fail(
            f"{split}: X shape={X.shape}"
        )


    if not (
        len(X)
        ==
        len(y)
        ==
        len(subj)
    ):

        fail(
            f"{split}: sample-count mismatch"
        )


    if not np.isfinite(
        X
    ).all():

        fail(
            f"{split}: NaN/Inf present"
        )


    if (
        y.min() < 0
        or
        y.max() > 7
    ):

        fail(
            f"{split}: label-range mismatch"
        )


    sources = (
        subj //
        1000
    )


    source_subject_counts = {}


    for source_id in [
        1,
        2,
        3,
    ]:

        source_subject_counts[
            source_id
        ] = int(
            np.unique(
                subj[
                    sources
                    ==
                    source_id
                ]
            ).size
        )


    if (
        source_subject_counts
        !=
        EXPECTED_SPLIT_SOURCE_SUBJECTS[
            split
        ]
    ):

        fail(
            f"{split}: source subject allocation "
            f"{source_subject_counts} != "
            f"{EXPECTED_SPLIT_SOURCE_SUBJECTS[split]}"
        )


    counts = np.bincount(
        y,
        minlength=8
    )


    split_summary[
        split
    ] = {
        "windows":
            int(
                len(y)
            ),

        "subjects":
            int(
                np.unique(
                    subj
                ).size
            ),

        "source_subject_counts":
            {
                str(k):
                    int(v)
                for k, v
                in source_subject_counts.items()
            },

        "class_counts":
            {
                LABELS[i]:
                    int(counts[i])
                for i in range(8)
            },
    }


    subject_sets[
        split
    ] = set(
        subj.tolist()
    )


    all_y.append(
        y
    )

    all_subj.append(
        subj
    )


if (
    subject_sets["train"]
    &
    subject_sets["val"]
):

    fail(
        "Train/val subject overlap"
    )


if (
    subject_sets["train"]
    &
    subject_sets["test"]
):

    fail(
        "Train/test subject overlap"
    )


if (
    subject_sets["val"]
    &
    subject_sets["test"]
):

    fail(
        "Val/test subject overlap"
    )


print(
    "SUBJECT_DISJOINT_SPLITS=True"
)

print(
    "SOURCE_STRATIFIED_SPLITS=True"
)


# ----------------------------------------------------------
# Global Table-2 match
# ----------------------------------------------------------

combined_y = np.concatenate(
    all_y
)


combined_subj = np.concatenate(
    all_subj
)


global_counts = np.bincount(
    combined_y,
    minlength=8
)


print()
print(
    "PUBLISHED_TABLE2_EXPECTED=",
    EXPECTED_GLOBAL_COUNTS.tolist()
)

print(
    "REPRODUCED_GLOBAL_COUNTS=",
    global_counts.tolist()
)


if not np.array_equal(
    global_counts,
    EXPECTED_GLOBAL_COUNTS
):

    fail(
        "R2 does not reproduce published Table 2. "
        f"delta="
        f"{(global_counts - EXPECTED_GLOBAL_COUNTS).tolist()}"
    )


if len(
    combined_y
) != EXPECTED_TOTAL:

    fail(
        f"Total windows={len(combined_y)}, "
        f"expected={EXPECTED_TOTAL}"
    )


print(
    "PUBLISHED_TOTAL_WINDOWS_EXACT=87530"
)

print(
    "PUBLISHED_TABLE2_EXACT_MATCH=True"
)


# ----------------------------------------------------------
# Overall source subject counts
# ----------------------------------------------------------

sources = (
    combined_subj //
    1000
)


source_subject_totals = {}


for source_id in [
    1,
    2,
    3,
]:

    source_subject_totals[
        source_id
    ] = int(
        np.unique(
            combined_subj[
                sources
                ==
                source_id
            ]
        ).size
    )


if (
    source_subject_totals
    !=
    EXPECTED_SOURCE_SUBJECTS
):

    fail(
        f"Source subject totals={source_subject_totals}"
    )


print(
    "SOURCE_SUBJECT_COUNTS_EXACT=True"
)


# ----------------------------------------------------------
# Train-only normalization numerical check
# ----------------------------------------------------------

train = np.load(
    DATA /
    "train.npz",
    allow_pickle=False
)


train_X = (
    train[
        "X"
    ]
    .reshape(
        -1,
        6
    )
)


train_mean = train_X.mean(
    axis=0
)


train_std = train_X.std(
    axis=0
)


max_abs_mean = float(
    np.max(
        np.abs(
            train_mean
        )
    )
)


max_std_error = float(
    np.max(
        np.abs(
            train_std
            -
            1.0
        )
    )
)


print(
    "TRAIN_NORMALIZED_MAX_ABS_MEAN=",
    max_abs_mean
)

print(
    "TRAIN_NORMALIZED_MAX_ABS_STD_ERROR=",
    max_std_error
)


if max_abs_mean > 1e-4:

    fail(
        "Train normalization mean check failed"
    )


if max_std_error > 1e-4:

    fail(
        "Train normalization std check failed"
    )


print(
    "TRAIN_ONLY_NORMALIZATION_PASS=True"
)


# ----------------------------------------------------------
# Hash all final data products
# ----------------------------------------------------------

data_hashes = {}


for name in [
    "train.npz",
    "val.npz",
    "test.npz",
    "meta.json",
]:

    path = (
        DATA /
        name
    )

    data_hashes[
        name
    ] = sha256(
        path
    )


receipt = {
    "audit":
        "storm_external_dataset_r2",

    "protocol_sha256":
        sha256(
            PROTO
        ),

    "status":
        "PASS",

    "published_table2_exact_match":
        True,

    "published_total_windows":
        EXPECTED_TOTAL,

    "reproduced_total_windows":
        int(
            len(
                combined_y
            )
        ),

    "reproduction_derived_parameter":
        {
            "min_purity":
                0.8125,

            "fractional_interpretation":
                "52/64",

            "documentation_status":
                (
                    "Derived by exhaustive forensic "
                    "reproduction against published "
                    "Table-2 counts; not claimed as "
                    "explicitly documented in the paper."
                ),
        },

    "released_code_changes":
        None,

    "released_code_modified":
        False,

    "cli_only_change_from_r1":
        (
            "--min-purity 0.8125"
        ),

    "max_other_ratio":
        1.0,

    "global_class_counts":
        {
            LABELS[i]:
                int(global_counts[i])
            for i in range(8)
        },

    "source_subject_counts":
        {
            str(k):
                int(v)
            for k, v
            in source_subject_totals.items()
        },

    "split_summary":
        split_summary,

    "subject_disjoint":
        True,

    "source_stratified":
        True,

    "train_only_normalization":
        True,

    "shape":
        [
            64,
            6,
        ],

    "data_hashes":
        data_hashes,

    "training_allowed_after_this_receipt":
        True,

    "claim_boundary":
        (
            "The dataset matches the published "
            "global Table-2 class distribution exactly. "
            "The min_purity=0.8125 value is a "
            "reproduction-derived parameter and must "
            "be reported transparently."
        ),
}


receipt_path = (
    OUT /
    "storm_dataset_r2_receipt.json"
)


receipt_path.write_text(
    json.dumps(
        receipt,
        indent=2,
        sort_keys=True
    )
)


print()
print(
    "R2_DATASET_RECEIPT=",
    receipt_path
)

print(
    "R2_DATASET_RECEIPT_SHA256=",
    sha256(
        receipt_path
    )
)


print()
print("=" * 96)

print(
    "RELEASED_STORM_CODE_MODIFIED=False"
)

print(
    "REPRODUCTION_DERIVED_MIN_PURITY=0.8125"
)

print(
    "TRAINING_ALLOWED_AFTER_R2=True"
)

print(
    "STORM_EXTERNAL_DATASET_R2_PASS=True"
)

print("=" * 96)
