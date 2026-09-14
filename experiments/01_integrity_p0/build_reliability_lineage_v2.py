from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import re
import subprocess

import numpy as np


ROOT = Path.home() / "toqeer" / "IMU_Reliability"

SPLIT = (
    ROOT
    / "data/manifests/"
      "date2025_cnn400_inferred_split_v1.json"
)

OUTPUT = (
    ROOT
    / "data/provenance/"
      "reliability_lineage_v2_candidate.json"
)

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

RAW_UNIVR_ORIGINAL = Path(
    "/mnt/hdd16T/protechto/"
    "UniVrFallOriginalDataset"
)

RAW_UNIVR_ORIENTED = Path(
    "/mnt/hdd16T/protechto/"
    "UniVrFall_oriented/sensors_data"
)

RAW_KFALL = Path(
    "/mnt/hdd16T/protechto/"
    "ThirdPartyDatasets/KFall/sensors_data"
)

RAW_KFALL_ORIENTED = Path(
    "/mnt/hdd16T/protechto/"
    "ThirdPartyDatasets/KFall_oriented/sensors_data"
)

AUGMENTATION_ONLY = {
    "999",
    "1000",
}

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

TRIAL_RE = re.compile(
    r"^S(?P<subject>\d+)"
    r"T(?P<task>\d+)"
    r"R(?P<trial>\d+)\.csv$",
    re.IGNORECASE,
)


def git(*args):
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=ROOT,
            text=True,
        ).strip()
    except Exception:
        return None


def load(path):
    return np.load(
        path,
        mmap_mode="r",
        allow_pickle=False,
    )


def n_windows(path):
    x = load(path)

    if x.size == 0:
        return 0

    if x.ndim != 3:
        raise RuntimeError(
            f"Unexpected segment shape {x.shape}: {path}"
        )

    return int(x.shape[0])


def exact_array(
    a_path,
    b_path,
    *,
    chunk=2048,
):
    if not a_path.is_file() or not b_path.is_file():
        return False

    a = load(a_path)
    b = load(b_path)

    if a.shape != b.shape or a.dtype != b.dtype:
        return False

    if a.size == 0:
        return True

    for start in range(0, len(a), chunk):
        stop = min(start + chunk, len(a))

        if not np.array_equal(
            a[start:stop],
            b[start:stop],
        ):
            return False

    return True


def overlap_labels_equal(
    a_path,
    b_path,
):
    a = load(a_path)
    b = load(b_path)

    n = min(
        len(a),
        len(b),
    )

    return bool(
        np.array_equal(
            a[:n],
            b[:n],
        )
    )


def task6_transform_stats(
    historical_path,
    current_path,
    signs,
    *,
    overlap_only=True,
    chunk=2048,
):
    h = load(historical_path)
    c = load(current_path)

    nh = (
        int(h.shape[0])
        if h.ndim > 0
        else 0
    )

    nc = (
        int(c.shape[0])
        if c.ndim > 0
        else 0
    )

    n = min(nh, nc)

    if not overlap_only and nh != nc:
        raise ValueError(
            "Full comparison requested for unequal lengths"
        )

    if n == 0:
        return {
            "value_count": 0,
            "exact": True,
            "exact_fraction": 1.0,
            "mae": 0.0,
            "max_abs": 0.0,
        }

    if (
        h.ndim != 3
        or c.ndim != 3
        or h.shape[1:] != c.shape[1:]
    ):
        raise RuntimeError(
            f"Incompatible segment shapes: "
            f"{h.shape} vs {c.shape}"
        )

    count = 0
    exact_count = 0
    absolute_sum = 0.0
    absolute_max = 0.0

    all_exact = True

    signs = signs.reshape(
        1,
        1,
        6,
    )

    for start in range(
        0,
        n,
        chunk,
    ):
        stop = min(
            start + chunk,
            n,
        )

        a = np.asarray(
            h[start:stop, :, :6],
            dtype=np.float64,
        )

        b = np.asarray(
            c[start:stop, :, :6],
            dtype=np.float64,
        )

        reconstructed = (
            b * signs
        )

        diff = (
            a - reconstructed
        )

        absolute = np.abs(diff)

        if not np.all(
            np.isfinite(absolute)
        ):
            raise RuntimeError(
                f"Non-finite transform residual: "
                f"{historical_path}"
            )

        if not np.array_equal(
            a,
            reconstructed,
        ):
            all_exact = False

        count += int(
            absolute.size
        )

        exact_count += int(
            np.count_nonzero(
                diff == 0
            )
        )

        absolute_sum += float(
            np.sum(
                absolute,
                dtype=np.float64,
            )
        )

        absolute_max = max(
            absolute_max,
            float(
                np.max(
                    absolute
                )
            ),
        )

    return {
        "value_count":
            count,

        "exact":
            all_exact,

        "exact_fraction":
            (
                exact_count / count
                if count
                else 1.0
            ),

        "mae":
            (
                absolute_sum / count
                if count
                else 0.0
            ),

        "max_abs":
            absolute_max,
    }


