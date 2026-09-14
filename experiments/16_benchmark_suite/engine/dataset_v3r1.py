from pathlib import Path
import json

import numpy as np
import torch

from torch.utils.data import (
    Dataset,
    TensorDataset,
    DataLoader,
)


class ReliabilityTrainingDataset(Dataset):

    def __init__(
        self,
        x,
        y,
        corruption_probability=0.3,
    ):
        self.x = x
        self.y = y
        self.p = float(corruption_probability)

    def __len__(self):
        return len(self.y)

    def __getitem__(self, index):

        clean = self.x[index]
        corrupt = clean.clone()

        if torch.rand(1).item() < self.p:

            channel = int(
                torch.randint(
                    low=0,
                    high=corrupt.shape[-1],
                    size=(1,),
                ).item()
            )

            corrupt[:, channel] = 0.0

        return (
            clean,
            corrupt,
            self.y[index],
        )


def _load_index(split_root, name):

    path = split_root / f"{name}_idx.npy"

    if not path.exists():
        raise FileNotFoundError(path)

    idx = np.load(path).astype(
        np.int64,
        copy=False,
    )

    if idx.ndim != 1:
        raise RuntimeError(
            f"{path}: split index must be 1-D"
        )

    if len(idx) == 0:
        raise RuntimeError(
            f"{path}: split is empty"
        )

    return idx


def _validate_indices(
    n,
    train_idx,
    val_idx,
    test_idx,
):

    splits = {
        "train": train_idx,
        "validation": val_idx,
        "test": test_idx,
    }

    for name, idx in splits.items():

        if len(np.unique(idx)) != len(idx):
            raise RuntimeError(
                f"Duplicate sample indices in {name}"
            )

        if idx.min() < 0 or idx.max() >= n:
            raise RuntimeError(
                f"Out-of-range sample index in {name}"
            )

    train_set = set(
        train_idx.tolist()
    )
    val_set = set(
        val_idx.tolist()
    )
    test_set = set(
        test_idx.tolist()
    )

    if train_set & val_set:
        raise RuntimeError(
            "Train/validation sample overlap"
        )

    if train_set & test_set:
        raise RuntimeError(
            "Train/test sample overlap"
        )

    if val_set & test_set:
        raise RuntimeError(
            "Validation/test sample overlap"
        )

    combined = (
        train_set |
        val_set |
        test_set
    )

    if combined != set(range(n)):
        raise RuntimeError(
            "Stored train/val/test splits "
            "do not cover the dataset exactly"
        )


def _validate_subjects(
    subjects,
    train_idx,
    val_idx,
    test_idx,
):

    train_subjects = set(
        subjects[train_idx].tolist()
    )
    val_subjects = set(
        subjects[val_idx].tolist()
    )
    test_subjects = set(
        subjects[test_idx].tolist()
    )

    if train_subjects & val_subjects:
        raise RuntimeError(
            "Train/validation SUBJECT overlap"
        )

    if train_subjects & test_subjects:
        raise RuntimeError(
            "Train/test SUBJECT overlap"
        )

    if val_subjects & test_subjects:
        raise RuntimeError(
            "Validation/test SUBJECT overlap"
        )

    return {
        "train": len(train_subjects),
        "validation": len(val_subjects),
        "test": len(test_subjects),
    }


