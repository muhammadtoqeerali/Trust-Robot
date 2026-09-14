from pathlib import Path
import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import time

import numpy as np
import torch
import torch.nn as nn
import yaml

from sklearn.metrics import f1_score


ROOT = Path(
    __file__
).resolve().parent

PROJECT_ROOT = (
    ROOT.parents[1]
)

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from engine.dataset_v3r1 import (
    load_dataset_v3r1
)

from engine.model_registry import (
    create_model,
    load_model_registry,
)

from engine.model_forward import (
    model_forward
)

from engine.evaluator import (
    evaluate_model
)

from engine.reproducibility import (
    set_seed
)

from engine.reliability_runner_v2 import (
    run_reliability_evaluation_v2
)


DATASETS = [
    "UCI_HAR",
    "PAMAP2",
    "DSADS",
    "MotionSense",
]

EXPECTED = {
    "UCI_HAR": {
        "classes": 6,
        "train": 5817,
        "validation": 2196,
        "test": 2286,
    },
    "PAMAP2": {
        "classes": 12,
        "train": 18609,
        "validation": 7542,
        "test": 4192,
    },
    "DSADS": {
        "classes": 19,
        "train": 4560,
        "validation": 2280,
        "test": 2280,
    },
    "MotionSense": {
        "classes": 6,
        "train": 12370,
        "validation": 4809,
        "test": 4349,
    },
}

MODELS = [
    "ReliabilityCNN_v22",
    "CNN1D",
    "LSTM",
    "DeepConvLSTM",
    "Transformer",
    "ReliabilityCNN_v24",
    "DS_CNN",
    "TCN",
    "TinyTransformer",
]

MODEL_CONFIGS = {
    "ReliabilityCNN_v22":
        "reliability_cnn_v22.yaml",
    "CNN1D":
        "cnn1d.yaml",
    "LSTM":
        "lstm.yaml",
    "DeepConvLSTM":
        "deepconv_lstm.yaml",
    "Transformer":
        "transformer.yaml",
    "ReliabilityCNN_v24":
        "reliability_cnn_v24.yaml",
    "DS_CNN":
        "ds_cnn.yaml",
    "TCN":
        "tcn.yaml",
    "TinyTransformer":
        "tiny_transformer.yaml",
}

SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]

CONFIG_ROOT = (
    ROOT /
    "configs"
)

RESULT_ROOT = Path(
    "results/benchmark_v3r1"
)

RAW_ROOT = (
    RESULT_ROOT /
    "raw_runs"
)

RELIABILITY_ROOT = (
    RESULT_ROOT /
    "reliability_v2"
)

PROTOCOL_ROOT = (
    RESULT_ROOT /
    "protocol"
)

PREFLIGHT_MARKER = (
    RESULT_ROOT /
    "PREFLIGHT_PASS"
)

PROTOCOL_MANIFEST = (
    PROTOCOL_ROOT /
    "protocol_manifest.json"
)

CORRUPTION_SOURCE = Path(
    "configs/reliability/"
    "corruption_registry_v2.json"
)

FROZEN_CORRUPTION = (
    PROTOCOL_ROOT /
    "corruption_registry_v2.json"
)


def json_safe(value):

    if isinstance(
        value,
        Path,
    ):
        return str(value)

    if isinstance(
        value,
        np.generic,
    ):
        return value.item()

    if isinstance(
        value,
        np.ndarray,
    ):
        return value.tolist()

    if isinstance(
        value,
        torch.Tensor,
    ):
        return (
            value
            .detach()
            .cpu()
            .tolist()
        )

    if isinstance(
        value,
        dict,
    ):
        return {
            str(k): json_safe(v)
            for k, v
            in value.items()
        }

    if isinstance(
        value,
        (list, tuple),
    ):
        return [
            json_safe(v)
            for v in value
        ]

    return value


def save_json(path, data):

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            json_safe(data),
            indent=2,
            sort_keys=True,
        )
    )

    temporary.replace(path)


def sha256_file(path):

    path = Path(path)

    h = hashlib.sha256()

    with path.open("rb") as f:

        while True:

            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def git_head():

    try:

        return subprocess.check_output(
            [
                "git",
                "rev-parse",
                "HEAD",
            ],
            text=True,
        ).strip()

    except Exception:

        return "unknown"


