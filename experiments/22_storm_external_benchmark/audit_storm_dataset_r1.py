from pathlib import Path
import hashlib
import json

import numpy as np


REPO = Path.cwd()

ROOT = (
    REPO /
    "results" /
    "storm_external_r1"
)

DATA = (
    ROOT /
    "data" /
    "unified"
)

PROTO = (
    ROOT /
    "protocol" /
    "storm_external_protocol_r1.json"
)

OUT = (
    ROOT /
    "dataset_audit"
)

OUT.mkdir(
    parents=True,
    exist_ok=True
)


EXPECTED_LABELS = [
    "walking",
    "running",
    "upstairs",
    "downstairs",
    "sitting",
    "standing",
    "lying",
    "other",
]


EXPECTED_COUNTS = np.array(
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

    with Path(path).open(
        "rb"
    ) as f:

        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b""
        ):

            h.update(
                block
            )

    return h.hexdigest()


def fail(message):

    raise RuntimeError(
        message
    )


if not PROTO.exists():

    fail(
        f"Missing frozen protocol: {PROTO}"
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
        f"Missing metadata: {meta_path}"
    )


meta = json.loads(
    meta_path.read_text()
)


if meta.get(
    "labels"
) != EXPECTED_LABELS:

    fail(
        "Label-space mismatch: "
        f"{meta.get('labels')}"
    )


if meta.get(
    "unified_label_space"
) != EXPECTED_LABELS:

    fail(
        "Unified label-space mismatch"
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
        "Sampling rate mismatch"
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
        "Window length mismatch"
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
        "Window stride mismatch"
    )


if int(
    meta.get(
        "T"
    )
) != 64:

    fail(
        "T mismatch"
    )


if int(
    meta.get(
        "C"
    )
) != 6:

    fail(
        "Channel count mismatch"
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
        "Normalization was not fit on train only"
    )


if (
    meta.get(
        "split_strategy"
    )
    !=
    "stratified_by_source"
):

    fail(
        "Split strategy mismatch: "
        f"{meta.get('split_strategy')}"
    )


splits = {}

subject_sets = {}

all_y = []

all_subjects = []

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


    X = d["X"]

    y = d["y"].astype(
        np.int64
    )

    subj = d["subj"].astype(
        np.int64
    )


    if X.ndim != 3:

        fail(
            f"{split}: X rank mismatch"
        )


    if X.shape[1:] != (
        64,
        6
    ):

        fail(
            f"{split}: X shape mismatch "
            f"{X.shape}"
        )


    if (
        len(X)
        !=
        len(y)
        or
        len(y)
        !=
        len(subj)
    ):

        fail(
            f"{split}: N mismatch"
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
            f"{split}: label range invalid"
        )


    sources = (
        subj //
        1000
    )


    source_ids = set(
        np.unique(
            sources
        ).tolist()
    )


    if source_ids != {
        1,
        2,
        3
    }:

        fail(
            f"{split}: missing source(s): "
            f"{source_ids}"
        )


    source_subject_counts = {}


    for source_id in [
        1,
        2,
        3
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
            f"{split}: source/subject split "
            "does not match 70/15/15 "
            "source-stratified protocol. "
            f"actual={source_subject_counts}, "
            "expected="
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
                in
                source_subject_counts.items()
            },

        "class_counts":
            {
                EXPECTED_LABELS[i]:
                    int(
                        counts[i]
                    )
                for i in range(8)
            },
    }


    splits[
        split
    ] = {
        "X":
            X,

        "y":
            y,

        "subj":
            subj,
    }


    subject_sets[
        split
    ] = set(
        subj.tolist()
    )


    all_y.append(
        y
    )

    all_subjects.append(
        subj
    )


if (
    subject_sets[
        "train"
    ]
    &
    subject_sets[
        "val"
    ]
):

    fail(
        "Train/val subject overlap"
    )


if (
    subject_sets[
        "train"
    ]
    &
    subject_sets[
        "test"
    ]
):

    fail(
        "Train/test subject overlap"
    )


