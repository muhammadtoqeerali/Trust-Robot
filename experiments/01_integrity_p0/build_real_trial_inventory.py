from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import json
import os
import re

import numpy as np


ROOT = Path.home() / "toqeer" / "IMU_Reliability"

SPLIT_MANIFEST = (
    ROOT
    / "data/manifests/"
      "date2025_cnn400_inferred_split_v1.json"
)

OUTPUT_JSON = (
    ROOT
    / "data/manifests/"
      "reliability_trial_inventory_candidate_v1.json"
)


OLD = Path(
    "/mnt/hdd16T/protechto"
)

COMBINED = Path(
    "/mnt/hdd16T/protechto/data/back/"
    "UniVrFall_KFall/segments/"
    "400ms_50ov_npseg_filt_binary"
)


CANONICAL_PROCESSED = {
    "UNIVRFALL": Path(
        "/mnt/hdd16T/protechto/data/"
        "UniVrFall_oriented/segments/"
        "400ms_50ov_npseg_filt_binary"
    ),

    "KFALL": Path(
        "/mnt/hdd16T/protechto/data/"
        "KFall_oriented/segments/"
        "400ms_50ov_npseg_filt_binary"
    ),

    "ONFIELD": Path(
        "/mnt/hdd16T/protechto/data/"
        "OnField/segments/"
        "400ms_50ov_npseg_filt_binary"
    ),
}


UNIVR_ORIENTED_RAW = Path(
    "/mnt/hdd16T/protechto/"
    "UniVrFall_oriented/sensors_data"
)

UNIVR_ORIGINAL_RAW = Path(
    "/mnt/hdd16T/protechto/"
    "UniVrFallOriginalDataset"
)

KFALL_ORIENTED_RAW = Path(
    "/mnt/hdd16T/protechto/"
    "ThirdPartyDatasets/"
    "KFall_oriented/sensors_data"
)

KFALL_ORIGINAL_RAW = Path(
    "/mnt/hdd16T/protechto/"
    "ThirdPartyDatasets/"
    "KFall/sensors_data"
)

ONFIELD_RAW = Path(
    "/mnt/hdd16T/protechto/"
    "ThirdPartyDatasets/"
    "OnFieldRecordings"
)


# Historical activity-only augmentation streams.
#
# These subjects are present in the combined training tree but are not
# members of the frozen train/validation/test subject split.
AUGMENTATION_ONLY_SUBJECTS = {
    "999",
    "1000",
}


TRIAL_RE = re.compile(
    r"^S(?P<subject>\d+)"
    r"T(?P<task>\d+)"
    r"R(?P<trial>\d+)\.csv$",
    re.IGNORECASE,
)

ONFIELD_RE = re.compile(
    r"^(?P<prefix>.+)_"
    r"(?P<subject>\d+)\.csv$",
    re.IGNORECASE,
)


def sha256_file(
    path: Path,
    chunk_size: int = 8 * 1024 * 1024,
) -> str:

    h = sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(
                chunk_size
            )

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


_hash_cache: dict[Path, str] = {}


def cached_sha256(
    path: Path,
) -> str:

    if path not in _hash_cache:
        _hash_cache[path] = (
            sha256_file(path)
        )

    return _hash_cache[path]


def exact_pair_identity(
    combined_dir: Path,
    source_dir: Path,
) -> tuple[bool, str]:

    c_seg = combined_dir / "segments.npy"
    c_lab = combined_dir / "labels.npy"

    s_seg = source_dir / "segments.npy"
    s_lab = source_dir / "labels.npy"

    if not (
        c_seg.is_file()
        and c_lab.is_file()
        and s_seg.is_file()
        and s_lab.is_file()
    ):
        return False, "missing_files"

    try:
        if (
            os.path.samefile(
                c_seg,
                s_seg,
            )
            and os.path.samefile(
                c_lab,
                s_lab,
            )
        ):
            return True, "same_file"
    except Exception:
        pass

    if (
        c_seg.stat().st_size
        != s_seg.stat().st_size
        or c_lab.stat().st_size
        != s_lab.stat().st_size
    ):
        return False, "size_mismatch"

    seg_equal = (
        cached_sha256(c_seg)
        == cached_sha256(s_seg)
    )

    lab_equal = (
        cached_sha256(c_lab)
        == cached_sha256(s_lab)
    )

    if seg_equal and lab_equal:
        return True, "sha256_equal"

    return False, "hash_mismatch"