def deep_merge(base, override):

    result = copy.deepcopy(base)

    for key, value in (
        override or {}
    ).items():

        if (
            isinstance(value, dict)
            and
            isinstance(
                result.get(key),
                dict,
            )
        ):
            result[key] = deep_merge(
                result[key],
                value,
            )

        else:
            result[key] = copy.deepcopy(
                value
            )

    return result


def load_config(
    model_name,
    dataset_name,
    seed,
):

    default_path = (
        CONFIG_ROOT /
        "experiments" /
        "benchmark_default.yaml"
    )

    model_path = (
        CONFIG_ROOT /
        "UCI_HAR" /
        MODEL_CONFIGS[
            model_name
        ]
    )

    if not default_path.exists():
        raise FileNotFoundError(
            default_path
        )

    if not model_path.exists():
        raise FileNotFoundError(
            model_path
        )

    default_cfg = yaml.safe_load(
        default_path.read_text()
    )

    model_cfg = yaml.safe_load(
        model_path.read_text()
    )

    cfg = deep_merge(
        default_cfg,
        model_cfg,
    )

    cfg.setdefault(
        "dataset",
        {},
    )

    cfg.setdefault(
        "training",
        {},
    )

    cfg.setdefault(
        "augmentation",
        {},
    )

    cfg["dataset"]["name"] = (
        dataset_name
    )

    cfg["training"]["seed"] = int(
        seed
    )

    cfg.setdefault(
        "experiment",
        {},
    )

    cfg["experiment"]["name"] = (
        f"benchmark_v3r1_"
        f"{dataset_name}_"
        f"{model_name}_"
        f"seed_{seed}"
    )

    return cfg


def unpack_output(output):

    if isinstance(
        output,
        (tuple, list),
    ):

        logits = output[0]

        feature = (
            output[1]
            if len(output) > 1
            else None
        )

        return logits, feature

    return output, None


def evaluate_basic(
    model,
    loader,
    device,
):

    model.eval()

    predictions = []
    labels = []

    with torch.no_grad():

        for batch in loader:

            x = batch[0].to(
                device,
                non_blocking=True,
            )

            y = batch[1].to(
                device,
                non_blocking=True,
            )

            raw = model_forward(
                model,
                x,
            )

            logits, _ = unpack_output(
                raw
            )

            prediction = logits.argmax(
                dim=1
            )

            predictions.extend(
                prediction
                .detach()
                .cpu()
                .tolist()
            )

            labels.extend(
                y.detach()
                .cpu()
                .tolist()
            )

    accuracy = float(
        np.mean(
            np.asarray(predictions)
            ==
            np.asarray(labels)
        )
    )

    macro_f1 = float(
        f1_score(
            labels,
            predictions,
            average="macro",
            zero_division=0,
        )
    )

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
    }


def load_state(path, device):

    try:

        return torch.load(
            path,
            map_location=device,
            weights_only=True,
        )

    except TypeError:

        return torch.load(
            path,
            map_location=device,
        )


def save_cpu_state(
    model,
    path,
):

    state = {
        key:
            value.detach().cpu()
        for key, value
        in model.state_dict().items()
    }

    torch.save(
        state,
        path,
    )


