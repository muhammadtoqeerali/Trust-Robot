from __future__ import annotations

from collections import Counter
from pathlib import Path
import json

import numpy as np


ROOT = Path.home() / "toqeer" / "IMU_Reliability"

COMBINED = Path(
    "/mnt/hdd16T/protechto/data/back/"
    "UniVrFall_KFall/segments/"
    "400ms_50ov_npseg_filt_binary"
)

HISTORICAL_UNIVR = Path(
    "/mnt/hdd16T/protechto/data/back/"
    "UniVrFall/segments/"
    "400ms_50ov_npseg_filt_binary"
)

CURRENT_UNIVR = Path(
    "/mnt/hdd16T/protechto/data/"
    "UniVrFall_oriented/segments/"
    "400ms_50ov_npseg_filt_binary"
)

CURRENT_KFALL = Path(
    "/mnt/hdd16T/protechto/data/"
    "KFall_oriented/segments/"
    "400ms_50ov_npseg_filt_binary"
)

CURRENT_ONFIELD = Path(
    "/mnt/hdd16T/protechto/data/"
    "OnField/segments/"
    "400ms_50ov_npseg_filt_binary"
)

OUTPUT = (
    ROOT
    / "data/provenance/"
      "full_signal_lineage_audit_v1.json"
)


SIGN_MAPS = {
    "UNIVRFALL": np.asarray(
        [-1, +1, -1, -1, +1, -1],
        dtype=np.float64,
    ),

    "ONFIELD": np.asarray(
        [-1, +1, -1, -1, +1, -1],
        dtype=np.float64,
    ),

    "KFALL": np.asarray(
        [-1, -1, -1, -1, +1, -1],
        dtype=np.float64,
    ),
}


CURRENT_ROOTS = {
    "UNIVRFALL": CURRENT_UNIVR,
    "ONFIELD": CURRENT_ONFIELD,
    "KFALL": CURRENT_KFALL,
}


# Descriptive bins only. These are NOT detector thresholds.
ABS_ERROR_BIN_EDGES = [
    0.0,
    1e-12,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    1.1,
    1.5,
    2.0,
    5.0,
    10.0,
    float("inf"),
]


def load_array(path: Path):
    return np.load(
        path,
        mmap_mode="r",
        allow_pickle=False,
    )


def exact_array_equal(
    left_path: Path,
    right_path: Path,
    *,
    chunk_rows: int = 4096,
) -> tuple[bool, str]:

    if not left_path.is_file():
        return False, "left_missing"

    if not right_path.is_file():
        return False, "right_missing"

    a = load_array(left_path)
    b = load_array(right_path)

    if a.shape != b.shape:
        return False, "shape_mismatch"

    if a.dtype != b.dtype:
        return False, "dtype_mismatch"

    if a.size == 0:
        return True, "exact_empty"

    n = int(a.shape[0])

    for start in range(
        0,
        n,
        chunk_rows,
    ):
        stop = min(
            start + chunk_rows,
            n,
        )

        if not np.array_equal(
            a[start:stop],
            b[start:stop],
        ):
            return False, "value_mismatch"

    return True, "exact"


def identify_dataset(
    rel: Path,
) -> str:

    historical = (
        HISTORICAL_UNIVR / rel
    )

    current_onfield = (
        CURRENT_ONFIELD / rel
    )

    current_univr = (
        CURRENT_UNIVR / rel
    )

    current_kfall = (
        CURRENT_KFALL / rel
    )

    if current_onfield.is_dir():
        if not historical.is_dir():
            raise RuntimeError(
                "OnField trial lacks historical source: "
                f"{rel}"
            )
        return "ONFIELD"

    if current_univr.is_dir():
        if not historical.is_dir():
            raise RuntimeError(
                "UniVR trial lacks historical source: "
                f"{rel}"
            )
        return "UNIVRFALL"

    if current_kfall.is_dir():
        return "KFALL"

    raise RuntimeError(
        "Unable to identify source dataset for "
        f"{rel}"
    )