def segment_window_count(
    path: Path,
) -> int:

    x = np.load(
        path,
        mmap_mode="r",
        allow_pickle=False,
    )

    # Historical preprocessing can serialize trials with no surviving
    # windows as an empty 1-D NumPy array with shape (0,).
    #
    # This is accepted only for genuinely empty arrays. Any non-empty
    # non-3-D representation remains an error.
    if x.size == 0:
        return 0

    if x.ndim != 3:
        raise RuntimeError(
            f"Unexpected non-empty segment shape "
            f"{x.shape} at {path}"
        )

    return int(
        x.shape[0]
    )


def build_trial_csv_index(
    root: Path,
) -> dict[
    tuple[int, int, int],
    list[str],
]:

    index = defaultdict(list)

    if not root.is_dir():
        return {}

    for path in sorted(
        root.rglob("*.csv")
    ):

        m = TRIAL_RE.match(
            path.name
        )

        if m is None:
            continue

        key = (
            int(
                m.group(
                    "subject"
                )
            ),
            int(
                m.group(
                    "task"
                )
            ),
            int(
                m.group(
                    "trial"
                )
            ),
        )

        index[key].append(
            str(path)
        )

    return dict(index)


def build_onfield_index(
    root: Path,
) -> dict[int, list[str]]:

    index = defaultdict(list)

    if not root.is_dir():
        return {}

    for path in sorted(
        root.rglob("*.csv")
    ):

        m = ONFIELD_RE.match(
            path.name
        )

        if m is None:
            continue

        subject = int(
            m.group(
                "subject"
            )
        )

        index[subject].append(
            str(path)
        )

    return dict(index)


def raw_pairing(
    dataset: str,
    subject: int,
    task: int,
    trial: int,
    *,
    univr_oriented_index,
    univr_original_index,
    kfall_oriented_index,
    kfall_original_index,
    onfield_index,
) -> dict:

    if dataset == "UNIVRFALL":

        key = (
            subject,
            task,
            trial,
        )

        oriented = (
            univr_oriented_index
            .get(
                key,
                [],
            )
        )

        original = (
            univr_original_index
            .get(
                key,
                [],
            )
        )

        exact = (
            len(oriented) == 1
            and len(original) == 1
        )

        return {
            "status": (
                "EXACT_FILENAME_PAIR"
                if exact
                else "UNRESOLVED"
            ),

            "model_compatible_raw":
                oriented,

            "acquisition_original_raw":
                original,
        }


    if dataset == "KFALL":

        # Historical processed KFall subjects were offset by +100.
        raw_subject = (
            subject - 100
        )

        key = (
            raw_subject,
            task,
            trial,
        )

        oriented = (
            kfall_oriented_index
            .get(
                key,
                [],
            )
        )

        original = (
            kfall_original_index
            .get(
                key,
                [],
            )
        )

        exact = (
            raw_subject >= 0
            and len(oriented) == 1
            and len(original) == 1
        )

        return {
            "status": (
                "EXACT_FILENAME_PAIR"
                if exact
                else "UNRESOLVED"
            ),

            "raw_subject":
                raw_subject,

            "model_compatible_raw":
                oriented,

            "acquisition_original_raw":
                original,
        }


    if dataset == "ONFIELD":

        candidates = (
            onfield_index
            .get(
                subject,
                [],
            )
        )

        # Historical create_on_field assigned trial numbers from
        # filesystem processing order. Without a preserved mapping,
        # subject-level filename candidates are NOT declared exact.
        return {
            "status":
                "SUBJECT_CANDIDATES_ONLY",

            "candidate_count":
                len(candidates),

            "candidate_raw_paths":
                candidates[:50],

            "note": (
                "Trial-to-file mapping is not accepted as exact "
                "until processing-order/content lineage is recovered."
            ),
        }


    return {
        "status":
            "UNRESOLVED_DATASET",
    }