def build_raw_index(root):
    index = {}

    for path in root.rglob(
        "*.csv"
    ):
        match = TRIAL_RE.match(
            path.name
        )

        if not match:
            continue

        key = (
            int(match.group("subject")),
            int(match.group("task")),
            int(match.group("trial")),
        )

        index.setdefault(
            key,
            [],
        ).append(
            str(path)
        )

    return index


def identify_dataset(rel):
    if (
        CURRENT_ONFIELD
        / rel
    ).is_dir():
        return "ONFIELD"

    if (
        CURRENT_UNIVR
        / rel
    ).is_dir():
        return "UNIVRFALL"

    if (
        CURRENT_KFALL
        / rel
    ).is_dir():
        return "KFALL"

    raise RuntimeError(
        f"Dataset identity unresolved: {rel}"
    )


def canonical_digest(payload):
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return sha256(
        raw
    ).hexdigest()


def main():
    split = json.loads(
        SPLIT.read_text()
    )

    subject_role = {}

    for subject in split[
        "train_subjects"
    ]:
        subject_role[
            str(subject)
        ] = "train"

    for subject in split[
        "validation_subjects"
    ]:
        subject_role[
            str(subject)
        ] = "validation"

    for subject in split[
        "test_subjects"
    ]:
        subject_role[
            str(subject)
        ] = "test"

    for subject in AUGMENTATION_ONLY:
        subject_role[
            subject
        ] = (
            "historical_training_augmentation_only"
        )


    print(
        "Building raw indexes...",
        flush=True,
    )

    univr_original = build_raw_index(
        RAW_UNIVR_ORIGINAL
    )

    univr_oriented = build_raw_index(
        RAW_UNIVR_ORIENTED
    )

    kfall_raw = build_raw_index(
        RAW_KFALL
    )

    kfall_oriented = build_raw_index(
        RAW_KFALL_ORIENTED
    )


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


    records = []

    dataset_counts = Counter()
    role_counts = Counter()
    lineage_counts = Counter()
    raw_pairing_counts = Counter()

    split_windows = Counter()
    augmentation_windows = 0

    kfall_aligned_value_count = 0
    kfall_aligned_abs_sum = 0.0
    kfall_aligned_abs_max = 0.0

    historical_back_mismatch = []


    for index, combined_dir in enumerate(
        trial_dirs,
        start=1,
    ):
        rel = combined_dir.relative_to(
            COMBINED
        )

        subject = rel.parts[0]
        task = int(rel.parts[1])
        trial = int(rel.parts[2])

        role = subject_role.get(
            subject
        )

        if role is None:
            raise RuntimeError(
                f"Unexpected subject: {subject}"
            )

        dataset = identify_dataset(
            rel
        )

        dataset_counts[
            dataset
        ] += 1

        role_counts[
            role
        ] += 1


        historical_segments = (
            combined_dir
            / "segments.npy"
        )

        historical_labels = (
            combined_dir
            / "labels.npy"
        )

        nh = n_windows(
            historical_segments
        )


        if role in {
            "train",
            "validation",
            "test",
        }:
            split_windows[
                role
            ] += nh
        else:
            augmentation_windows += nh


        if dataset == "UNIVRFALL":
            current_dir = (
                CURRENT_UNIVR
                / rel
            )
        elif dataset == "KFALL":
            current_dir = (
                CURRENT_KFALL
                / rel
            )
        else:
            current_dir = (
                CURRENT_ONFIELD
                / rel
            )


        current_segments = (
            current_dir
            / "segments.npy"
        )

        current_labels = (
            current_dir
            / "labels.npy"
        )

        nc = n_windows(
            current_segments
        )


        label_overlap_equal = (
            overlap_labels_equal(
                historical_labels,
                current_labels,
            )
        )


        # ----------------------------------------------------
        # Historical back-tree identity
        # ----------------------------------------------------

        historical_back_status = (
            "NOT_APPLICABLE"
        )

        if dataset in {
            "UNIVRFALL",
            "ONFIELD",
        }:
            back_dir = (
                HISTORICAL_UNIVR
                / rel
            )

            seg_equal = exact_array(
                historical_segments,
                back_dir
                / "segments.npy",
            )

            lab_equal = exact_array(
                historical_labels,
                back_dir
                / "labels.npy",
            )

            if seg_equal and lab_equal:
                historical_back_status = (
                    "BYTE_EXACT"
                )
            else:
                historical_back_status = (
                    "MISMATCH"
                )

                historical_back_mismatch.append(
                    str(rel)
                )


        # ----------------------------------------------------
        # Signal lineage class
        # ----------------------------------------------------

        if dataset in {
            "UNIVRFALL",
            "ONFIELD",
        }:
            stats = task6_transform_stats(
                historical_segments,
                current_segments,
                SIGN_MAPS[
                    dataset
                ],
            )

            if (
                nh == nc
                and label_overlap_equal
                and stats["exact"]
            ):
                lineage = (
                    "CURRENT_TASK6_EXACT_FULL"
                )

            elif (
                dataset == "UNIVRFALL"
                and nc == nh + 1
                and label_overlap_equal
                and stats["exact"]
            ):
                lineage = (
                    "CURRENT_TASK6_EXACT_HISTORICAL_PREFIX"
                )

            else:
                lineage = (
                    "CURRENT_PROCESSED_VERSION_DIVERGENT"
                )

        else:
            # KFall:
            # Compute transform residual only when the historical and
            # current window grids have equal length. This is the set
            # for which zero-index comparison is justified.
            if (
                nh == nc
                and label_overlap_equal
            ):
                stats = task6_transform_stats(
                    historical_segments,
                    current_segments,
                    SIGN_MAPS["KFALL"],
                )

                lineage = (
                    "CURRENT_SHAPE_LABEL_ALIGNED_FIXED_SIGN_RESIDUAL"
                )

                kfall_aligned_value_count += (
                    stats[
                        "value_count"
                    ]
                )

                kfall_aligned_abs_sum += (
                    stats[
                        "mae"
                    ]
                    * stats[
                        "value_count"
                    ]
                )

                kfall_aligned_abs_max = max(
                    kfall_aligned_abs_max,
                    stats[
                        "max_abs"
                    ],
                )

            elif label_overlap_equal:
                stats = None

                lineage = (
                    "CURRENT_LENGTH_DIVERGENT_LABEL_PREFIX_ALIGNED"
                )

            else:
                stats = None

                lineage = (
                    "CURRENT_PROCESSED_VERSION_DIVERGENT"
                )


        lineage_counts[
            (
                dataset,
                lineage,
            )
        ] += 1


        # ----------------------------------------------------
        # Raw acquisition filename pairing
        # ----------------------------------------------------

        if dataset == "UNIVRFALL":
            key = (
                int(subject),
                task,
                trial,
            )

            original_paths = (
                univr_original.get(
                    key,
                    [],
                )
            )

            oriented_paths = (
                univr_oriented.get(
                    key,
                    [],
                )
            )

            raw_status = (
                "EXACT_FILENAME_PAIR"
                if (
                    len(original_paths) == 1
                    and len(oriented_paths) == 1
                )
                else "UNRESOLVED"
            )

            raw = {
                "status":
                    raw_status,

                "original":
                    original_paths,

                "oriented":
                    oriented_paths,

                "frame_counter_hard_qualified":
                    False,

                "original_timestamp_available":
                    True,
            }


        elif dataset == "KFALL":
            key = (
                int(subject) - 100,
                task,
                trial,
            )

            original_paths = (
                kfall_raw.get(
                    key,
                    [],
                )
            )

            oriented_paths = (
                kfall_oriented.get(
                    key,
                    [],
                )
            )

            raw_status = (
                "EXACT_FILENAME_PAIR"
                if (
                    len(original_paths) == 1
                    and len(oriented_paths) == 1
                )
                else "UNRESOLVED"
            )

            raw = {
                "status":
                    raw_status,

                "raw_subject":
                    int(subject) - 100,

                "original":
                    original_paths,

                "oriented":
                    oriented_paths,

                "frame_counter_hard_qualified":
                    True,

                "timestamp_available":
                    True,
            }


        else:
            raw_status = (
                "TRIAL_MAPPING_UNVERIFIED"
            )

            raw = {
                "status":
                    raw_status,

                "frame_counter_hard_qualified":
                    False,
            }


        raw_pairing_counts[
            (
                dataset,
                raw_status,
            )
        ] += 1


        records.append(
            {
                "subject":
                    subject,

                "task":
                    task,

                "trial":
                    trial,

                "relative_trial":
                    str(rel),

                "role":
                    role,

                "dataset":
                    dataset,

                "historical_windows":
                    nh,

                "current_windows":
                    nc,

                "current_minus_historical_windows":
                    nc - nh,

                "historical_back_status":
                    historical_back_status,

                "current_label_overlap_equal":
                    label_overlap_equal,

                "protected_task6_sign_map":
                    SIGN_MAPS[
                        dataset
                    ].astype(
                        int
                    ).tolist(),

                "signal_lineage":
                    lineage,

                "transform_stats":
                    stats,

                "raw_pairing":
                    raw,
            }
        )


        if (
            index % 500
        ) == 0:
            print(
                f"processed {index}/"
                f"{len(trial_dirs)}",
                flush=True,
            )


    expected_windows = {
        name:
            int(
                split[
                    "preaugmentation_counts"
                ][name]["total"]
            )
        for name in (
            "train",
            "validation",
            "test",
        )
    }


    if dict(
        split_windows
    ) != expected_windows:
        raise RuntimeError(
            "Frozen split window counts changed: "
            f"{dict(split_windows)} "
            f"vs {expected_windows}"
        )


    expected_dataset_counts = {
        "UNIVRFALL": 1100,
        "KFALL": 5075,
        "ONFIELD": 18,
    }

    if dict(
        dataset_counts
    ) != expected_dataset_counts:
        raise RuntimeError(
            "Unexpected dataset trial counts: "
            f"{dict(dataset_counts)}"
        )


    if augmentation_windows != 220472:
        raise RuntimeError(
            "Historical augmentation fingerprint changed: "
            f"{augmentation_windows}"
        )


    if historical_back_mismatch:
        raise RuntimeError(
            "Historical back-tree mismatch found: "
            f"{historical_back_mismatch[:10]}"
        )


    expected_lineage = {
        (
            "UNIVRFALL",
            "CURRENT_TASK6_EXACT_FULL",
        ): 713,

        (
            "UNIVRFALL",
            "CURRENT_TASK6_EXACT_HISTORICAL_PREFIX",
        ): 289,

        (
            "UNIVRFALL",
            "CURRENT_PROCESSED_VERSION_DIVERGENT",
        ): 98,

        (
            "ONFIELD",
            "CURRENT_TASK6_EXACT_FULL",
        ): 18,

        (
            "KFALL",
            "CURRENT_SHAPE_LABEL_ALIGNED_FIXED_SIGN_RESIDUAL",
        ): 3301,

        (
            "KFALL",
            "CURRENT_LENGTH_DIVERGENT_LABEL_PREFIX_ALIGNED",
        ): 1573,

        (
            "KFALL",
            "CURRENT_PROCESSED_VERSION_DIVERGENT",
        ): 201,
    }


    if dict(
        lineage_counts
    ) != expected_lineage:
        raise RuntimeError(
            "Lineage class counts differ from audited evidence: "
            f"{dict(lineage_counts)}"
        )


    kfall_mae = (
        kfall_aligned_abs_sum
        / kfall_aligned_value_count
        if kfall_aligned_value_count
        else 0.0
    )


    payload = {
        "manifest_id":
            "RELIABILITY_LINEAGE_V2",

        "status":
            "candidate_for_freeze",

        "repository": {
            "head":
                git(
                    "rev-parse",
                    "HEAD",
                ),

            "protected_baseline":
                git(
                    "rev-parse",
                    "baseline-date2025-cnn400-v1",
                ),
        },

        "principles": {
            "protected_model_uses_historical_arrays":
                True,

            "current_processed_arrays_are_not_silently_substituted":
                True,

            "raw_metadata_provenance_is_separate_from_signal_lineage":
                True,

            "synthetic_truth_is_separate_from_runtime_cause":
                True,
        },

        "dataset_trial_counts":
            dict(
                dataset_counts
            ),

        "role_trial_counts":
            dict(
                role_counts
            ),

        "frozen_split_window_counts":
            dict(
                split_windows
            ),

        "historical_augmentation_windows":
            augmentation_windows,

        "lineage_counts": [
            {
                "dataset":
                    dataset,

                "status":
                    status,

                "trial_count":
                    count,
            }
            for (
                dataset,
                status,
            ), count in sorted(
                lineage_counts.items()
            )
        ],

        "raw_pairing_counts": [
            {
                "dataset":
                    dataset,

                "status":
                    status,

                "trial_count":
                    count,
            }
            for (
                dataset,
                status,
            ), count in sorted(
                raw_pairing_counts.items()
            )
        ],

        "kfall_shape_aligned_transform": {
            "sign_map":
                SIGN_MAPS[
                    "KFALL"
                ].astype(
                    int
                ).tolist(),

            "value_count":
                kfall_aligned_value_count,

            "mae":
                kfall_mae,

            "max_abs":
                kfall_aligned_abs_max,

            "interpretation":
                (
                    "Descriptive historical/current lineage residual; "
                    "not an integrity detector threshold."
                ),
        },

        "dataset_level_evidence": {
            "UNIVRFALL": {
                "historical_back_tree_authoritative":
                    True,

                "historical_back_trials_byte_exact":
                    1100,

                "hard_frame_counter_available":
                    False,

                "original_timestamp_available":
                    True,

                "range_rail_verified":
                    False,
            },

            "KFALL": {
                "raw_frame_counter_hard_qualified":
                    True,

                "raw_timestamp_available":
                    True,

                "historical_current_signal_generations_differ":
                    True,

                "range_rail_verified_for_primary_claim":
                    False,
            },

            "ONFIELD": {
                "historical_back_tree_authoritative":
                    True,

                "historical_back_trials_byte_exact":
                    18,

                "role_999_1000":
                    "historical_training_augmentation_only",

                "raw_trial_mapping_verified":
                    False,
            },
        },

        "trials":
            records,
    }


    payload[
        "content_sha256"
    ] = canonical_digest(
        payload
    )


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        json.dumps(
            payload,
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
        "RELIABILITY LINEAGE V2 SUMMARY"
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

    print(
        "role_trial_counts =",
        dict(
            role_counts
        ),
    )

    print(
        "split_window_counts =",
        dict(
            split_windows
        ),
    )

    print(
        "augmentation_windows =",
        augmentation_windows,
    )


    print()
    print(
        "lineage_counts:"
    )

    for (
        dataset,
        status,
    ), count in sorted(
        lineage_counts.items()
    ):
        print(
            " ",
            dataset,
            status,
            "=",
            count,
        )


    print()
    print(
        "raw_pairing_counts:"
    )

    for (
        dataset,
        status,
    ), count in sorted(
        raw_pairing_counts.items()
    ):
        print(
            " ",
            dataset,
            status,
            "=",
            count,
        )


    print()
    print(
        "KFALL_ALIGNED_MAE =",
        kfall_mae,
    )

    print(
        "KFALL_ALIGNED_MAX_ABS =",
        kfall_aligned_abs_max,
    )

    print(
        "CONTENT_SHA256 =",
        payload[
            "content_sha256"
        ],
    )

    print(
        "OUTPUT =",
        OUTPUT,
    )

    print(
        "RELIABILITY_LINEAGE_V2_PASS = True"
    )


if __name__ == "__main__":
    main()