def compare_task6_transform(
    historical_path: Path,
    current_path: Path,
    signs: np.ndarray,
    *,
    chunk_windows: int = 2048,
) -> dict:

    a = load_array(
        historical_path
    )

    b = load_array(
        current_path
    )

    result = {
        "shape_equal":
            bool(
                a.shape == b.shape
            ),

        "historical_shape":
            list(
                a.shape
            ),

        "current_shape":
            list(
                b.shape
            ),

        "empty":
            bool(
                a.size == 0
                and b.size == 0
            ),

        "finite":
            True,

        "value_count":
            0,

        "exact_count":
            0,

        "absolute_error_sum":
            0.0,

        "absolute_error_max":
            0.0,

        "bin_counts":
            [
                0
                for _ in range(
                    len(
                        ABS_ERROR_BIN_EDGES
                    )
                    - 1
                )
            ],
    }


    if a.shape != b.shape:
        return result


    if a.size == 0:
        return result


    if (
        a.ndim != 3
        or b.ndim != 3
        or a.shape[2] < 6
        or b.shape[2] < 6
    ):
        raise RuntimeError(
            "Unexpected non-empty segment shape: "
            f"{historical_path}: {a.shape}, "
            f"{current_path}: {b.shape}"
        )


    n_windows = int(
        a.shape[0]
    )


    for start in range(
        0,
        n_windows,
        chunk_windows,
    ):

        stop = min(
            start + chunk_windows,
            n_windows,
        )

        historical = np.asarray(
            a[
                start:stop,
                :,
                :6,
            ],
            dtype=np.float64,
        )

        current = np.asarray(
            b[
                start:stop,
                :,
                :6,
            ],
            dtype=np.float64,
        )

        reconstruction = (
            current
            * signs.reshape(
                1,
                1,
                6,
            )
        )

        diff = (
            historical
            - reconstruction
        )

        abs_diff = np.abs(
            diff
        )

        finite = np.isfinite(
            abs_diff
        )

        if not bool(
            np.all(finite)
        ):
            result[
                "finite"
            ] = False

            raise RuntimeError(
                "Non-finite transformed residual at "
                f"{historical_path}"
            )


        result[
            "value_count"
        ] += int(
            abs_diff.size
        )

        result[
            "exact_count"
        ] += int(
            np.count_nonzero(
                diff == 0
            )
        )

        result[
            "absolute_error_sum"
        ] += float(
            np.sum(
                abs_diff,
                dtype=np.float64,
            )
        )

        result[
            "absolute_error_max"
        ] = max(
            result[
                "absolute_error_max"
            ],
            float(
                np.max(
                    abs_diff
                )
            ),
        )


        hist, _ = np.histogram(
            abs_diff,
            bins=np.asarray(
                ABS_ERROR_BIN_EDGES,
                dtype=np.float64,
            ),
        )

        for i, value in enumerate(
            hist.tolist()
        ):
            result[
                "bin_counts"
            ][i] += int(
                value
            )


    return result


def add_transform_result(
    aggregate: dict,
    trial_result: dict,
) -> None:

    aggregate[
        "trial_count"
    ] += 1

    if trial_result[
        "empty"
    ]:
        aggregate[
            "empty_trial_count"
        ] += 1

    if not trial_result[
        "shape_equal"
    ]:
        aggregate[
            "shape_mismatch_count"
        ] += 1

    aggregate[
        "value_count"
    ] += trial_result[
        "value_count"
    ]

    aggregate[
        "exact_count"
    ] += trial_result[
        "exact_count"
    ]

    aggregate[
        "absolute_error_sum"
    ] += trial_result[
        "absolute_error_sum"
    ]

    aggregate[
        "absolute_error_max"
    ] = max(
        aggregate[
            "absolute_error_max"
        ],
        trial_result[
            "absolute_error_max"
        ],
    )

    for i, value in enumerate(
        trial_result[
            "bin_counts"
        ]
    ):
        aggregate[
            "bin_counts"
        ][i] += value