def archive_partial(
    path,
    category,
):

    path = Path(path)

    if not path.exists():
        return

    if (
        path.is_dir()
        and
        not any(path.iterdir())
    ):
        path.rmdir()
        return

    stamp = (
        time.strftime(
            "%Y%m%d_%H%M%S"
        )
        +
        "_"
        +
        str(time.time_ns())
    )

    try:
        relative = path.relative_to(
            RESULT_ROOT
        )
    except ValueError:
        relative = Path(
            path.name
        )

    destination = (
        RESULT_ROOT /
        "_partial_archive" /
        category /
        stamp /
        relative
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.move(
        str(path),
        str(destination),
    )

    print(
        "PARTIAL_ARCHIVED:",
        path,
        "->",
        destination,
        flush=True,
    )


def critical_files():

    paths = [
        ROOT /
        "run_benchmark_v3r1.py",

        ROOT /
        "engine" /
        "dataset_v3r1.py",

        ROOT /
        "engine" /
        "model_registry.py",

        ROOT /
        "engine" /
        "model_forward.py",

        ROOT /
        "engine" /
        "evaluator.py",

        ROOT /
        "engine" /
        "reproducibility.py",

        ROOT /
        "engine" /
        "reliability_runner_v2.py",

        ROOT /
        "engine" /
        "reliability_dataset_v2.py",

        ROOT /
        "engine" /
        "corruption_engine_v2.py",

        CONFIG_ROOT /
        "experiments" /
        "benchmark_default.yaml",

        ROOT /
        "registry" /
        "models.yaml",

        CORRUPTION_SOURCE,
    ]

    registry = load_model_registry()

    for model_name in MODELS:

        paths.append(
            CONFIG_ROOT /
            "UCI_HAR" /
            MODEL_CONFIGS[
                model_name
            ]
        )

        entry = registry[
            model_name
        ]

        module_name = entry[
            "module"
        ]

        if module_name.startswith(
            "models."
        ):

            source = (
                PROJECT_ROOT /
                (
                    module_name.replace(
                        ".",
                        "/",
                    )
                    +
                    ".py"
                )
            )

        else:

            source = (
                ROOT /
                "models" /
                f"{module_name}.py"
            )

        paths.append(source)

    for dataset_name in DATASETS:

        data_root = (
            Path(
                "data/processed/harmonized"
            )
            /
            dataset_name
        )

        split_root = (
            Path(
                "data/processed/splits"
            )
            /
            dataset_name
        )

        paths.extend([
            data_root / "X.npy",
            data_root / "y.npy",
            data_root / "subjects.npy",
            split_root / "train_idx.npy",
            split_root / "val_idx.npy",
            split_root / "test_idx.npy",
            split_root / "split_manifest.json",
        ])

    unique = []

    seen = set()

    for path in paths:

        path = Path(path)

        key = str(path)

        if key in seen:
            continue

        seen.add(key)

        if not path.exists():
            raise FileNotFoundError(
                path
            )

        unique.append(path)

    return unique


def preflight():

    print(
        "=" * 72
    )
    print(
        "BENCHMARK V3R1 PREFLIGHT"
    )
    print(
        "=" * 72
    )

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is unavailable in "
            "controlled Python"
        )

    print(
        "PYTHON=",
        sys.version.replace(
            "\n",
            " ",
        )
    )

    print(
        "TORCH=",
        torch.__version__,
    )

    print(
        "CUDA_DEVICE_COUNT=",
        torch.cuda.device_count(),
    )

    for index in range(
        torch.cuda.device_count()
    ):

        print(
            f"GPU_{index}=",
            torch.cuda.get_device_name(
                index
            ),
        )

    print()
    print(
        "DATASET_PREFLIGHT"
    )

    for dataset_name in DATASETS:

        data = load_dataset_v3r1(
            dataset_name,
            batch_size=64,
            reliability_training=False,
        )

        summary = data[
            "summary"
        ]

        expected = EXPECTED[
            dataset_name
        ]

        observed = {
            "classes":
                data[
                    "num_classes"
                ],
            "train":
                summary[
                    "train_samples"
                ],
            "validation":
                summary[
                    "validation_samples"
                ],
            "test":
                summary[
                    "test_samples"
                ],
        }

        if observed != expected:
            raise RuntimeError(
                f"{dataset_name}: "
                f"expected={expected} "
                f"observed={observed}"
            )

        print(
            "DATASET_PASS:",
            dataset_name,
            observed,
            "subjects=",
            summary[
                "subject_counts"
            ],
        )

        del data

    print()
    print(
        "CONFIG_PREFLIGHT"
    )

    for model_name in MODELS:

        cfg = load_config(
            model_name,
            "UCI_HAR",
            42,
        )

        training = cfg[
            "training"
        ]

        epochs = int(
            training.get(
                "epochs",
                100,
            )
        )

        batch_size = int(
            training.get(
                "batch_size",
                64,
            )
        )

        learning_rate = float(
            training.get(
                "learning_rate",
                0.001,
            )
        )

        optimizer = str(
            training.get(
                "optimizer",
                "Adam",
            )
        )

        if epochs != 100:
            raise RuntimeError(
                f"{model_name}: "
                f"epochs={epochs}, expected 100"
            )

        if batch_size != 64:
            raise RuntimeError(
                f"{model_name}: "
                f"batch_size={batch_size}, "
                "expected 64"
            )

        if abs(
            learning_rate - 0.001
        ) > 1e-12:
            raise RuntimeError(
                f"{model_name}: "
                f"learning_rate="
                f"{learning_rate}"
            )

        if optimizer.lower() != "adam":
            raise RuntimeError(
                f"{model_name}: "
                f"optimizer={optimizer}"
            )

        print(
            "CONFIG_PASS:",
            model_name,
            "reliability_training=",
            bool(
                cfg[
                    "augmentation"
                ].get(
                    "reliability_training",
                    False,
                )
            ),
        )

    print()
    print(
        "MODEL_FORWARD_PREFLIGHT"
    )

    with torch.no_grad():

        for dataset_name in DATASETS:

            classes = EXPECTED[
                dataset_name
            ][
                "classes"
            ]

            x = torch.zeros(
                2,
                128,
                6,
            )

            for model_name in MODELS:

                model = create_model(
                    model_name,
                    classes,
                    input_channels=6,
                )

                model.eval()

                raw = model_forward(
                    model,
                    x,
                )

                logits, _ = unpack_output(
                    raw
                )

                if tuple(
                    logits.shape
                ) != (
                    2,
                    classes,
                ):
                    raise RuntimeError(
                        f"Forward contract failed: "
                        f"{dataset_name}/"
                        f"{model_name}/"
                        f"{tuple(logits.shape)}"
                    )

                print(
                    "MODEL_PASS:",
                    dataset_name,
                    model_name,
                    tuple(
                        logits.shape
                    ),
                )

                del model

    if not CORRUPTION_SOURCE.exists():
        raise FileNotFoundError(
            CORRUPTION_SOURCE
        )

    corruption_registry = json.loads(
        CORRUPTION_SOURCE.read_text()
    )

    if (
        corruption_registry.get(
            "version"
        )
        !=
        "v2"
    ):
        raise RuntimeError(
            "Corruption registry is "
            "not Reliability V2"
        )

    required_families = {
        "missing_channel",
        "random_dropout",
        "gaussian_noise",
        "sensor_drift",
    }

    available_families = set(
        corruption_registry.get(
            "corruptions",
            {}
        )
    )

    if not required_families.issubset(
        available_families
    ):
        raise RuntimeError(
            "Reliability V2 registry "
            "is missing required families"
        )

    print(
        "RELIABILITY_V2_REGISTRY_PASS=True"
    )

    print()
    print(
        "HASHING_PROTOCOL_INPUTS"
    )

    hashes = {}

    for path in critical_files():

        digest = sha256_file(
            path
        )

        hashes[
            str(path)
        ] = digest

        print(
            "HASH_PASS:",
            path,
            digest,
        )

    manifest = {
        "protocol":
            "benchmark_v3r1_multidataset",
        "git_head":
            git_head(),
        "datasets":
            DATASETS,
        "models":
            MODELS,
        "excluded_model":
            "ReliabilityCNN_v23",
        "seeds":
            SEEDS,
        "training_run_count":
            len(DATASETS)
            *
            len(MODELS)
            *
            len(SEEDS),
        "input_contract":
            "[N,128,6]",
        "split_protocol":
            "stored explicit subject-disjoint "
            "train/validation/test",
        "normalization":
            "explicit training split only",
        "config_policy":
            "same UCI_HAR per-model config "
            "template reused across datasets; "
            "dataset name and seed overridden",
        "epochs":
            100,
        "batch_size":
            64,
        "optimizer":
            "Adam",
        "learning_rate":
            0.001,
        "model_selection":
            "highest validation macro-F1 "
            "across 100 epochs",
        "reliability_training_semantics":
            "clean classification loss plus "
            "feature consistency when model "
            "exposes a second output; paired "
            "single-channel outage augmentation",
        "reliability_evaluation":
            "Reliability Protocol V2 on CUDA",
        "result_namespace":
            str(RESULT_ROOT),
        "hashes":
            hashes,
    }

    PROTOCOL_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    if PROTOCOL_MANIFEST.exists():

        previous = json.loads(
            PROTOCOL_MANIFEST.read_text()
        )

        if (
            previous.get("hashes")
            !=
            manifest["hashes"]
        ):
            raise RuntimeError(
                "Existing benchmark_v3r1 "
                "protocol hashes differ. "
                "Use a new revision namespace "
                "instead of mixing lineages."
            )

        if not FROZEN_CORRUPTION.exists():
            raise RuntimeError(
                "Protocol manifest exists "
                "but frozen corruption "
                "registry is missing"
            )

        if (
            sha256_file(
                FROZEN_CORRUPTION
            )
            !=
            sha256_file(
                CORRUPTION_SOURCE
            )
        ):
            raise RuntimeError(
                "Frozen Reliability V2 "
                "registry differs from source"
            )

        print(
            "PROTOCOL_MANIFEST_REUSED=True"
        )

    else:

        shutil.copy2(
            CORRUPTION_SOURCE,
            FROZEN_CORRUPTION,
        )

        save_json(
            PROTOCOL_MANIFEST,
            manifest,
        )

        print(
            "PROTOCOL_MANIFEST_CREATED=True"
        )

    PREFLIGHT_MARKER.write_text(
        "BENCHMARK_V3R1_PREFLIGHT_PASS=True\n"
    )

    print()
    print(
        "BENCHMARK_V3R1_PREFLIGHT_PASS=True"
    )
    print(
        "FINAL_DATASETS=4"
    )
    print(
        "FINAL_MODELS=9"
    )
    print(
        "SEEDS=5"
    )
    print(
        "TOTAL_TRAINING_RUNS=180"
    )


