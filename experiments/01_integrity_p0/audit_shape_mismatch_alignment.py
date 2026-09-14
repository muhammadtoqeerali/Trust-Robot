from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import re

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

RAW_UNIVR = Path(
    "/mnt/hdd16T/protechto/"
    "UniVrFall_oriented/sensors_data"
)

RAW_KFALL = Path(
    "/mnt/hdd16T/protechto/"
    "ThirdPartyDatasets/"
    "KFall_oriented/sensors_data"
)

OUTPUT = (
    ROOT
    / "data/provenance/"
      "shape_mismatch_alignment_audit_v1.json"
)


SIGNS = {
    "UNIVRFALL": np.asarray(
        [-1, +1, -1, -1, +1, -1],
        dtype=np.float64,
    ),

    "KFALL": np.asarray(
        [-1, -1, -1, -1, +1, -1],
        dtype=np.float64,
    ),
}


TRIAL_RE = re.compile(
    r"^S(?P<subject>\d+)"
    r"T(?P<task>\d+)"
    r"R(?P<trial>\d+)\.csv$",
    re.IGNORECASE,
)


def window_count_from_rows(n_rows: int) -> int:

    if n_rows < 40:
        return 0

    return (
        (n_rows - 40) // 20
        + 1
    )


def csv_data_rows(path: Path) -> int:

    # Current oriented UniVR and KFall files have one CSV header row.
    # Count lines without loading the full dataframe.
    count = 0

    with path.open(
        "r",
        encoding="utf-8",
        errors="replace",
    ) as f:

        for _ in f:
            count += 1

    return max(
        count - 1,
        0,
    )


def build_raw_index(
    root: Path,
) -> dict[
    tuple[int, int, int],
    Path,
]:

    index = {}

    for path in root.rglob(
        "*.csv"
    ):

        m = TRIAL_RE.match(
            path.name
        )

        if m is None:
            continue

        key = (
            int(m.group("subject")),
            int(m.group("task")),
            int(m.group("trial")),
        )

        if key in index:
            raise RuntimeError(
                f"Duplicate raw key {key}"
            )

        index[key] = path

    return index


def load(path: Path):

    return np.load(
        path,
        mmap_mode="r",
        allow_pickle=False,
    )


def compare_overlap(
    historical_segments: Path,
    current_segments: Path,
    historical_labels: Path,
    current_labels: Path,
    signs: np.ndarray,
    *,
    chunk_windows: int = 2048,
) -> dict:

    h = load(
        historical_segments
    )

    c = load(
        current_segments
    )

    hl = load(
        historical_labels
    )

    cl = load(
        current_labels
    )


    nh = int(
        h.shape[0]
    ) if h.ndim > 0 else 0

    nc = int(
        c.shape[0]
    ) if c.ndim > 0 else 0

    overlap = min(
        nh,
        nc,
    )


    result = {
        "historical_windows": nh,
        "current_windows": nc,

        "current_minus_historical":
            nc - nh,

        "overlap_windows":
            overlap,

        "overlap_label_equal":
            True,

        "task6_exact":
            True,

        "task6_value_count":
            0,

        "task6_exact_count":
            0,

        "task6_abs_error_sum":
            0.0,

        "task6_abs_error_max":
            0.0,
    }


    if overlap == 0:
        return result


    if (
        h.ndim != 3
        or c.ndim != 3
        or h.shape[1:] != c.shape[1:]
        or h.shape[2] < 6
    ):
        raise RuntimeError(
            "Unexpected overlapping shapes: "
            f"{h.shape} vs {c.shape}"
        )


    result[
        "overlap_label_equal"
    ] = bool(
        np.array_equal(
            hl[:overlap],
            cl[:overlap],
        )
    )


    for start in range(
        0,
        overlap,
        chunk_windows,
    ):

        stop = min(
            start + chunk_windows,
            overlap,
        )

        a = np.asarray(
            h[
                start:stop,
                :,
                :6,
            ],
            dtype=np.float64,
        )

        b = np.asarray(
            c[
                start:stop,
                :,
                :6,
            ],
            dtype=np.float64,
        )

        reconstructed = (
            b
            * signs.reshape(
                1,
                1,
                6,
            )
        )

        diff = (
            a
            - reconstructed
        )

        absolute = np.abs(
            diff
        )

        result[
            "task6_value_count"
        ] += int(
            absolute.size
        )

        result[
            "task6_exact_count"
        ] += int(
            np.count_nonzero(
                diff == 0
            )
        )

        result[
            "task6_abs_error_sum"
        ] += float(
            np.sum(
                absolute,
                dtype=np.float64,
            )
        )

        result[
            "task6_abs_error_max"
        ] = max(
            result[
                "task6_abs_error_max"
            ],
            float(
                np.max(
                    absolute
                )
            ),
        )

        if not np.array_equal(
            a,
            reconstructed,
        ):
            result[
                "task6_exact"
            ] = False


    return result


