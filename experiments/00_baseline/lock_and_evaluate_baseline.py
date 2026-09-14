from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

from imu_reliability.baseline.date2025_cnn400 import Date2025CNN400


PROJECT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

DATA = Path(
    "/mnt/hdd16T/protechto/data/back/"
    "UniVrFall_KFall/segments/"
    "400ms_50ov_npseg_filt_binary"
)

ONFIELD = Path(
    "/mnt/hdd16T/protechto/data/OnField/"
    "segments/400ms_50ov_npseg_filt_binary"
)

CKPT = Path(
    "/mnt/hdd16T/protechto/checkpoints/CNN/400ms/"
    "2025-02-25_12_24_47/best-checkpoint.ckpt"
)

EXPECTED_CKPT_SHA = (
    "ee7c0079bfb8555bff45c3077cc24eaa"
    "4373c57729045d92a831a1d7a3ea9bb1"
)

BATCH_SIZE = 64
TARGET_STEPS = 11516

AUGMENTATION_SUBJECTS = {"999", "1000"}

MANIFEST_OUT = (
    PROJECT
    / "data/manifests/"
      "date2025_cnn400_inferred_split_v1.json"
)

METRICS_OUT = (
    PROJECT
    / "results/raw/baseline/"
      "date2025_cnn400_clean_metrics_v1.json"
)