def main() -> None:

    if not SPLIT_MANIFEST.is_file():
        raise SystemExit(
            f"Missing frozen split manifest: "
            f"{SPLIT_MANIFEST}"
        )

    if not COMBINED.is_dir():
        raise SystemExit(
            f"Missing combined dataset root: "
            f"{COMBINED}"
        )


    split = json.loads(
        SPLIT_MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    split_subjects = {
        "train": set(
            split[
                "train_subjects"
            ]
        ),

        "validation": set(
            split[
                "validation_subjects"
            ]
        ),

        "test": set(
            split[
                "test_subjects"
            ]
        ),
    }


    # --------------------------------------------------------
    # Split invariants
    # --------------------------------------------------------

    if (
        split_subjects["train"]
        & split_subjects["validation"]
    ):
        raise RuntimeError(
            "Train/validation subject overlap"
        )

    if (
        split_subjects["train"]
        & split_subjects["test"]
    ):
        raise RuntimeError(
            "Train/test subject overlap"
        )

    if (
        split_subjects["validation"]
        & split_subjects["test"]
    ):
        raise RuntimeError(
            "Validation/test subject overlap"
        )


    subject_to_split = {}

    for split_name, subjects in (
        split_subjects.items()
    ):

        for subject in subjects:
            subject_to_split[
                str(subject)
            ] = split_name


    # --------------------------------------------------------
    # Raw indexes
    # --------------------------------------------------------

    print(
        "Building raw filename indexes...",
        flush=True,
    )

    univr_oriented_index = (
        build_trial_csv_index(
            UNIVR_ORIENTED_RAW
        )
    )

    univr_original_index = (
        build_trial_csv_index(
            UNIVR_ORIGINAL_RAW
        )
    )

    kfall_oriented_index = (
        build_trial_csv_index(
            KFALL_ORIENTED_RAW
        )
    )

    kfall_original_index = (
        build_trial_csv_index(
            KFALL_ORIGINAL_RAW
        )
    )

    onfield_index = (
        build_onfield_index(
            ONFIELD_RAW
        )
    )


    # --------------------------------------------------------
    # Canonical processed-source availability
    # --------------------------------------------------------

    print()
    print(
        "Canonical processed roots:"
    )

    for dataset, path in (
        CANONICAL_PROCESSED.items()
    ):
        print(
            f"  {dataset}: "
            f"{path} "
            f"exists={path.is_dir()}"
        )


    # --------------------------------------------------------
    # Discover other 400-ms trees for forensic context only
    # --------------------------------------------------------

    discovered_roots = []

    data_root = (
        OLD / "data"
    )

    for path in sorted(
        data_root.rglob(
            "400ms_50ov_npseg_filt_binary"
        )
    ):

        if path.is_dir():
            discovered_roots.append(
                str(path)
            )


    print()
    print(
        "Discovered 400-ms trees =",
        len(discovered_roots),
    )

    for path in discovered_roots:
        print(
            " ",
            path,
        )


    # --------------------------------------------------------
    # Inventory combined trials
    # --------------------------------------------------------

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


    print()
    print(
        "Combined trial directories =",
        len(trial_dirs),
    )


    records = []

    summary_split_dataset = Counter()
    summary_pairing = Counter()
    summary_source_resolution = Counter()
    subject_datasets = defaultdict(set)
    observed_subjects = set()

    split_window_counts = Counter()

    unresolved_examples = []
    ambiguous_examples = []

    augmentation_records = []
    augmentation_window_counts = Counter()
    augmentation_source_resolution = Counter()


    for i, trial_dir in enumerate(
        trial_dirs,
        start=1,
    ):

        rel = trial_dir.relative_to(
            COMBINED
        )

        if len(rel.parts) != 3:
            raise RuntimeError(
                "Expected combined layout "
                "subject/task/trial, got "
                f"{rel}"
            )

        subject_s, task_s, trial_s = (
            rel.parts
        )

        subject = int(
            subject_s
        )

        task = int(
            task_s
        )

        trial = int(
            trial_s
        )

        n_windows = (
            segment_window_count(
                trial_dir
                / "segments.npy"
            )
        )


        # ----------------------------------------------------
        # Historical augmentation-only streams
        # ----------------------------------------------------

        if subject_s in AUGMENTATION_ONLY_SUBJECTS:

            source_root = (
                CANONICAL_PROCESSED[
                    "ONFIELD"
                ]
            )

            source_dir = (
                source_root / rel
            )

            exact = False
            identity_mode = (
                "missing_files"
            )

            if source_dir.is_dir():

                exact, identity_mode = (
                    exact_pair_identity(
                        trial_dir,
                        source_dir,
                    )
                )


            source_status = (
                "EXACT_ONFIELD_AUGMENTATION_SOURCE"
                if exact
                else "UNRESOLVED_ONFIELD_AUGMENTATION_SOURCE"
            )

            augmentation_window_counts[
                subject_s
            ] += n_windows

            augmentation_source_resolution[
                source_status
            ] += 1

            raw = raw_pairing(
                "ONFIELD",
                subject,
                task,
                trial,
                univr_oriented_index=
                    univr_oriented_index,
                univr_original_index=
                    univr_original_index,
                kfall_oriented_index=
                    kfall_oriented_index,
                kfall_original_index=
                    kfall_original_index,
                onfield_index=
                    onfield_index,
            )

            augmentation_records.append(
                {
                    "role":
                        "historical_training_augmentation_only",

                    "subject":
                        subject_s,

                    "task":
                        task_s,

                    "trial":
                        trial_s,

                    "relative_trial":
                        str(rel),

                    "combined_dir":
                        str(
                            trial_dir
                        ),

                    "n_windows":
                        n_windows,

                    "processed_source_status":
                        source_status,

                    "source_dataset":
                        "ONFIELD",

                    "source_processed_dir":
                        (
                            str(source_dir)
                            if source_dir.is_dir()
                            else None
                        ),

                    "source_identity_mode":
                        identity_mode,

                    "raw_pairing":
                        raw,
                }
            )

            continue


        # ----------------------------------------------------
        # Frozen train/validation/test subjects
        # ----------------------------------------------------

        observed_subjects.add(
            subject_s
        )

        split_name = (
            subject_to_split.get(
                subject_s
            )
        )

        if split_name is None:

            raise RuntimeError(
                "Combined trial belongs to an unexpected subject "
                "that is neither in the frozen split nor declared "
                "historical augmentation-only: "
                f"{subject_s}"
            )


        split_window_counts[
            split_name
        ] += n_windows


        exact_sources = []
        candidate_checks = []


        for dataset, source_root in (
            CANONICAL_PROCESSED.items()
        ):

            source_dir = (
                source_root / rel
            )

            if not source_dir.is_dir():
                continue

            exact, mode = (
                exact_pair_identity(
                    trial_dir,
                    source_dir,
                )
            )

            candidate_checks.append(
                {
                    "dataset":
                        dataset,
                    "source_dir":
                        str(
                            source_dir
                        ),
                    "identity":
                        mode,
                    "exact":
                        exact,
                }
            )

            if exact:
                exact_sources.append(
                    (
                        dataset,
                        source_root,
                        source_dir,
                        mode,
                    )
                )


        if len(exact_sources) == 1:

            (
                dataset,
                source_root,
                source_dir,
                identity_mode,
            ) = exact_sources[0]

            source_status = (
                "EXACT_CANONICAL_SOURCE"
            )

            subject_datasets[
                subject_s
            ].add(
                dataset
            )


        elif len(exact_sources) == 0:

            dataset = "UNRESOLVED"
            source_root = None
            source_dir = None
            identity_mode = None

            source_status = (
                "NO_EXACT_CANONICAL_SOURCE"
            )

            if len(
                unresolved_examples
            ) < 30:
                unresolved_examples.append(
                    str(rel)
                )


        else:

            dataset = "AMBIGUOUS"
            source_root = None
            source_dir = None
            identity_mode = None

            source_status = (
                "MULTIPLE_EXACT_CANONICAL_SOURCES"
            )

            if len(
                ambiguous_examples
            ) < 30:
                ambiguous_examples.append(
                    {
                        "trial":
                            str(rel),
                        "sources": [
                            x[0]
                            for x in exact_sources
                        ],
                    }
                )


        raw = raw_pairing(
            dataset,
            subject,
            task,
            trial,
            univr_oriented_index=
                univr_oriented_index,
            univr_original_index=
                univr_original_index,
            kfall_oriented_index=
                kfall_oriented_index,
            kfall_original_index=
                kfall_original_index,
            onfield_index=
                onfield_index,
        )


        summary_split_dataset[
            (
                split_name,
                dataset,
            )
        ] += 1

        summary_pairing[
            (
                split_name,
                dataset,
                raw["status"],
            )
        ] += 1

        summary_source_resolution[
            source_status
        ] += 1


        records.append(
            {
                "split":
                    split_name,

                "subject":
                    subject_s,

                "task":
                    task_s,

                "trial":
                    trial_s,

                "relative_trial":
                    str(rel),

                "combined_dir":
                    str(
                        trial_dir
                    ),

                "n_windows":
                    n_windows,

                "processed_source_status":
                    source_status,

                "source_dataset":
                    dataset,

                "source_processed_root":
                    (
                        str(
                            source_root
                        )
                        if source_root
                        is not None
                        else None
                    ),

                "source_processed_dir":
                    (
                        str(
                            source_dir
                        )
                        if source_dir
                        is not None
                        else None
                    ),

                "source_identity_mode":
                    identity_mode,

                "candidate_source_checks":
                    candidate_checks,

                "raw_pairing":
                    raw,
            }
        )


        if (
            i % 500
        ) == 0:
            print(
                f"Processed "
                f"{i}/{len(trial_dirs)} "
                f"trials...",
                flush=True,
            )


    # --------------------------------------------------------
    # Global invariants
    # --------------------------------------------------------

    expected_subjects = set(
        subject_to_split
    )

    missing_subjects = sorted(
        expected_subjects
        - observed_subjects
    )

    unexpected_subjects = sorted(
        observed_subjects
        - expected_subjects
    )


    expected_windows = {
        split_name:
            int(
                split[
                    "preaugmentation_counts"
                ][
                    split_name
                ][
                    "total"
                ]
            )
        for split_name in (
            "train",
            "validation",
            "test",
        )
    }


    window_match = {
        name: (
            split_window_counts[name]
            == expected_windows[name]
        )
        for name in expected_windows
    }


    cross_dataset_subjects = {
        subject:
            sorted(datasets)
        for subject, datasets
        in subject_datasets.items()
        if len(datasets) != 1
    }


    # --------------------------------------------------------
    # Summary structure
    # --------------------------------------------------------

    split_dataset_rows = []

    for (
        split_name,
        dataset,
    ), count in sorted(
        summary_split_dataset.items()
    ):

        split_dataset_rows.append(
            {
                "split":
                    split_name,
                "dataset":
                    dataset,
                "trial_count":
                    count,
            }
        )


    pairing_rows = []

    for (
        split_name,
        dataset,
        status,
    ), count in sorted(
        summary_pairing.items()
    ):

        pairing_rows.append(
            {
                "split":
                    split_name,
                "dataset":
                    dataset,
                "raw_pairing_status":
                    status,
                "trial_count":
                    count,
            }
        )


    output = {
        "manifest_id":
            "RELIABILITY_TRIAL_INVENTORY_CANDIDATE_V1",

        "status":
            "candidate_read_only_lineage_inventory",

        "generation_policy": {
            "read_only_source_audit":
                True,

            "corruptions_applied":
                False,

            "thresholds_selected":
                False,

            "test_signal_values_used_for_tuning":
                False,

            "note": (
                "File identity and structural metadata only. "
                "No reliability operating point is selected."
            ),
        },

        "frozen_split_manifest":
            str(
                SPLIT_MANIFEST
            ),

        "combined_dataset_root":
            str(
                COMBINED
            ),

        "canonical_processed_roots": {
            k: str(v)
            for k, v
            in CANONICAL_PROCESSED.items()
        },

        "discovered_400ms_roots":
            discovered_roots,

        "split_subject_counts": {
            k: len(v)
            for k, v
            in split_subjects.items()
        },

        "expected_window_counts":
            expected_windows,

        "observed_window_counts": {
            k: int(
                split_window_counts[k]
            )
            for k in expected_windows
        },

        "window_count_matches_frozen_manifest":
            window_match,

        "observed_subject_count":
            len(
                observed_subjects
            ),

        "historical_training_augmentation": {
            "subjects":
                sorted(
                    AUGMENTATION_ONLY_SUBJECTS,
                    key=int,
                ),

            "trial_count":
                len(
                    augmentation_records
                ),

            "window_counts_by_subject": {
                subject:
                    int(
                        augmentation_window_counts[
                            subject
                        ]
                    )
                for subject in sorted(
                    AUGMENTATION_ONLY_SUBJECTS,
                    key=int,
                )
            },

            "total_windows":
                int(
                    sum(
                        augmentation_window_counts.values()
                    )
                ),

            "processed_source_resolution":
                dict(
                    augmentation_source_resolution
                ),

            "excluded_from_reliability_split":
                True,

            "records":
                augmentation_records,
        },

        "missing_frozen_subjects":
            missing_subjects,

        "unexpected_subjects":
            unexpected_subjects,

        "cross_dataset_subjects":
            cross_dataset_subjects,

        "processed_source_resolution":
            dict(
                summary_source_resolution
            ),

        "split_dataset_trial_counts":
            split_dataset_rows,

        "raw_pairing_counts":
            pairing_rows,

        "unresolved_examples":
            unresolved_examples,

        "ambiguous_examples":
            ambiguous_examples,

        "trials":
            records,
    }


    # Do NOT freeze the candidate unless core lineage invariants hold.
    if missing_subjects:
        raise RuntimeError(
            "Frozen subjects missing from combined dataset: "
            f"{missing_subjects}"
        )

    if unexpected_subjects:
        raise RuntimeError(
            "Unexpected combined subjects: "
            f"{unexpected_subjects}"
        )

    if not all(
        window_match.values()
    ):
        raise RuntimeError(
            "Combined split window counts do not reproduce "
            "the frozen baseline manifest: "
            f"observed={dict(split_window_counts)}, "
            f"expected={expected_windows}"
        )


    OUTPUT_JSON.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_JSON.write_text(
        json.dumps(
            output,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


    # --------------------------------------------------------
    # Concise stdout report
    # --------------------------------------------------------

    print()
    print(
        "=" * 80
    )

    print(
        "REAL TRIAL INVENTORY SUMMARY"
    )

    print(
        "=" * 80
    )

    print(
        "split_subject_counts =",
        {
            k: len(v)
            for k, v
            in split_subjects.items()
        },
    )

    print(
        "expected_window_counts =",
        expected_windows,
    )

    print(
        "observed_window_counts =",
        dict(
            split_window_counts
        ),
    )

    print(
        "WINDOW_COUNT_MATCH =",
        all(
            window_match.values()
        ),
    )

    print(
        "combined_trial_count =",
        len(records),
    )

    print()
    print(
        "historical training augmentation:"
    )

    print(
        " augmentation_subjects =",
        sorted(
            AUGMENTATION_ONLY_SUBJECTS,
            key=int,
        ),
    )

    print(
        " augmentation_trial_count =",
        len(
            augmentation_records
        ),
    )

    print(
        " augmentation_window_counts =",
        dict(
            augmentation_window_counts
        ),
    )

    print(
        " augmentation_total_windows =",
        int(
            sum(
                augmentation_window_counts.values()
            )
        ),
    )

    print(
        " augmentation_source_resolution =",
        dict(
            augmentation_source_resolution
        ),
    )


    print()
    print(
        "processed_source_resolution:"
    )

    for key, count in sorted(
        summary_source_resolution.items()
    ):
        print(
            " ",
            key,
            "=",
            count,
        )


    print()
    print(
        "split x dataset:"
    )

    for row in split_dataset_rows:
        print(
            " ",
            row,
        )


    print()
    print(
        "raw pairing:"
    )

    for row in pairing_rows:
        print(
            " ",
            row,
        )


    print()
    print(
        "subject -> exact source dataset:"
    )

    for subject in sorted(
        subject_datasets,
        key=lambda x: int(x),
    ):
        print(
            " ",
            subject,
            "->",
            sorted(
                subject_datasets[
                    subject
                ]
            ),
        )


    print()
    print(
        "missing_frozen_subjects =",
        missing_subjects,
    )

    print(
        "unexpected_subjects =",
        unexpected_subjects,
    )

    print(
        "cross_dataset_subjects =",
        cross_dataset_subjects,
    )

    print(
        "unresolved_examples =",
        unresolved_examples,
    )

    print(
        "ambiguous_examples =",
        ambiguous_examples,
    )

    print()
    print(
        "OUTPUT_JSON =",
        OUTPUT_JSON,
    )

    print(
        "REAL_TRIAL_INVENTORY_PASS =",
        (
            not missing_subjects
            and not unexpected_subjects
            and all(
                window_match.values()
            )
        ),
    )


if __name__ == "__main__":
    main()