def new_aggregate() -> dict:

    return {
        "trial_count": 0,
        "empty_trial_count": 0,
        "shape_mismatch_count": 0,
        "label_mismatch_count": 0,

        "historical_back_exact_trial_count": 0,
        "historical_back_mismatch_trial_count": 0,

        "value_count": 0,
        "exact_count": 0,

        "absolute_error_sum": 0.0,
        "absolute_error_max": 0.0,

        "bin_counts": [
            0
            for _ in range(
                len(
                    ABS_ERROR_BIN_EDGES
                )
                - 1
            )
        ],
    }


def main() -> None:

    trial_dirs = sorted(
        {
            p.parent
            for p in COMBINED.rglob(
                "segments.npy"
            )
            if (
                p.parent
                / "labels.npy"
            ).is_file()
        }
    )


    print(
        "combined_trial_dirs =",
        len(
            trial_dirs
        ),
        flush=True,
    )


    aggregates = {
        dataset:
            new_aggregate()
        for dataset in (
            "UNIVRFALL",
            "ONFIELD",
            "KFALL",
        )
    }


    dataset_counts = Counter()

    transform_outliers = []

    historical_back_mismatches = []

    label_mismatches = []


    for index, combined_dir in enumerate(
        trial_dirs,
        start=1,
    ):

        rel = combined_dir.relative_to(
            COMBINED
        )

        dataset = identify_dataset(
            rel
        )

        dataset_counts[
            dataset
        ] += 1


        current_dir = (
            CURRENT_ROOTS[
                dataset
            ]
            / rel
        )


        combined_segments = (
            combined_dir
            / "segments.npy"
        )

        combined_labels = (
            combined_dir
            / "labels.npy"
        )

        current_segments = (
            current_dir
            / "segments.npy"
        )

        current_labels = (
            current_dir
            / "labels.npy"
        )


        # ----------------------------------------------------
        # Label lineage
        # ----------------------------------------------------

        labels_equal, label_status = (
            exact_array_equal(
                combined_labels,
                current_labels,
            )
        )

        if not labels_equal:

            aggregates[
                dataset
            ][
                "label_mismatch_count"
            ] += 1

            if len(
                label_mismatches
            ) < 30:
                label_mismatches.append(
                    {
                        "trial":
                            str(rel),
                        "dataset":
                            dataset,
                        "status":
                            label_status,
                    }
                )


        # ----------------------------------------------------
        # Historical back-tree identity for UniVR + OnField
        # ----------------------------------------------------

        if dataset in {
            "UNIVRFALL",
            "ONFIELD",
        }:

            back_dir = (
                HISTORICAL_UNIVR
                / rel
            )

            seg_equal, seg_status = (
                exact_array_equal(
                    combined_segments,
                    back_dir
                    / "segments.npy",
                )
            )

            back_label_equal, back_label_status = (
                exact_array_equal(
                    combined_labels,
                    back_dir
                    / "labels.npy",
                )
            )

            if (
                seg_equal
                and back_label_equal
            ):
                aggregates[
                    dataset
                ][
                    "historical_back_exact_trial_count"
                ] += 1

            else:
                aggregates[
                    dataset
                ][
                    "historical_back_mismatch_trial_count"
                ] += 1

                if len(
                    historical_back_mismatches
                ) < 30:

                    historical_back_mismatches.append(
                        {
                            "trial":
                                str(rel),

                            "dataset":
                                dataset,

                            "segment_status":
                                seg_status,

                            "label_status":
                                back_label_status,
                        }
                    )


        # ----------------------------------------------------
        # Protected six-channel transformation
        # ----------------------------------------------------

        trial_result = (
            compare_task6_transform(
                combined_segments,
                current_segments,
                SIGN_MAPS[
                    dataset
                ],
            )
        )

        add_transform_result(
            aggregates[
                dataset
            ],
            trial_result,
        )


        # Record largest individual KFall residual examples.
        if (
            dataset == "KFALL"
            and trial_result[
                "absolute_error_max"
            ] > 0
        ):

            transform_outliers.append(
                {
                    "trial":
                        str(rel),

                    "max_abs":
                        trial_result[
                            "absolute_error_max"
                        ],

                    "mae": (
                        trial_result[
                            "absolute_error_sum"
                        ]
                        / trial_result[
                            "value_count"
                        ]
                        if trial_result[
                            "value_count"
                        ]
                        else 0.0
                    ),
                }
            )


        if (
            index % 500
        ) == 0:
            print(
                f"processed "
                f"{index}/"
                f"{len(trial_dirs)}",
                flush=True,
            )


    # --------------------------------------------------------
    # Derived aggregate statistics
    # --------------------------------------------------------

    for dataset, agg in (
        aggregates.items()
    ):

        if agg[
            "value_count"
        ]:

            agg[
                "mae"
            ] = (
                agg[
                    "absolute_error_sum"
                ]
                / agg[
                    "value_count"
                ]
            )

            agg[
                "exact_fraction"
            ] = (
                agg[
                    "exact_count"
                ]
                / agg[
                    "value_count"
                ]
            )

        else:

            agg["mae"] = 0.0
            agg["exact_fraction"] = 1.0


        agg[
            "error_bins"
        ] = [
            {
                "lower_inclusive":
                    (
                        None
                        if not np.isfinite(
                            ABS_ERROR_BIN_EDGES[i]
                        )
                        else ABS_ERROR_BIN_EDGES[i]
                    ),

                "upper_exclusive":
                    (
                        None
                        if not np.isfinite(
                            ABS_ERROR_BIN_EDGES[
                                i + 1
                            ]
                        )
                        else ABS_ERROR_BIN_EDGES[
                            i + 1
                        ]
                    ),

                "count":
                    agg[
                        "bin_counts"
                    ][i],
            }
            for i in range(
                len(
                    ABS_ERROR_BIN_EDGES
                )
                - 1
            )
        ]


    transform_outliers.sort(
        key=lambda row:
            row[
                "max_abs"
            ],
        reverse=True,
    )


    output = {
        "audit_id":
            "FULL_SIGNAL_LINEAGE_AUDIT_V1",

        "status":
            "candidate_full_dataset_audit",

        "combined_root":
            str(
                COMBINED
            ),

        "dataset_trial_counts":
            dict(
                dataset_counts
            ),

        "protected_task_channels":
            [
                "AccX",
                "AccY",
                "AccZ",
                "GyrX",
                "GyrY",
                "GyrZ",
            ],

        "candidate_sign_maps": {
            dataset:
                signs.astype(
                    int
                ).tolist()
            for dataset, signs
            in SIGN_MAPS.items()
        },

        "aggregates":
            aggregates,

        "historical_back_mismatch_examples":
            historical_back_mismatches,

        "label_mismatch_examples":
            label_mismatches,

        "largest_kfall_transform_residuals":
            transform_outliers[:30],

        "notes": [
            (
                "Absolute residual bins are descriptive lineage "
                "statistics, not detector thresholds."
            ),
            (
                "Euler channels are not part of the protected "
                "CNN input and are not used for task6 transform "
                "qualification."
            ),
        ],
    }


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


    # --------------------------------------------------------
    # Human-readable report
    # --------------------------------------------------------

    print()
    print(
        "=" * 100
    )

    print(
        "FULL SIGNAL LINEAGE SUMMARY"
    )

    print(
        "=" * 100
    )

    print(
        "dataset_trial_counts =",
        dict(
            dataset_counts
        ),
    )


    for dataset in (
        "UNIVRFALL",
        "ONFIELD",
        "KFALL",
    ):

        agg = aggregates[
            dataset
        ]

        print()
        print(
            dataset
        )

        print(
            " sign_map =",
            SIGN_MAPS[
                dataset
            ].astype(
                int
            ).tolist(),
        )

        print(
            " trial_count =",
            agg[
                "trial_count"
            ],
        )

        print(
            " empty_trial_count =",
            agg[
                "empty_trial_count"
            ],
        )

        print(
            " shape_mismatch_count =",
            agg[
                "shape_mismatch_count"
            ],
        )

        print(
            " label_mismatch_count =",
            agg[
                "label_mismatch_count"
            ],
        )

        if dataset in {
            "UNIVRFALL",
            "ONFIELD",
        }:

            print(
                " historical_back_exact_trial_count =",
                agg[
                    "historical_back_exact_trial_count"
                ],
            )

            print(
                " historical_back_mismatch_trial_count =",
                agg[
                    "historical_back_mismatch_trial_count"
                ],
            )

        print(
            " task6_value_count =",
            agg[
                "value_count"
            ],
        )

        print(
            " task6_exact_fraction =",
            agg[
                "exact_fraction"
            ],
        )

        print(
            " task6_mae =",
            agg[
                "mae"
            ],
        )

        print(
            " task6_max_abs =",
            agg[
                "absolute_error_max"
            ],
        )


    print()
    print(
        "historical_back_mismatch_examples =",
        historical_back_mismatches,
    )

    print(
        "label_mismatch_examples =",
        label_mismatches,
    )


    print()
    print(
        "largest_kfall_transform_residuals:"
    )

    for row in transform_outliers[:20]:
        print(
            " ",
            row,
        )


    univr_pass = (
        aggregates[
            "UNIVRFALL"
        ][
            "shape_mismatch_count"
        ] == 0
        and aggregates[
            "UNIVRFALL"
        ][
            "label_mismatch_count"
        ] == 0
        and aggregates[
            "UNIVRFALL"
        ][
            "historical_back_mismatch_trial_count"
        ] == 0
        and aggregates[
            "UNIVRFALL"
        ][
            "absolute_error_max"
        ] == 0.0
    )


    onfield_pass = (
        aggregates[
            "ONFIELD"
        ][
            "shape_mismatch_count"
        ] == 0
        and aggregates[
            "ONFIELD"
        ][
            "label_mismatch_count"
        ] == 0
        and aggregates[
            "ONFIELD"
        ][
            "historical_back_mismatch_trial_count"
        ] == 0
        and aggregates[
            "ONFIELD"
        ][
            "absolute_error_max"
        ] == 0.0
    )


    kfall_structural_pass = (
        aggregates[
            "KFALL"
        ][
            "shape_mismatch_count"
        ] == 0
        and aggregates[
            "KFALL"
        ][
            "label_mismatch_count"
        ] == 0
    )


    print()
    print(
        "UNIVR_EXACT_TASK6_LINEAGE_PASS =",
        univr_pass,
    )

    print(
        "ONFIELD_EXACT_TASK6_LINEAGE_PASS =",
        onfield_pass,
    )

    print(
        "KFALL_STRUCTURAL_LINEAGE_PASS =",
        kfall_structural_pass,
    )

    print(
        "KFALL_TASK6_MAX_RESIDUAL =",
        aggregates[
            "KFALL"
        ][
            "absolute_error_max"
        ],
    )

    print(
        "KFALL_TASK6_MAE =",
        aggregates[
            "KFALL"
        ][
            "mae"
        ],
    )

    print(
        "OUTPUT_JSON =",
        OUTPUT,
    )

    print()
    print(
        "FULL_SIGNAL_LINEAGE_AUDIT_COMPLETE"
    )


if __name__ == "__main__":
    main()