PRED_OUT = (
    PROJECT
    / "results/raw/baseline/"
      "date2025_cnn400_clean_predictions_v1.csv"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def subject_dirs(root: Path):
    return sorted(
        [
            p
            for p in root.iterdir()
            if p.is_dir()
            and p.name not in AUGMENTATION_SUBJECTS
            and not p.name.startswith(".")
        ],
        key=lambda p: p.name,
    )


def find_pairs(subject_dir: Path):
    """
    Historical layout contains task/recording subdirectories with
    segments.npy + labels.npy. Pair by common parent.
    """

    pairs = []

    for seg in sorted(
        subject_dir.rglob("segments.npy")
    ):
        lab = seg.with_name("labels.npy")

        if not lab.exists():
            raise RuntimeError(
                f"Missing labels for {seg}"
            )

        pairs.append((seg, lab))

    return pairs


def normalize_label(value):
    """
    Preserve historical binary semantics.
    """
    if isinstance(value, bytes):
        value = value.decode()

    if isinstance(value, np.generic):
        value = value.item()

    text = str(value).strip()

    if text == "Activity":
        return 0

    if text == "Falling":
        return 1

    # Some saved arrays may already be integer encoded.
    if text in {"0", "0.0"}:
        return 0

    if text in {"1", "1.0"}:
        return 1

    raise ValueError(
        f"Unknown historical label: {value!r}"
    )


def count_subject(subject_dir: Path):
    total = 0
    classes = Counter()

    for seg_path, lab_path in find_pairs(
        subject_dir
    ):
        x = np.load(
            seg_path,
            mmap_mode="r",
            allow_pickle=False,
        )

        y = np.load(
            lab_path,
            allow_pickle=True,
        )

        if len(x) != len(y):
            raise RuntimeError(
                f"Length mismatch: {seg_path}"
            )

        total += len(y)

        for value, n in zip(
            *np.unique(
                y,
                return_counts=True,
            )
        ):
            classes[
                normalize_label(value)
            ] += int(n)

    return {
        "total": total,
        "activity": classes[0],
        "falling": classes[1],
    }


def count_named_subjects(
    root: Path,
    names,
):
    out = Counter()

    details = {}

    for name in names:
        d = root / str(name)

        stats = count_subject(d)

        details[str(name)] = stats

        out["total"] += stats["total"]
        out["activity"] += stats["activity"]
        out["falling"] += stats["falling"]

    return dict(out), details


# ------------------------------------------------------------
# 1. Reproduce historical subject split
# ------------------------------------------------------------

subjects = [
    p.name
    for p in subject_dirs(DATA)
]

train_subjects, test_subjects = (
    train_test_split(
        subjects,
        test_size=0.2,
        random_state=42,
    )
)

train_subjects, val_subjects = (
    train_test_split(
        train_subjects,
        test_size=0.1,
        random_state=42,
    )
)

train_subjects = list(train_subjects)
val_subjects = list(val_subjects)
test_subjects = list(test_subjects)

print("SUBJECT COUNTS")
print("train =", len(train_subjects))
print("val   =", len(val_subjects))
print("test  =", len(test_subjects))

print()
print(
    "TRAIN =",
    ",".join(sorted(train_subjects)),
)

print(
    "VAL   =",
    ",".join(sorted(val_subjects)),
)

print(
    "TEST  =",
    ",".join(sorted(test_subjects)),
)


# ------------------------------------------------------------
# 2. Exact class counts
# ------------------------------------------------------------

train_stats, train_detail = (
    count_named_subjects(
        DATA,
        train_subjects,
    )
)

val_stats, val_detail = (
    count_named_subjects(
        DATA,
        val_subjects,
    )
)

test_stats, test_detail = (
    count_named_subjects(
        DATA,
        test_subjects,
    )
)

augmentation_stats, augmentation_detail = (
    count_named_subjects(
        ONFIELD,
        ["999", "1000"],
    )
)

print()
print("CLASS COUNTS")

print(
    "train_preaug =",
    train_stats,
)

print(
    "validation   =",
    val_stats,
)

print(
    "test         =",
    test_stats,
)

print(
    "onfield_999_1000 =",
    augmentation_stats,
)


# ------------------------------------------------------------
# 3. Historical augmentation/global-step fingerprint
# ------------------------------------------------------------

augmented_train_windows = (
    train_stats["total"]
    + 2 * train_stats["falling"]
    + augmentation_stats["total"]
)

calculated_steps = math.ceil(
    augmented_train_windows
    / BATCH_SIZE
)

print()
print("GLOBAL-STEP FINGERPRINT")

print(
    "falling_train_windows =",
    train_stats["falling"],
)

print(
    "augmented_train_windows =",
    augmented_train_windows,
)

print(
    "batch_size =",
    BATCH_SIZE,
)

print(
    "calculated_steps_per_epoch =",
    calculated_steps,
)

print(
    "checkpoint_steps_per_epoch =",
    TARGET_STEPS,
)

print(
    "STEP_MATCH =",
    calculated_steps == TARGET_STEPS,
)


# ------------------------------------------------------------
# 4. Load frozen protected model
# ------------------------------------------------------------

actual_sha = sha256(CKPT)

if actual_sha != EXPECTED_CKPT_SHA:
    raise RuntimeError(
        "Protected checkpoint SHA mismatch."
    )

ckpt = torch.load(
    CKPT,
    map_location="cpu",
    weights_only=False,
)

state = {
    k.removeprefix("model."): v
    for k, v in ckpt["state_dict"].items()
    if k.startswith("model.")
}

model = Date2025CNN400()

model.load_state_dict(
    state,
    strict=True,
)

model.eval()


# ------------------------------------------------------------
# 5. Streaming clean inference
# ------------------------------------------------------------

def evaluate_subjects(
    split_name: str,
    names,
    prediction_writer,
):
    y_true = []
    y_pred = []

    # For reliability work we retain logits/probabilities,
    # but do not alter the historical task decision here.
    probabilities_fall = []

    for subject in names:
        subject_dir = DATA / subject

        for seg_path, lab_path in find_pairs(
            subject_dir
        ):
            x = np.load(
                seg_path,
                mmap_mode="r",
                allow_pickle=False,
            )

            y_raw = np.load(
                lab_path,
                allow_pickle=True,
            )

            y = np.asarray(
                [
                    normalize_label(v)
                    for v in y_raw
                ],
                dtype=np.int64,
            )

            if (
                x.ndim != 3
                or x.shape[1:] != (40, 9)
            ):
                raise RuntimeError(
                    f"Unexpected shape "
                    f"{x.shape}: {seg_path}"
                )

            local_predictions = []

            for start in range(
                0,
                len(x),
                2048,
            ):
                end = min(
                    start + 2048,
                    len(x),
                )

                xb = torch.from_numpy(
                    np.asarray(
                        x[start:end],
                        dtype=np.float32,
                    )
                )

                with torch.inference_mode():
                    logits, features = (
                        model.forward_with_features(
                            xb
                        )
                    )

                    probs = torch.softmax(
                        logits,
                        dim=1,
                    )

                    pred = logits.argmax(
                        dim=1
                    )

                pred_np = (
                    pred.cpu()
                    .numpy()
                    .astype(np.int64)
                )

                prob_fall_np = (
                    probs[:, 1]
                    .cpu()
                    .numpy()
                )

                y_true.extend(
                    y[start:end].tolist()
                )

                y_pred.extend(
                    pred_np.tolist()
                )

                probabilities_fall.extend(
                    prob_fall_np.tolist()
                )

                for offset in range(
                    end - start
                ):
                    prediction_writer.writerow(
                        [
                            split_name,
                            subject,
                            str(
                                seg_path.relative_to(
                                    DATA
                                )
                            ),
                            start + offset,
                            int(
                                y[start + offset]
                            ),
                            int(
                                pred_np[offset]
                            ),
                            float(
                                prob_fall_np[offset]
                            ),
                        ]
                    )

    y_true = np.asarray(
        y_true,
        dtype=np.int64,
    )

    y_pred = np.asarray(
        y_pred,
        dtype=np.int64,
    )

    cm = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1],
    )

    return {
        "n_windows": int(len(y_true)),
        "confusion_matrix": cm.tolist(),
        "accuracy": float(
            accuracy_score(
                y_true,
                y_pred,
            )
        ),
        "macro_precision": float(
            precision_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),
        "macro_recall": float(
            recall_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),
        "macro_f1": float(
            f1_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),
        "fall_precision": float(
            precision_score(
                y_true,
                y_pred,
                pos_label=1,
                zero_division=0,
            )
        ),
        "fall_recall": float(
            recall_score(
                y_true,
                y_pred,
                pos_label=1,
                zero_division=0,
            )
        ),
        "fall_f1": float(
            f1_score(
                y_true,
                y_pred,
                pos_label=1,
                zero_division=0,
            )
        ),
        "fall_false_negative_rate": float(
            (
                cm[1, 0]
                / cm[1].sum()
            )
            if cm[1].sum()
            else 0.0
        ),
    }


