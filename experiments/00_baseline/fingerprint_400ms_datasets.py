from collections import defaultdict
from pathlib import Path
from math import ceil

import numpy as np
from sklearn.model_selection import train_test_split


ROOTS = [
    Path(
        "/mnt/hdd16T/protechto/data/"
        "KFall_oriented/segments/"
        "400ms_50ov_npseg_filt_binary"
    ),
    Path(
        "/mnt/hdd16T/protechto/data/"
        "UniVrFall_oriented/segments/"
        "400ms_50ov_npseg_filt_binary"
    ),
    Path(
        "/mnt/hdd16T/protechto/data/"
        "UniVrFall_KFall_OF/segments/"
        "400ms_50ov_npseg_filt_binary"
    ),
    Path(
        "/mnt/hdd16T/protechto/data/"
        "OnField/segments/"
        "400ms_50ov_npseg_filt_binary"
    ),
    Path(
        "/mnt/hdd16T/protechto/data/back/"
        "UniVrFall/segments/"
        "400ms_50ov_npseg_filt_binary"
    ),
    Path(
        "/mnt/hdd16T/protechto/data/back/"
        "UniVrFall_KFall/segments/"
        "400ms_50ov_npseg_filt_binary"
    ),
]

EXCLUDED = {"999", "1000"}

TARGET_GLOBAL_STEP = 702476
TARGET_EPOCH_INDEX = 60

# Assuming epochs 0..60 completed.
TARGET_STEPS_PER_EPOCH = (
    TARGET_GLOBAL_STEP // (TARGET_EPOCH_INDEX + 1)
)

print(
    "TARGET_STEPS_PER_EPOCH =",
    TARGET_STEPS_PER_EPOCH,
)

print(
    "DIVISION_EXACT =",
    TARGET_GLOBAL_STEP
    % (TARGET_EPOCH_INDEX + 1)
    == 0,
)


def segment_count(path: Path) -> int:
    arr = np.load(
        path,
        mmap_mode="r",
        allow_pickle=False,
    )

    if arr.ndim < 1:
        raise RuntimeError(
            f"Invalid segment array: {path}"
        )

    return int(arr.shape[0])


def inspect(root: Path):
    print()
    print("=" * 100)
    print(root)
    print("=" * 100)

    if not root.is_dir():
        print("MISSING")
        return

    subject_counts = defaultdict(int)

    for seg in root.rglob("segments.npy"):
        try:
            rel = seg.relative_to(root)
        except ValueError:
            continue

        if len(rel.parts) < 4:
            continue

        subject = rel.parts[0]

        try:
            n = segment_count(seg)
        except Exception as exc:
            print(
                "READ_ERROR",
                seg,
                repr(exc),
            )
            continue

        subject_counts[subject] += n

    subjects_all = sorted(
        subject_counts
    )

    subjects_model = [
        s
        for s in subjects_all
        if s not in EXCLUDED
        and not s.startswith(".")
    ]

    print(
        "subjects_all       =",
        len(subjects_all),
    )

    print(
        "subjects_model     =",
        len(subjects_model),
    )

    print(
        "total_windows      =",
        sum(subject_counts.values()),
    )

    for special in sorted(EXCLUDED):
        if special in subject_counts:
            print(
                f"special_subject_{special}_windows =",
                subject_counts[special],
            )

    if len(subjects_model) < 3:
        print("TOO_FEW_SUBJECTS_FOR_SPLIT")
        return

    # Matches the preserved TrainTestDataloader split semantics:
    # 20% subject test; then 10% of remaining subjects for validation.
    train_subjects, test_subjects = train_test_split(
        subjects_model,
        test_size=0.2,
        random_state=42,
    )

    train_subjects, val_subjects = train_test_split(
        train_subjects,
        test_size=0.1,
        random_state=42,
    )

    def windows(subjects):
        return sum(
            subject_counts[s]
            for s in subjects
        )

    n_train = windows(train_subjects)
    n_val = windows(val_subjects)
    n_test = windows(test_subjects)

    print(
        "train_subjects     =",
        len(train_subjects),
    )

    print(
        "val_subjects       =",
        len(val_subjects),
    )

    print(
        "test_subjects      =",
        len(test_subjects),
    )

    print(
        "train_windows_preaug =",
        n_train,
    )

    print(
        "val_windows          =",
        n_val,
    )

    print(
        "test_windows         =",
        n_test,
    )

    for batch_size in (64, 128):
        batches = ceil(
            n_train / batch_size
        )

        lo = (
            (TARGET_STEPS_PER_EPOCH - 1)
            * batch_size
            + 1
        )

        hi = (
            TARGET_STEPS_PER_EPOCH
            * batch_size
        )

        print()
        print(
            f"batch_size={batch_size}"
        )

        print(
            "  preaug_batches =",
            batches,
        )

        print(
            "  target_steps   =",
            TARGET_STEPS_PER_EPOCH,
        )

        print(
            "  exact_match    =",
            batches
            == TARGET_STEPS_PER_EPOCH,
        )

        print(
            "  target_N_range =",
            f"{lo}..{hi}",
        )

        print(
            "  delta_windows_to_range =",
            0
            if lo <= n_train <= hi
            else (
                lo - n_train
                if n_train < lo
                else n_train - hi
            ),
        )

    print()
    print(
        "TRAIN SUBJECT IDS =",
        ",".join(
            sorted(
                train_subjects,
                key=lambda x: (
                    int(x)
                    if x.isdigit()
                    else x
                ),
            )
        ),
    )

    print(
        "VAL SUBJECT IDS   =",
        ",".join(
            sorted(
                val_subjects,
                key=lambda x: (
                    int(x)
                    if x.isdigit()
                    else x
                ),
            )
        ),
    )

    print(
        "TEST SUBJECT IDS  =",
        ",".join(
            sorted(
                test_subjects,
                key=lambda x: (
                    int(x)
                    if x.isdigit()
                    else x
                ),
            )
        ),
    )


for root in ROOTS:
    inspect(root)
