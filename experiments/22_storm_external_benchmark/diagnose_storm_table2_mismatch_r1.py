from pathlib import Path
import hashlib
import json
import math

import numpy as np
import pandas as pd


REPO = Path.cwd()

ROOT = (
    REPO /
    "results" /
    "storm_external_r1"
)

DATA = (
    ROOT /
    "data"
)

UNIFIED = (
    DATA /
    "unified"
)

PAMAP = (
    DATA /
    "pamap2" /
    "PAMAP2_Dataset" /
    "Protocol"
)

OUT = (
    ROOT /
    "table2_forensics_r1"
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


PUBLISHED = np.array(
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


WIN = 64
STRIDE = 32
FS = 50.0


def sha256(path):

    h = hashlib.sha256()

    with Path(path).open("rb") as f:

        for block in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(block)

    return h.hexdigest()


def map_activity(code):

    mapping = {
        1: 6,   # lying
        2: 4,   # sitting
        3: 5,   # standing
        4: 0,   # walking
        5: 1,   # running
        12: 2,  # upstairs
        13: 3,  # downstairs
    }

    return mapping.get(
        int(code),
        7
    )


print("=" * 96)
print("STORM TABLE-2 REPRODUCTION FORENSICS R1")
print("=" * 96)


meta_path = (
    UNIFIED /
    "meta.json"
)


if not meta_path.exists():

    raise FileNotFoundError(
        meta_path
    )


meta = json.loads(
    meta_path.read_text()
)


dataset_stats = meta[
    "dataset_stats"
]


def dist_array(name):

    dist = (
        dataset_stats[
            name
        ][
            "class_distribution"
        ]
    )

    return np.array(
        [
            int(
                dist.get(
                    label,
                    0
                )
            )
            for label in LABELS
        ],
        dtype=np.int64
    )


uci = dist_array(
    "uci"
)

motionsense = dist_array(
    "motionsense"
)

pamap_released = dist_array(
    "pamap2"
)


print(
    "UCI_COUNTS=",
    uci.tolist()
)

print(
    "MOTIONSENSE_COUNTS=",
    motionsense.tolist()
)

print(
    "PAMAP_RELEASED_COUNTS=",
    pamap_released.tolist()
)


# The paper target for PAMAP2 IF UCI and
# MotionSense are unchanged.
target_pamap_nonother = (
    PUBLISHED[:7]
    -
    uci[:7]
    -
    motionsense[:7]
)


print()
print(
    "TARGET_PAMAP_NONOTHER_IF_UCI_MS_FIXED=",
    target_pamap_nonother.tolist()
)

print(
    "CURRENT_PAMAP_NONOTHER=",
    pamap_released[:7].tolist()
)

print(
    "PAMAP_REQUIRED_REDUCTION=",
    (
        pamap_released[:7]
        -
        target_pamap_nonother
    ).tolist()
)


expected_reduction = np.array(
    [
        6,
        5,
        25,
        18,
        12,
        3,
        11,
    ],
    dtype=np.int64
)


actual_reduction = (
    pamap_released[:7]
    -
    target_pamap_nonother
)


if not np.array_equal(
    actual_reduction,
    expected_reduction
):

    raise RuntimeError(
        "Unexpected decomposition: "
        "the entire non-other Table-2 "
        "difference is not attributable "
        "to PAMAP2 under fixed UCI/MS."
    )


print(
    "PAMAP_CAN_EXPLAIN_ALL_80_NONOTHER_WINDOWS=True"
)


dat_files = sorted(
    PAMAP.glob(
        "subject*.dat"
    )
)


if len(dat_files) != 9:

    raise RuntimeError(
        f"Expected 9 PAMAP subjects, found {len(dat_files)}"
    )


# ----------------------------------------------------------
# Load only timestamps + labels.
# Signal values do not affect class-count/window-purity
# calculations in the released PAMAP loader.
# ----------------------------------------------------------

subjects = []


for dat in dat_files:

    sid = int(
        dat.stem.replace(
            "subject",
            ""
        )
    )

    df = pd.read_csv(
        dat,
        sep=r"\s+",
        header=None,
        engine="python"
    )


    t = (
        df.iloc[:, 0]
        .astype(float)
        .to_numpy()
    )


    act = (
        df.iloc[:, 1]
        .astype(float)
    )


    act_codes = (
        act
        .ffill()
        .bfill()
        .round()
        .astype(int)
        .to_numpy()
    )


    t = (
        t
        -
        t[0]
    )


    if (
        t.size < 10
        or
        t[-1] <= 0
    ):

        raise RuntimeError(
            f"Bad PAMAP subject {sid}"
        )


    subjects.append(
        {
            "sid": sid,
            "t": t,
            "act": act_codes,
            "dur": float(t[-1]),
        }
    )


def make_length(
    dur,
    mode
):

    x = (
        dur *
        FS
    )


    if mode == "round":

        return int(
            round(x)
        )

    if mode == "floor":

        return int(
            math.floor(x)
        )

    if mode == "ceil":

        return int(
            math.ceil(x)
        )

    if mode == "round_plus1":

        return int(
            round(x)
        ) + 1

    if mode == "floor_plus1":

        return int(
            math.floor(x)
        ) + 1


    raise ValueError(
        mode
    )


def make_grid(
    dur,
    T,
    mode
):

    if mode == "linspace_inclusive":

        return np.linspace(
            0.0,
            dur,
            T
        )

    if mode == "linspace_endpoint_false":

        return np.linspace(
            0.0,
            dur,
            T,
            endpoint=False
        )

    if mode == "fixed_step":

        grid = (
            np.arange(
                T,
                dtype=np.float64
            )
            /
            FS
        )

        return np.clip(
            grid,
            0.0,
            dur
        )


    raise ValueError(
        mode
    )


def label_indices(
    t,
    grid,
    mode
):

    if mode == "searchsorted_left":

        idx = np.searchsorted(
            t,
            np.clip(
                grid,
                t[0],
                t[-1]
            ),
            side="left"
        )

        return np.clip(
            idx,
            0,
            len(t) - 1
        )


    if mode == "previous":

        idx = (
            np.searchsorted(
                t,
                np.clip(
                    grid,
                    t[0],
                    t[-1]
                ),
                side="right"
            )
            -
            1
        )

        return np.clip(
            idx,
            0,
            len(t) - 1
        )


    if mode == "nearest":

        right = np.searchsorted(
            t,
            np.clip(
                grid,
                t[0],
                t[-1]
            ),
            side="left"
        )

        right = np.clip(
            right,
            0,
            len(t) - 1
        )

        left = np.clip(
            right - 1,
            0,
            len(t) - 1
        )


        choose_left = (
            np.abs(
                grid
                -
                t[left]
            )
            <=
            np.abs(
                t[right]
                -
                grid
            )
        )


        return np.where(
            choose_left,
            left,
            right
        )


    raise ValueError(
        mode
    )


def generate_windows(
    length_mode,
    grid_mode,
    label_mode,
    endpoint_mode
):

    labels_out = []

    purity_out = []


    for subject in subjects:

        T = make_length(
            subject["dur"],
            length_mode
        )


        if T < WIN:
            continue


        grid = make_grid(
            subject["dur"],
            T,
            grid_mode
        )


        idx = label_indices(
            subject["t"],
            grid,
            label_mode
        )


        y_stream = np.array(
            [
                map_activity(
                    subject["act"][i]
                )
                for i in idx
            ],
            dtype=np.int64
        )


        if endpoint_mode == "inclusive":

            stop = (
                T
                -
                WIN
                +
                1
            )

        elif endpoint_mode == "strict":

            stop = (
                T
                -
                WIN
            )

        else:

            raise ValueError(
                endpoint_mode
            )


        for start in range(
            0,
            max(
                stop,
                0
            ),
            STRIDE
        ):

            segment = (
                y_stream[
                    start:
                    start + WIN
                ]
            )


            if len(segment) != WIN:
                continue


            counts = np.bincount(
                segment,
                minlength=8
            )


            winner = int(
                np.argmax(
                    counts
                )
            )


            purity = float(
                counts[winner]
                /
                WIN
            )


            labels_out.append(
                winner
            )

            purity_out.append(
                purity
            )


    return (
        np.asarray(
            labels_out,
            dtype=np.int64
        ),
        np.asarray(
            purity_out,
            dtype=np.float64
        ),
    )


# ----------------------------------------------------------
# First: verify our forensic implementation exactly
# recreates released PAMAP counts.
# ----------------------------------------------------------

current_y, current_purity = generate_windows(
    "round",
    "linspace_inclusive",
    "searchsorted_left",
    "inclusive",
)


current_counts = np.bincount(
    current_y,
    minlength=8
)


print()
print(
    "FORENSIC_CURRENT_PAMAP_COUNTS=",
    current_counts.tolist()
)

print(
    "RELEASED_PAMAP_COUNTS=",
    pamap_released.tolist()
)


if not np.array_equal(
    current_counts,
    pamap_released
):

    raise RuntimeError(
        "Forensic implementation does not "
        "reproduce released PAMAP loader. "
        "Stop before variant search."
    )


print(
    "FORENSIC_IMPLEMENTATION_IDENTITY_PASS=True"
)


# ----------------------------------------------------------
# Search plausible undocumented preprocessing choices.
#
# Purity values occur in multiples of 1/64.
# Released logic keeps windows when purity >= threshold.
# ----------------------------------------------------------

length_modes = [
    "round",
    "floor",
    "ceil",
    "round_plus1",
    "floor_plus1",
]


grid_modes = [
    "linspace_inclusive",
    "linspace_endpoint_false",
    "fixed_step",
]


label_modes = [
    "searchsorted_left",
    "previous",
    "nearest",
]


endpoint_modes = [
    "inclusive",
    "strict",
]


thresholds = sorted(
    set(
        [0.0]
        +
        [
            k / 64.0
            for k in range(
                1,
                65
            )
        ]
    )
)


rows = []


for length_mode in length_modes:

    for grid_mode in grid_modes:

        for label_mode in label_modes:

            for endpoint_mode in endpoint_modes:

                y, purity = generate_windows(
                    length_mode,
                    grid_mode,
                    label_mode,
                    endpoint_mode,
                )


                for threshold in thresholds:

                    keep = (
                        purity
                        >=
                        threshold
                    )


                    counts = np.bincount(
                        y[keep],
                        minlength=8
                    )


                    delta = (
                        counts[:7]
                        -
                        target_pamap_nonother
                    )


                    l1 = int(
                        np.abs(
                            delta
                        ).sum()
                    )


                    linf = int(
                        np.abs(
                            delta
                        ).max()
                    )


                    exact_nonother = bool(
                        np.array_equal(
                            counts[:7],
                            target_pamap_nonother
                        )
                    )


                    # If non-other exactly matches Table 2,
                    # max_other_ratio=1.0 will cap other to
                    # walking=16096 only if enough raw
                    # "other" remains.
                    cap_compatible = bool(
                        counts[7]
                        >=
                        PUBLISHED[7]
                    )


                    exact_table2_cap_compatible = bool(
                        exact_nonother
                        and
                        cap_compatible
                    )


                    rows.append(
                        {
                            "length_mode":
                                length_mode,

                            "grid_mode":
                                grid_mode,

                            "label_mode":
                                label_mode,

                            "endpoint_mode":
                                endpoint_mode,

                            "min_purity":
                                threshold,

                            "pamap_walking":
                                int(counts[0]),

                            "pamap_running":
                                int(counts[1]),

                            "pamap_upstairs":
                                int(counts[2]),

                            "pamap_downstairs":
                                int(counts[3]),

                            "pamap_sitting":
                                int(counts[4]),

                            "pamap_standing":
                                int(counts[5]),

                            "pamap_lying":
                                int(counts[6]),

                            "pamap_other_raw":
                                int(counts[7]),

                            "nonother_l1_error":
                                l1,

                            "nonother_linf_error":
                                linf,

                            "exact_nonother":
                                exact_nonother,

                            "cap_compatible":
                                cap_compatible,

                            "exact_table2_cap_compatible":
                                exact_table2_cap_compatible,
                        }
                    )


results = pd.DataFrame(
    rows
)


results = results.sort_values(
    [
        "nonother_l1_error",
        "nonother_linf_error",
        "length_mode",
        "grid_mode",
        "label_mode",
        "endpoint_mode",
        "min_purity",
    ]
)


results.to_csv(
    OUT /
    "storm_table2_variant_search.csv",
    index=False
)


top = results.head(
    40
)


top.to_csv(
    OUT /
    "storm_table2_top40.csv",
    index=False
)


exact = results[
    results[
        "exact_table2_cap_compatible"
    ]
].copy()


exact.to_csv(
    OUT /
    "storm_table2_exact_candidates.csv",
    index=False
)


print()
print("=" * 96)
print("TOP 40 CANDIDATES")
print("=" * 96)

print(
    top.to_string(
        index=False
    )
)


print()
print("=" * 96)
print("EXACT TABLE-2 CANDIDATES")
print("=" * 96)


if len(exact):

    print(
        exact.to_string(
            index=False
        )
    )

else:

    print(
        "NONE"
    )


# Special check:
# can the released algorithm itself reproduce
# the paper simply with a non-zero min_purity?
released_algorithm_exact = exact[
    (
        exact[
            "length_mode"
        ]
        ==
        "round"
    )
    &
    (
        exact[
            "grid_mode"
        ]
        ==
        "linspace_inclusive"
    )
    &
    (
        exact[
            "label_mode"
        ]
        ==
        "searchsorted_left"
    )
    &
    (
        exact[
            "endpoint_mode"
        ]
        ==
        "inclusive"
    )
]


min_purity_only_match = bool(
    len(
        released_algorithm_exact
    )
    >
    0
)


print()
print(
    "MIN_PURITY_ONLY_EXACT_MATCH=",
    min_purity_only_match
)


recommended = None


if min_purity_only_match:

    recommended = float(
        released_algorithm_exact.iloc[
            0
        ][
            "min_purity"
        ]
    )


    print(
        "RECOMMENDED_RELEASED_CODE_MIN_PURITY=",
        recommended
    )


print(
    "ANY_EXACT_VARIANT_MATCH=",
    bool(
        len(
            exact
        )
        >
        0
    )
)


# ----------------------------------------------------------
# Archive hashes and environment evidence
# ----------------------------------------------------------

archive_candidates = [
    (
        DATA /
        "uci" /
        "UCI_HAR_Dataset.zip"
    ),
    (
        DATA /
        "pamap2" /
        "PAMAP2_Dataset.zip"
    ),
    (
        DATA /
        "motionsense" /
        "_cache" /
        "motion-sense-master.zip"
    ),
]


archive_hashes = {}


for path in archive_candidates:

    if path.exists():

        archive_hashes[
            str(
                path.relative_to(
                    REPO
                )
            )
        ] = sha256(
            path
        )


receipt = {
    "audit":
        "storm_table2_forensics_r1",

    "published_counts":
        {
            LABELS[i]:
                int(PUBLISHED[i])
            for i in range(8)
        },

    "released_reproduction_counts":
        {
            LABELS[i]:
                int(
                    (
                        uci
                        +
                        motionsense
                        +
                        pamap_released
                    )[i]
                )
            for i in range(8)
        },

    "published_capped_total":
        int(
            PUBLISHED.sum()
        ),

    "released_capped_total":
        87616,

    "difference_windows":
        86,

    "difference_fraction":
        float(
            86
            /
            PUBLISHED.sum()
        ),

    "pamap_can_explain_all_nonother_difference":
        True,

    "forensic_implementation_identity_pass":
        True,

    "min_purity_only_exact_match":
        min_purity_only_match,

    "recommended_released_code_min_purity":
        recommended,

    "any_exact_variant_match":
        bool(
            len(exact)
            >
            0
        ),

    "exact_candidate_count":
        int(
            len(exact)
        ),

    "archive_hashes":
        archive_hashes,

    "training_allowed":
        False,

    "decision":
        (
            "Do not train until the published "
            "Table-2 mismatch is resolved and a "
            "new reproduction revision is frozen."
        ),
}


receipt_path = (
    OUT /
    "storm_table2_forensics_receipt.json"
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
    "FORENSICS_RECEIPT=",
    receipt_path
)

print(
    "FORENSICS_RECEIPT_SHA256=",
    sha256(
        receipt_path
    )
)


print()
print("=" * 96)

print(
    "TRAINING_ALLOWED=False"
)

print(
    "STORM_TABLE2_FORENSICS_R1_PASS=True"
)

print("=" * 96)