PRED_OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

with PRED_OUT.open(
    "w",
    newline="",
) as f:
    writer = csv.writer(f)

    writer.writerow(
        [
            "split",
            "subject",
            "source_file",
            "window_index",
            "y_true",
            "y_pred",
            "fall_probability",
        ]
    )

    print()
    print("RUNNING VALIDATION INFERENCE...")

    validation_metrics = (
        evaluate_subjects(
            "validation",
            val_subjects,
            writer,
        )
    )

    print(
        "VALIDATION METRICS =",
        json.dumps(
            validation_metrics,
            indent=2,
        ),
    )

    print()
    print("RUNNING TEST INFERENCE...")

    test_metrics = (
        evaluate_subjects(
            "test",
            test_subjects,
            writer,
        )
    )

    print(
        "TEST METRICS =",
        json.dumps(
            test_metrics,
            indent=2,
        ),
    )


# ------------------------------------------------------------
# 6. Freeze inferred historical split manifest
# ------------------------------------------------------------

manifest = {
    "manifest_id":
        "DATE2025_CNN400_INFERRED_SPLIT_V1",

    "status":
        (
            "step_count_confirmed_candidate"
            if calculated_steps
            == TARGET_STEPS
            else
            "step_count_not_confirmed"
        ),

    "dataset_root":
        str(DATA),

    "split_algorithm": {
        "subject_sort":
            "lexicographic",

        "test":
            "sklearn train_test_split("
            "test_size=0.2, random_state=42)",

        "validation":
            "train_test_split("
            "remaining_train, "
            "test_size=0.1, "
            "random_state=42)",
    },

    "train_subjects":
        sorted(train_subjects),

    "validation_subjects":
        sorted(val_subjects),

    "test_subjects":
        sorted(test_subjects),

    "preaugmentation_counts": {
        "train": train_stats,
        "validation": val_stats,
        "test": test_stats,
    },

    "augmentation": {
        "falling_timewarp_copies":
            2,

        "onfield_subjects":
            ["999", "1000"],

        "onfield_counts":
            augmentation_stats,

        "augmented_train_windows":
            augmented_train_windows,
    },

    "training_fingerprint": {
        "checkpoint_epoch":
            60,

        "checkpoint_global_step":
            702476,

        "inferred_completed_epochs":
            61,

        "checkpoint_steps_per_epoch":
            TARGET_STEPS,

        "batch_size":
            BATCH_SIZE,

        "calculated_steps_per_epoch":
            calculated_steps,

        "step_match":
            calculated_steps
            == TARGET_STEPS,
    },

    "checkpoint": {
        "path":
            str(CKPT),

        "sha256":
            actual_sha,
    },

    "provenance_note":
        (
            "This split is inferred from surviving "
            "dataset contents, preserved loader "
            "semantics, augmentation semantics, and "
            "checkpoint optimizer-step count. "
            "It is not claimed as byte-for-byte "
            "proof of the lost deployment build."
        ),
}

MANIFEST_OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

MANIFEST_OUT.write_text(
    json.dumps(
        manifest,
        indent=2,
    )
    + "\n"
)


metrics = {
    "baseline_id":
        "DATE2025_CNN_400MS_CANDIDATE_V1",

    "checkpoint_sha256":
        actual_sha,

    "dataset_manifest":
        str(MANIFEST_OUT),

    "decision_rule":
        "argmax_logits",

    "validation":
        validation_metrics,

    "test":
        test_metrics,
}

METRICS_OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

METRICS_OUT.write_text(
    json.dumps(
        metrics,
        indent=2,
    )
    + "\n"
)


print()
print("ARTIFACTS")

print(
    "manifest =",
    MANIFEST_OUT,
)

print(
    "metrics  =",
    METRICS_OUT,
)

print(
    "preds    =",
    PRED_OUT,
)

print()
print(
    "BASELINE_LINEAGE_LOCK =",
    (
        "PASS"
        if calculated_steps
        == TARGET_STEPS
        else
        "UNRESOLVED"
    ),
)