def load_dataset_v3r1(
    dataset_name,
    batch_size=64,
    reliability_training=False,
    corruption_probability=0.3,
):

    data_root = (
        Path("data/processed/harmonized")
        /
        dataset_name
    )

    split_root = (
        Path("data/processed/splits")
        /
        dataset_name
    )

    x_path = data_root / "X.npy"
    y_path = data_root / "y.npy"
    subject_path = data_root / "subjects.npy"
    manifest_path = (
        split_root /
        "split_manifest.json"
    )

    for path in [
        x_path,
        y_path,
        subject_path,
        manifest_path,
    ]:
        if not path.exists():
            raise FileNotFoundError(path)

    X = np.load(
        x_path
    ).astype(
        np.float32,
        copy=False,
    )

    y_original = np.load(
        y_path
    )

    subjects = np.load(
        subject_path,
        allow_pickle=True,
    )

    if X.ndim != 3:
        raise RuntimeError(
            f"{dataset_name}: invalid X ndim "
            f"{X.ndim}"
        )

    if tuple(X.shape[1:]) != (128, 6):
        raise RuntimeError(
            f"{dataset_name}: expected "
            f"[N,128,6], got {X.shape}"
        )

    if y_original.ndim != 1:
        raise RuntimeError(
            f"{dataset_name}: y must be 1-D"
        )

    if len(X) != len(y_original):
        raise RuntimeError(
            f"{dataset_name}: X/y mismatch"
        )

    if len(subjects) != len(X):
        raise RuntimeError(
            f"{dataset_name}: subjects/X mismatch"
        )

    classes = np.unique(
        y_original
    )

    label_map = {
        value: index
        for index, value
        in enumerate(classes)
    }

    y = np.asarray(
        [
            label_map[value]
            for value in y_original
        ],
        dtype=np.int64,
    )

    train_idx = _load_index(
        split_root,
        "train",
    )

    val_idx = _load_index(
        split_root,
        "val",
    )

    test_idx = _load_index(
        split_root,
        "test",
    )

    _validate_indices(
        len(X),
        train_idx,
        val_idx,
        test_idx,
    )

    manifest = json.loads(
        manifest_path.read_text()
    )

    if (
        manifest.get("split_strategy")
        !=
        "subject_disjoint"
    ):
        raise RuntimeError(
            f"{dataset_name}: split manifest "
            "is not subject_disjoint"
        )

    subject_counts = _validate_subjects(
        subjects,
        train_idx,
        val_idx,
        test_idx,
    )

    train_raw = X[train_idx]

    mean = train_raw.mean(
        axis=(0, 1)
    )

    std = train_raw.std(
        axis=(0, 1)
    )

    std = np.where(
        std < 1e-8,
        1.0,
        std,
    ).astype(
        np.float32
    )

    def normalize(idx):

        return np.asarray(
            (
                X[idx]
                -
                mean
            )
            /
            std,
            dtype=np.float32,
        )

    X_train = normalize(
        train_idx
    )

    X_val = normalize(
        val_idx
    )

    X_test = normalize(
        test_idx
    )

    y_train = y[train_idx]
    y_val = y[val_idx]
    y_test = y[test_idx]

    train_x = torch.from_numpy(
        np.ascontiguousarray(
            X_train
        )
    )

    train_y = torch.from_numpy(
        np.ascontiguousarray(
            y_train
        )
    )

    if reliability_training:

        train_dataset = (
            ReliabilityTrainingDataset(
                train_x,
                train_y,
                corruption_probability,
            )
        )

    else:

        train_dataset = TensorDataset(
            train_x,
            train_y,
        )

    val_dataset = TensorDataset(
        torch.from_numpy(
            np.ascontiguousarray(
                X_val
            )
        ),
        torch.from_numpy(
            np.ascontiguousarray(
                y_val
            )
        ),
    )

    test_dataset = TensorDataset(
        torch.from_numpy(
            np.ascontiguousarray(
                X_test
            )
        ),
        torch.from_numpy(
            np.ascontiguousarray(
                y_test
            )
        ),
    )

    pin_memory = (
        torch.cuda.is_available()
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=int(batch_size),
        shuffle=True,
        num_workers=0,
        pin_memory=pin_memory,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=int(batch_size),
        shuffle=False,
        num_workers=0,
        pin_memory=pin_memory,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=int(batch_size),
        shuffle=False,
        num_workers=0,
        pin_memory=pin_memory,
    )

    summary = {
        "dataset": dataset_name,
        "samples": int(len(X)),
        "train_samples": int(len(train_idx)),
        "validation_samples": int(len(val_idx)),
        "test_samples": int(len(test_idx)),
        "num_classes": int(len(classes)),
        "input_shape": [128, 6],
        "split_strategy":
            "explicit_subject_disjoint",
        "normalization":
            "explicit_training_split_only",
        "subject_counts": subject_counts,
        "reliability_training":
            bool(reliability_training),
        "corruption_probability":
            float(corruption_probability)
            if reliability_training
            else 0.0,
        "normalization_mean":
            [float(v) for v in mean],
        "normalization_std":
            [float(v) for v in std],
        "split_manifest": manifest,
    }

    return {
        "train_loader": train_loader,
        "val_loader": val_loader,
        "test_loader": test_loader,
        "num_classes": int(
            len(classes)
        ),
        "summary": summary,
    }