def train_seed(
    dataset_name,
    model_name,
    seed,
    device,
):

    seed_dir = (
        RAW_ROOT /
        dataset_name /
        model_name /
        f"seed_{seed}"
    )

    required = [
        seed_dir / "COMPLETE",
        seed_dir / "best_model.pt",
        seed_dir / "checkpoint.pt",
        seed_dir / "metrics.json",
        seed_dir / "config.json",
        seed_dir / "dataset_summary.json",
        seed_dir / "training_history.json",
        seed_dir / "receipt.json",
    ]

    if all(
        path.exists()
        for path in required
    ):
        print(
            "TRAIN_SKIP_COMPLETE:",
            dataset_name,
            model_name,
            seed,
            flush=True,
        )
        return

    if seed_dir.exists():
        archive_partial(
            seed_dir,
            "training",
        )

    seed_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    print()
    print(
        "=" * 72,
        flush=True,
    )
    print(
        "TRAIN_START:",
        dataset_name,
        model_name,
        "SEED",
        seed,
        flush=True,
    )
    print(
        "=" * 72,
        flush=True,
    )

    set_seed(seed)

    cfg = load_config(
        model_name,
        dataset_name,
        seed,
    )

    training = cfg[
        "training"
    ]

    augmentation = cfg[
        "augmentation"
    ]

    batch_size = int(
        training.get(
            "batch_size",
            64,
        )
    )

    epochs = int(
        training.get(
            "epochs",
            100,
        )
    )

    learning_rate = float(
        training.get(
            "learning_rate",
            0.001,
        )
    )

    reliability_training = bool(
        augmentation.get(
            "reliability_training",
            False,
        )
    )

    corruption_probability = float(
        augmentation.get(
            "corruption_probability",
            0.3,
        )
    )

    consistency_weight = float(
        augmentation.get(
            "consistency_weight",
            0.2,
        )
    )

    data = load_dataset_v3r1(
        dataset_name,
        batch_size=batch_size,
        reliability_training=(
            reliability_training
        ),
        corruption_probability=(
            corruption_probability
        ),
    )

    train_loader = data[
        "train_loader"
    ]

    val_loader = data[
        "val_loader"
    ]

    test_loader = data[
        "test_loader"
    ]

    num_classes = data[
        "num_classes"
    ]

    model = create_model(
        model_name,
        num_classes,
        input_channels=6,
    ).to(device)

    parameters = sum(
        parameter.numel()
        for parameter
        in model.parameters()
    )

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
    )

    criterion = nn.CrossEntropyLoss()

    best_f1 = float("-inf")

    best_epoch = None

    best_path = (
        seed_dir /
        "best_model.pt"
    )

    history = []

    consistency_feature_available = (
        False
    )

    training_start = time.time()

    for epoch in range(
        1,
        epochs + 1,
    ):

        model.train()

        total_loss = 0.0
        total_batches = 0

        for batch in train_loader:

            optimizer.zero_grad(
                set_to_none=True
            )

            if reliability_training:

                if len(batch) != 3:
                    raise RuntimeError(
                        "Reliability training "
                        "requires "
                        "(clean, corrupt, y)"
                    )

                clean = batch[0].to(
                    device,
                    non_blocking=True,
                )

                corrupt = batch[1].to(
                    device,
                    non_blocking=True,
                )

                y = batch[2].to(
                    device,
                    non_blocking=True,
                )

                clean_raw = model_forward(
                    model,
                    clean,
                )

                corrupt_raw = model_forward(
                    model,
                    corrupt,
                )

                (
                    clean_logits,
                    clean_feature,
                ) = unpack_output(
                    clean_raw
                )

                (
                    _,
                    corrupt_feature,
                ) = unpack_output(
                    corrupt_raw
                )

                classification_loss = (
                    criterion(
                        clean_logits,
                        y,
                    )
                )

                if (
                    clean_feature is not None
                    and
                    corrupt_feature is not None
                ):

                    consistency_feature_available = (
                        True
                    )

                    consistency_loss = (
                        (
                            clean_feature
                            -
                            corrupt_feature
                        )
                        .pow(2)
                        .mean()
                    )

                else:

                    consistency_loss = (
                        torch.zeros(
                            (),
                            device=device,
                        )
                    )

                loss = (
                    classification_loss
                    +
                    consistency_weight
                    *
                    consistency_loss
                )

            else:

                if len(batch) != 2:
                    raise RuntimeError(
                        "Standard training "
                        "requires (x, y)"
                    )

                x = batch[0].to(
                    device,
                    non_blocking=True,
                )

                y = batch[1].to(
                    device,
                    non_blocking=True,
                )

                raw = model_forward(
                    model,
                    x,
                )

                logits, _ = unpack_output(
                    raw
                )

                loss = criterion(
                    logits,
                    y,
                )

            loss.backward()

            optimizer.step()

            total_loss += float(
                loss.detach().item()
            )

            total_batches += 1

        val_result = evaluate_basic(
            model,
            val_loader,
            device,
        )

        history.append({
            "epoch":
                int(epoch),
            "train_loss":
                total_loss
                /
                max(
                    total_batches,
                    1,
                ),
            "val_accuracy":
                val_result[
                    "accuracy"
                ],
            "val_macro_f1":
                val_result[
                    "macro_f1"
                ],
        })

        if (
            val_result[
                "macro_f1"
            ]
            >
            best_f1
        ):

            best_f1 = float(
                val_result[
                    "macro_f1"
                ]
            )

            best_epoch = int(
                epoch
            )

            save_cpu_state(
                model,
                best_path,
            )

        if (
            epoch == 1
            or
            epoch % 10 == 0
            or
            epoch == epochs
        ):

            print(
                "EPOCH",
                epoch,
                "/",
                epochs,
                "VAL_F1=",
                f"{val_result['macro_f1']:.6f}",
                "BEST_F1=",
                f"{best_f1:.6f}",
                "BEST_EPOCH=",
                best_epoch,
                flush=True,
            )

    training_seconds = (
        time.time()
        -
        training_start
    )

    if not best_path.exists():
        raise RuntimeError(
            "No best_model.pt was saved"
        )

    state = load_state(
        best_path,
        device,
    )

    model.load_state_dict(
        state,
        strict=True,
    )

    model.eval()

    test_eval_dir = (
        seed_dir /
        "test_eval"
    )

    test_eval_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    test_result = evaluate_model(
        model,
        test_loader,
        device,
        test_eval_dir,
    )

    checkpoint_path = (
        seed_dir /
        "checkpoint.pt"
    )

    shutil.copy2(
        best_path,
        checkpoint_path,
    )

    metrics = {
        "protocol":
            "benchmark_v3r1",
        "dataset":
            dataset_name,
        "model":
            model_name,
        "seed":
            int(seed),
        "num_classes":
            int(num_classes),
        "epochs_requested":
            int(epochs),
        "epochs_completed":
            int(epochs),
        "best_epoch":
            int(best_epoch),
        "best_validation_macro_f1":
            float(best_f1),
        "training_seconds":
            float(training_seconds),
        "parameters":
            int(parameters),
        "checkpoint_size_mb":
            float(
                best_path.stat().st_size
                /
                (
                    1024
                    *
                    1024
                )
            ),
        "reliability_training":
            reliability_training,
        "corruption_probability":
            corruption_probability
            if reliability_training
            else 0.0,
        "consistency_weight":
            consistency_weight
            if reliability_training
            else 0.0,
        "consistency_feature_available":
            bool(
                consistency_feature_available
            ),
        "test":
            test_result,
    }

    save_json(
        seed_dir /
        "metrics.json",
        metrics,
    )

    save_json(
        seed_dir /
        "config.json",
        cfg,
    )

    save_json(
        seed_dir /
        "dataset_summary.json",
        data[
            "summary"
        ],
    )

    save_json(
        seed_dir /
        "training_history.json",
        history,
    )

    receipt = {
        "protocol_manifest_sha256":
            sha256_file(
                PROTOCOL_MANIFEST
            ),
        "best_model_sha256":
            sha256_file(
                best_path
            ),
        "checkpoint_sha256":
            sha256_file(
                checkpoint_path
            ),
        "config_sha256":
            sha256_file(
                seed_dir /
                "config.json"
            ),
        "metrics_sha256":
            sha256_file(
                seed_dir /
                "metrics.json"
            ),
    }

    save_json(
        seed_dir /
        "receipt.json",
        receipt,
    )

    (
        seed_dir /
        "COMPLETE"
    ).write_text(
        "BENCHMARK_V3R1_TRAIN_COMPLETE=True\n"
    )

    print(
        "TRAIN_COMPLETE:",
        dataset_name,
        model_name,
        seed,
        "BEST_EPOCH=",
        best_epoch,
        "TEST_ACC=",
        test_result.get(
            "accuracy"
        ),
        "TEST_F1=",
        test_result.get(
            "macro_f1"
        ),
        flush=True,
    )

    del model
    del data
    del train_loader
    del val_loader
    del test_loader

    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def run_reliability_dataset(
    dataset_name,
    device,
):

    print()
    print(
        "=" * 72,
        flush=True,
    )
    print(
        "RELIABILITY_DATASET_START:",
        dataset_name,
        flush=True,
    )
    print(
        "=" * 72,
        flush=True,
    )

    data = load_dataset_v3r1(
        dataset_name,
        batch_size=64,
        reliability_training=False,
    )

    test_loader = data[
        "test_loader"
    ]

    num_classes = data[
        "num_classes"
    ]

    for model_name in MODELS:

        for seed in SEEDS:

            training_dir = (
                RAW_ROOT /
                dataset_name /
                model_name /
                f"seed_{seed}"
            )

            checkpoint = (
                training_dir /
                "best_model.pt"
            )

            if not (
                training_dir /
                "COMPLETE"
            ).exists():

                raise RuntimeError(
                    "Reliability requested "
                    "before clean training "
                    "completed: "
                    f"{dataset_name}/"
                    f"{model_name}/"
                    f"{seed}"
                )

            if not checkpoint.exists():

                raise FileNotFoundError(
                    checkpoint
                )

            output_dir = (
                RELIABILITY_ROOT /
                dataset_name /
                model_name /
                f"seed_{seed}"
            )

            summary_path = (
                output_dir /
                "reliability_summary_v2.json"
            )

            complete_path = (
                output_dir /
                "COMPLETE"
            )

            if (
                summary_path.exists()
                and
                complete_path.exists()
            ):

                print(
                    "RELIABILITY_SKIP_COMPLETE:",
                    dataset_name,
                    model_name,
                    seed,
                    flush=True,
                )

                continue

            if output_dir.exists():

                archive_partial(
                    output_dir,
                    "reliability",
                )

            print(
                "RELIABILITY_START:",
                dataset_name,
                model_name,
                seed,
                flush=True,
            )

            model = create_model(
                model_name,
                num_classes,
                input_channels=6,
            ).to(device)

            state = load_state(
                checkpoint,
                device,
            )

            model.load_state_dict(
                state,
                strict=True,
            )

            model.eval()

            run_reliability_evaluation_v2(
                model,
                test_loader,
                device,
                output_dir,
                registry_path=(
                    FROZEN_CORRUPTION
                ),
            )

            if not summary_path.exists():

                raise RuntimeError(
                    "Reliability V2 did not "
                    "produce "
                    "reliability_summary_v2.json"
                )

            save_json(
                output_dir /
                "receipt.json",
                {
                    "protocol_manifest_sha256":
                        sha256_file(
                            PROTOCOL_MANIFEST
                        ),
                    "clean_checkpoint_sha256":
                        sha256_file(
                            checkpoint
                        ),
                    "corruption_registry_sha256":
                        sha256_file(
                            FROZEN_CORRUPTION
                        ),
                    "summary_sha256":
                        sha256_file(
                            summary_path
                        ),
                },
            )

            complete_path.write_text(
                "BENCHMARK_V3R1_RELIABILITY_COMPLETE=True\n"
            )

            print(
                "RELIABILITY_COMPLETE:",
                dataset_name,
                model_name,
                seed,
                flush=True,
            )

            del model

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    del data
    del test_loader