def main() -> None:

    print(
        "Building raw indexes...",
        flush=True,
    )

    raw_univr = build_raw_index(
        RAW_UNIVR
    )

    raw_kfall = build_raw_index(
        RAW_KFALL
    )


    aggregates = {}

    records = []


    for dataset in (
        "UNIVRFALL",
        "KFALL",
    ):

        aggregates[
            dataset
        ] = {
            "trial_count": 0,
            "shape_match_count": 0,
            "shape_mismatch_count": 0,

            "mismatch_overlap_label_equal_count": 0,
            "mismatch_overlap_label_mismatch_count": 0,

            "mismatch_overlap_task6_exact_count": 0,

            "mismatch_task6_value_count": 0,
            "mismatch_task6_exact_count": 0,
            "mismatch_task6_abs_error_sum": 0.0,
            "mismatch_task6_abs_error_max": 0.0,

            "raw_pair_count": 0,

            "current_windows_match_raw_formula_count": 0,

            "historical_windows_match_current_raw_formula_count": 0,

            "shape_delta_counts": Counter(),
        }


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


    for i, combined_dir in enumerate(
        trial_dirs,
        start=1,
    ):

        rel = combined_dir.relative_to(
            COMBINED
        )

        subject = int(
            rel.parts[0]
        )

        task = int(
            rel.parts[1]
        )

        trial = int(
            rel.parts[2]
        )


        # OnField is not part of this mismatch investigation.
        if (
            CURRENT_UNIVR
            / rel
        ).is_dir():

            dataset = "UNIVRFALL"

            current_dir = (
                CURRENT_UNIVR
                / rel
            )

            raw_key = (
                subject,
                task,
                trial,
            )

            raw_path = raw_univr.get(
                raw_key
            )


        elif (
            CURRENT_KFALL
            / rel
        ).is_dir():

            dataset = "KFALL"

            current_dir = (
                CURRENT_KFALL
                / rel
            )

            raw_key = (
                subject - 100,
                task,
                trial,
            )

            raw_path = raw_kfall.get(
                raw_key
            )


        else:
            continue


        agg = aggregates[
            dataset
        ]

        agg[
            "trial_count"
        ] += 1


        h_seg = (
            combined_dir
            / "segments.npy"
        )

        h_lab = (
            combined_dir
            / "labels.npy"
        )

        c_seg = (
            current_dir
            / "segments.npy"
        )

        c_lab = (
            current_dir
            / "labels.npy"
        )


        h = load(
            h_seg
        )

        c = load(
            c_seg
        )


        nh = int(
            h.shape[0]
        ) if h.ndim > 0 else 0

        nc = int(
            c.shape[0]
        ) if c.ndim > 0 else 0


        if nh == nc:

            agg[
                "shape_match_count"
            ] += 1

        else:

            agg[
                "shape_mismatch_count"
            ] += 1

            agg[
                "shape_delta_counts"
            ][
                nc - nh
            ] += 1


            result = compare_overlap(
                h_seg,
                c_seg,
                h_lab,
                c_lab,
                SIGNS[
                    dataset
                ],
            )


            if result[
                "overlap_label_equal"
            ]:

                agg[
                    "mismatch_overlap_label_equal_count"
                ] += 1

            else:

                agg[
                    "mismatch_overlap_label_mismatch_count"
                ] += 1


            if result[
                "task6_exact"
            ]:

                agg[
                    "mismatch_overlap_task6_exact_count"
                ] += 1


            agg[
                "mismatch_task6_value_count"
            ] += result[
                "task6_value_count"
            ]

            agg[
                "mismatch_task6_exact_count"
            ] += result[
                "task6_exact_count"
            ]

            agg[
                "mismatch_task6_abs_error_sum"
            ] += result[
                "task6_abs_error_sum"
            ]

            agg[
                "mismatch_task6_abs_error_max"
            ] = max(
                agg[
                    "mismatch_task6_abs_error_max"
                ],
                result[
                    "task6_abs_error_max"
                ],
            )


            record = {
                "dataset":
                    dataset,

                "trial":
                    str(rel),

                **result,
            }


            if raw_path is not None:

                agg[
                    "raw_pair_count"
                ] += 1

                n_rows = csv_data_rows(
                    raw_path
                )

                expected = (
                    window_count_from_rows(
                        n_rows
                    )
                )

                record[
                    "raw_path"
                ] = str(
                    raw_path
                )

                record[
                    "raw_rows"
                ] = n_rows

                record[
                    "expected_windows_from_current_raw"
                ] = expected


                if expected == nc:

                    agg[
                        "current_windows_match_raw_formula_count"
                    ] += 1


                if expected == nh:

                    agg[
                        "historical_windows_match_current_raw_formula_count"
                    ] += 1


            else:

                record[
                    "raw_path"
                ] = None


            records.append(
                record
            )


        if (
            i % 500
        ) == 0:

            print(
                f"processed {i}/"
                f"{len(trial_dirs)}",
                flush=True,
            )


    output_aggregates = {}


    for dataset, agg in (
        aggregates.items()
    ):

        values = agg[
            "mismatch_task6_value_count"
        ]

        output_aggregates[
            dataset
        ] = {
            k: (
                dict(v)
                if isinstance(
                    v,
                    Counter,
                )
                else v
            )
            for k, v
            in agg.items()
        }


        output_aggregates[
            dataset
        ][
            "mismatch_task6_mae"
        ] = (
            agg[
                "mismatch_task6_abs_error_sum"
            ]
            / values
            if values
            else 0.0
        )


        output_aggregates[
            dataset
        ][
            "mismatch_task6_exact_fraction"
        ] = (
            agg[
                "mismatch_task6_exact_count"
            ]
            / values
            if values
            else 1.0
        )


    output = {
        "audit_id":
            "SHAPE_MISMATCH_ALIGNMENT_AUDIT_V1",

        "status":
            "candidate_lineage_diagnostic",

        "window_rule": {
            "window_samples": 40,
            "step_samples": 20,
            "sampling_rate_hz": 100,
        },

        "sign_maps": {
            k:
                v.astype(
                    int
                ).tolist()
            for k, v
            in SIGNS.items()
        },

        "aggregates":
            output_aggregates,

        "mismatch_records":
            records,
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


    print()
    print(
        "=" * 100
    )

    print(
        "SHAPE MISMATCH ALIGNMENT SUMMARY"
    )

    print(
        "=" * 100
    )


    for dataset in (
        "UNIVRFALL",
        "KFALL",
    ):

        agg = output_aggregates[
            dataset
        ]

        print()
        print(
            dataset
        )

        for key in (
            "trial_count",
            "shape_match_count",
            "shape_mismatch_count",
            "mismatch_overlap_label_equal_count",
            "mismatch_overlap_label_mismatch_count",
            "mismatch_overlap_task6_exact_count",
            "mismatch_task6_exact_fraction",
            "mismatch_task6_mae",
            "mismatch_task6_abs_error_max",
            "raw_pair_count",
            "current_windows_match_raw_formula_count",
            "historical_windows_match_current_raw_formula_count",
        ):

            print(
                f" {key} =",
                agg[
                    key
                ],
            )


        top_deltas = sorted(
            (
                (
                    int(delta),
                    int(count),
                )
                for delta, count
                in agg[
                    "shape_delta_counts"
                ].items()
            ),
            key=lambda x:
                (
                    -x[1],
                    x[0],
                ),
        )[:30]


        print(
            " shape_delta_top30 =",
            top_deltas,
        )


    print()
    print(
        "OUTPUT_JSON =",
        OUTPUT,
    )

    print(
        "SHAPE_MISMATCH_ALIGNMENT_AUDIT_COMPLETE"
    )


if __name__ == "__main__":
    main()