if (
    subject_sets[
        "val"
    ]
    &
    subject_sets[
        "test"
    ]
):

    fail(
        "Val/test subject overlap"
    )


combined_y = np.concatenate(
    all_y
)


combined_subj = np.concatenate(
    all_subjects
)


counts = np.bincount(
    combined_y,
    minlength=8
)


print(
    "PUBLISHED_TABLE2_EXPECTED=",
    EXPECTED_COUNTS.tolist()
)

print(
    "REPRODUCED_GLOBAL_COUNTS=",
    counts.tolist()
)


if not np.array_equal(
    counts,
    EXPECTED_COUNTS
):

    diff = (
        counts
        -
        EXPECTED_COUNTS
    )

    fail(
        "STORM Table-2 global class "
        "distribution was NOT reproduced. "
        f"delta={diff.tolist()}. "
        "DO NOT TRAIN."
    )


source_subject_counts_total = {}


sources = (
    combined_subj //
    1000
)


for source_id in [
    1,
    2,
    3
]:

    source_subject_counts_total[
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
    source_subject_counts_total
    !=
    EXPECTED_SOURCE_SUBJECTS
):

    fail(
        "Source subject totals mismatch: "
        f"{source_subject_counts_total}"
    )


train_X = (
    splits[
        "train"
    ][
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


max_abs_train_mean = float(
    np.max(
        np.abs(
            train_mean
        )
    )
)


max_abs_train_std_error = float(
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
    max_abs_train_mean
)

print(
    "TRAIN_NORMALIZED_MAX_ABS_STD_ERROR=",
    max_abs_train_std_error
)


if max_abs_train_mean > 1e-4:

    fail(
        "Train mean normalization check failed"
    )


if max_abs_train_std_error > 1e-4:

    fail(
        "Train std normalization check failed"
    )


print()
print(
    "SPLIT SUMMARY"
)


for split in [
    "train",
    "val",
    "test",
]:

    print(
        split,
        json.dumps(
            split_summary[
                split
            ],
            sort_keys=True
        )
    )


split_hashes = {
    f"{split}.npz":
        sha256(
            DATA /
            f"{split}.npz"
        )
    for split
    in [
        "train",
        "val",
        "test",
    ]
}


split_hashes[
    "meta.json"
] = sha256(
    meta_path
)


receipt = {

    "audit":
        "storm_external_dataset_r1",

    "protocol_sha256":
        sha256(
            PROTO
        ),

    "published_table2_exact_match":
        True,

    "published_total_windows":
        int(
            EXPECTED_COUNTS.sum()
        ),

    "reproduced_total_windows":
        int(
            counts.sum()
        ),

    "global_class_counts":
        {
            EXPECTED_LABELS[i]:
                int(
                    counts[i]
                )
            for i
            in range(8)
        },

    "source_subject_counts":
        {
            str(k):
                int(v)
            for k, v
            in
            source_subject_counts_total.items()
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

    "split_and_meta_hashes":
        split_hashes,

    "training_allowed_after_this_receipt":
        True,

    "important_boundary":
        (
            "This receipt validates dataset/protocol "
            "reproduction only. It does not yet "
            "constitute STORM model reproduction or "
            "V25-vs-STORM performance evidence."
        ),
}


receipt_path = (
    OUT /
    "storm_dataset_r1_receipt.json"
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
    "DATASET_RECEIPT=",
    receipt_path
)

print(
    "DATASET_RECEIPT_SHA256=",
    sha256(
        receipt_path
    )
)

print(
    "PUBLISHED_TABLE2_EXACT_MATCH=True"
)

print(
    "SOURCE_SUBJECT_COUNTS_EXACT=True"
)

print(
    "SUBJECT_DISJOINT_SPLITS=True"
)

print(
    "SOURCE_STRATIFIED_SPLITS=True"
)

print(
    "TRAIN_ONLY_NORMALIZATION_PASS=True"
)

print(
    "STORM_EXTERNAL_DATASET_R1_PASS=True"
)