def write_worker_status(
    datasets,
    phase,
):

    status_root = (
        RESULT_ROOT /
        "status"
    )

    status_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    clean_complete = 0
    reliability_complete = 0

    for dataset_name in datasets:

        for model_name in MODELS:

            for seed in SEEDS:

                if (
                    RAW_ROOT /
                    dataset_name /
                    model_name /
                    f"seed_{seed}" /
                    "COMPLETE"
                ).exists():
                    clean_complete += 1

                if (
                    RELIABILITY_ROOT /
                    dataset_name /
                    model_name /
                    f"seed_{seed}" /
                    "COMPLETE"
                ).exists():
                    reliability_complete += 1

    worker_name = "_".join(
        datasets
    )

    save_json(
        status_root /
        f"worker_{worker_name}.json",
        {
            "datasets":
                datasets,
            "phase":
                phase,
            "training_complete":
                clean_complete,
            "training_expected":
                len(datasets)
                *
                len(MODELS)
                *
                len(SEEDS),
            "reliability_complete":
                reliability_complete,
            "reliability_expected":
                len(datasets)
                *
                len(MODELS)
                *
                len(SEEDS),
            "worker_complete":
                True,
        },
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--preflight",
        action="store_true",
    )

    parser.add_argument(
        "--phase",
        choices=[
            "all",
            "train",
            "reliability",
        ],
        default="all",
    )

    parser.add_argument(
        "--datasets",
        nargs="+",
        default=DATASETS,
    )

    args = parser.parse_args()

    if args.preflight:
        preflight()
        return

    unknown = [
        dataset
        for dataset
        in args.datasets
        if dataset not in DATASETS
    ]

    if unknown:
        raise RuntimeError(
            f"Unknown datasets: {unknown}"
        )

    if not PREFLIGHT_MARKER.exists():
        raise RuntimeError(
            "BENCHMARK V3R1 "
            "PREFLIGHT_PASS is missing"
        )

    if not PROTOCOL_MANIFEST.exists():
        raise RuntimeError(
            "Protocol manifest is missing"
        )

    if not FROZEN_CORRUPTION.exists():
        raise RuntimeError(
            "Frozen Reliability V2 "
            "registry is missing"
        )

    if not torch.cuda.is_available():
        raise RuntimeError(
            "Canonical V3R1 run "
            "requires CUDA"
        )

    device = torch.device(
        "cuda"
    )

    print(
        "BENCHMARK_V3R1_WORKER_START=True",
        flush=True,
    )

    print(
        "DATASETS=",
        args.datasets,
        flush=True,
    )

    print(
        "PHASE=",
        args.phase,
        flush=True,
    )

    print(
        "VISIBLE_GPU=",
        torch.cuda.get_device_name(
            0
        ),
        flush=True,
    )

    if args.phase in (
        "all",
        "train",
    ):

        for dataset_name in args.datasets:

            print()
            print(
                "DATASET_TRAINING_START:",
                dataset_name,
                flush=True,
            )

            for model_name in MODELS:

                for seed in SEEDS:

                    train_seed(
                        dataset_name,
                        model_name,
                        seed,
                        device,
                    )

    if args.phase in (
        "all",
        "reliability",
    ):

        for dataset_name in args.datasets:

            run_reliability_dataset(
                dataset_name,
                device,
            )

    write_worker_status(
        args.datasets,
        args.phase,
    )

    print(
        "BENCHMARK_V3R1_WORKER_COMPLETE=True",
        flush=True,
    )


if __name__ == "__main__":
    main()
