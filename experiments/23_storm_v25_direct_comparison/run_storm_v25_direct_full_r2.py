from __future__ import annotations

from pathlib import Path

import argparse
import csv
import hashlib
import importlib.util
import inspect
import json
import math
import os
import random
import shutil
import subprocess
import sys
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from scipy.stats import (
    ttest_rel,
    wilcoxon,
)


# ============================================================
# PATHS
# ============================================================

REPO = Path.cwd()

EXP = (
    REPO /
    "experiments" /
    "23_storm_v25_direct_comparison"
)

ROOT = (
    REPO /
    "results" /
    "storm_v25_direct_r2"
)

RAW = (
    ROOT /
    "raw_runs"
)

FAULT_ROOT = (
    ROOT /
    "fault_eval"
)

FINAL = (
    ROOT /
    "final_analysis"
)

SMOKE = (
    ROOT /
    "smoke"
)

PROTO = (
    ROOT /
    "protocol"
)

DATA_ROOT = (
    REPO /
    "results" /
    "storm_external_r2" /
    "data" /
    "unified"
)

DATA_RECEIPT = (
    REPO /
    "results" /
    "storm_external_r2" /
    "dataset_audit" /
    "storm_dataset_r2_receipt.json"
)

PREFLIGHT_MANIFEST = (
    PROTO /
    "preflight_manifest_r1.json"
)

PREFLIGHT_RECEIPT = (
    ROOT /
    "preflight" /
    "storm_v25_direct_preflight_receipt_r1.json"
)

DIRECT_PROTOCOL = (
    PROTO /
    "storm_v25_direct_protocol_r1.json"
)

STORM_REF = (
    REPO /
    "external_references" /
    "storm_2026_upstream"
)

STORM_TRAIN = (
    STORM_REF /
    "train.py"
)

V25_CODE = (
    REPO /
    "experiments" /
    "17_v25_screening"
)

V25_ABLATION = (
    REPO /
    "experiments" /
    "18_v25_training_ablation" /
    "run_v25_ablation_r1.py"
)

V25_FINAL_SOURCE = (
    REPO /
    "experiments" /
    "19_v25_final_confirmation" /
    "run_v25_final_r2.py"
)


sys.path.insert(
    0,
    str(STORM_REF)
)

sys.path.insert(
    0,
    str(V25_CODE)
)


from storm import (
    STORM,
    STORMConfig,
)

from v25_candidates import (
    create_candidate,
)


# ============================================================
# CONSTANTS
# ============================================================

SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]


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


EXPECTED_STORM_PARAMS = 19753
EXPECTED_V25_PARAMS = 48306

EXPECTED_TRAIN_N = 60379
EXPECTED_VAL_N = 13158
EXPECTED_TEST_N = 13993

FAULT_CASES_EXPECTED = 33

V25_CORRUPTION_P = 0.30


for path in [
    RAW,
    FAULT_ROOT,
    FINAL,
    SMOKE,
]:

    path.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# GENERAL HELPERS
# ============================================================

def sha256_file(path: Path) -> str:

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


def load_json(path: Path):

    return json.loads(
        Path(path).read_text()
    )


def write_json(
    path: Path,
    obj
):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        json.dumps(
            obj,
            indent=2,
            sort_keys=True
        )
    )


def seed_everything(
    seed: int
):

    random.seed(
        seed
    )

    np.random.seed(
        seed
    )

    torch.manual_seed(
        seed
    )

    if torch.cuda.is_available():

        torch.cuda.manual_seed_all(
            seed
        )


def confusion_matrix(
    y_true,
    y_pred,
    k=8
):

    cm = np.zeros(
        (
            k,
            k
        ),
        dtype=np.int64
    )


    for t, p in zip(
        y_true,
        y_pred
    ):

        cm[
            int(t),
            int(p)
        ] += 1


    return cm


def metrics_from_predictions(
    y_true,
    y_pred,
    k=8
):

    y_true = np.asarray(
        y_true,
        dtype=np.int64
    )

    y_pred = np.asarray(
        y_pred,
        dtype=np.int64
    )


    cm = confusion_matrix(
        y_true,
        y_pred,
        k=k
    )


    accuracy = float(
        np.mean(
            y_true
            ==
            y_pred
        )
    )


    f1s = []


    for cls in range(
        k
    ):

        tp = float(
            cm[
                cls,
                cls
            ]
        )

        fp = float(
            cm[
                :,
                cls
            ].sum()
            -
            tp
        )

        fn = float(
            cm[
                cls,
                :
            ].sum()
            -
            tp
        )


        denom = (
            2.0 * tp
            +
            fp
            +
            fn
        )


        if denom > 0:

            f1 = (
                2.0
                *
                tp
                /
                denom
            )

        else:

            f1 = 0.0


        f1s.append(
            f1
        )


    return {
        "accuracy":
            accuracy,

        "macro_f1":
            float(
                np.mean(
                    f1s
                )
            ),

        "confusion_matrix":
            cm.tolist(),

        "n":
            int(
                len(
                    y_true
                )
            ),
    }


def archive_incomplete_run(
    run_dir: Path
):

    if not run_dir.exists():
        return


    success = (
        run_dir /
        "SUCCESS.json"
    )


    if success.exists():
        return


    stamp = time.strftime(
        "%Y%m%d_%H%M%S"
    )


    dst = (
        run_dir.parent /
        (
            run_dir.name
            +
            "_incomplete_"
            +
            stamp
        )
    )


    shutil.move(
        str(
            run_dir
        ),
        str(
            dst
        )
    )


    print(
        "ARCHIVED_INCOMPLETE_RUN=",
        dst
    )


def success_is_valid(
    run_dir: Path
):

    success_path = (
        run_dir /
        "SUCCESS.json"
    )


    if not success_path.exists():
        return False


    try:

        success = load_json(
            success_path
        )


        ckpt = Path(
            success[
                "checkpoint"
            ]
        )


        if not ckpt.is_absolute():

            ckpt = (
                REPO /
                ckpt
            )


        if not ckpt.exists():
            return False


        if (
            sha256_file(
                ckpt
            )
            !=
            success[
                "checkpoint_sha256"
            ]
        ):

            return False


        return True

    except Exception:

        return False


# ============================================================
# FROZEN-EVIDENCE VERIFICATION
# ============================================================

def verify_frozen_evidence():

    for path in [
        DATA_RECEIPT,
        PREFLIGHT_MANIFEST,
        PREFLIGHT_RECEIPT,
        DIRECT_PROTOCOL,
        STORM_TRAIN,
        V25_ABLATION,
        V25_FINAL_SOURCE,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                path
            )


    stage22 = load_json(
        DATA_RECEIPT
    )


    if (
        stage22.get(
            "published_table2_exact_match"
        )
        is not True
    ):

        raise RuntimeError(
            "Stage22 dataset no longer PASS"
        )


    if (
        stage22.get(
            "training_allowed_after_this_receipt"
        )
        is not True
    ):

        raise RuntimeError(
            "Stage22 does not allow training"
        )


    preflight = load_json(
        PREFLIGHT_RECEIPT
    )


    if (
        preflight.get(
            "training_started"
        )
        is not False
    ):

        raise RuntimeError(
            "Unexpected preflight receipt state"
        )


    if (
        preflight.get(
            "storm_parameters"
        )
        !=
        EXPECTED_STORM_PARAMS
    ):

        raise RuntimeError(
            "STORM parameter preflight changed"
        )


    if (
        preflight.get(
            "v25_parameters"
        )
        !=
        EXPECTED_V25_PARAMS
    ):

        raise RuntimeError(
            "V25 parameter preflight changed"
        )


    manifest = load_json(
        PREFLIGHT_MANIFEST
    )


    verified = 0


    for relative, expected in (
        manifest[
            "hashes"
        ].items()
    ):

        path = (
            REPO /
            relative
        )


        if not path.exists():

            raise FileNotFoundError(
                path
            )


        actual = sha256_file(
            path
        )


        if actual != expected:

            raise RuntimeError(
                "Frozen Stage23 preflight input "
                f"changed: {relative}"
            )


        verified += 1


    if verified != 12:

        raise RuntimeError(
            f"Expected 12 frozen hashes, got {verified}"
        )


    app_expected = subprocess.check_output(
        [
            "git",
            "-C",
            str(
                STORM_REF
            ),
            "ls-tree",
            "HEAD",
            "app",
        ],
        text=True
    ).split()[2]


    app_actual = subprocess.check_output(
        [
            "git",
            "-C",
            str(
                STORM_REF /
                "app"
            ),
            "rev-parse",
            "HEAD",
        ],
        text=True
    ).strip()


    if app_expected != app_actual:

        raise RuntimeError(
            "STORM app submodule mismatch"
        )


    print(
        "FULL_BATCH_FROZEN_HASHES_VERIFIED=12/12"
    )

    print(
        "STORM_APP_COMMIT=",
        app_actual
    )

    print(
        "FULL_BATCH_INPUT_INTEGRITY_PASS=True"
    )


# ============================================================
# DATA LOADERS
# ============================================================

def load_split_numpy(
    split
):

    path = (
        DATA_ROOT /
        f"{split}.npz"
    )


    d = np.load(
        path,
        allow_pickle=False
    )


    X = d[
        "X"
    ].astype(
        np.float32,
        copy=False
    )


    y = d[
        "y"
    ].astype(
        np.int64,
        copy=False
    )


    return X, y


def load_all_data():

    train = load_split_numpy(
        "train"
    )

    val = load_split_numpy(
        "val"
    )

    test = load_split_numpy(
        "test"
    )


    if len(
        train[
            1
        ]
    ) != EXPECTED_TRAIN_N:

        raise RuntimeError(
            "Unexpected train N"
        )


    if len(
        val[
            1
        ]
    ) != EXPECTED_VAL_N:

        raise RuntimeError(
            "Unexpected val N"
        )


    if len(
        test[
            1
        ]
    ) != EXPECTED_TEST_N:

        raise RuntimeError(
            "Unexpected test N"
        )


    return train, val, test


# ============================================================
# STORM
# ============================================================

def storm_config():

    return STORMConfig(
        in_ch=6,
        d_model=32,
        nhead=4,
        depth=2,
        ffn_mult=2,
        num_classes=8,
        attention_window=16,
        int_layernorm=True,
        int_ln_lut_size=256,
        drop_path_rate=0.0,
        feat_dropout=0.0,
    )


def storm_command(
    seed,
    out_path,
    *,
    smoke=False,
):

    epochs = (
        4
        if smoke
        else
        200
    )


    early_stop = (
        0
        if smoke
        else
        15
    )


    num_workers = (
        0
        if smoke
        else
        4
    )


    cmd = [
        sys.executable,
        str(
            STORM_TRAIN
        ),

        "--train",
        str(
            DATA_ROOT /
            "train.npz"
        ),

        "--val",
        str(
            DATA_ROOT /
            "val.npz"
        ),

        "--out",
        str(
            out_path
        ),

        "--model",
        "storm",

        "--in-ch",
        "6",

        "--d-model",
        "32",

        "--nhead",
        "4",

        "--depth",
        "2",

        "--ffn-mult",
        "2",

        "--num-classes",
        "8",

        "--attn-window",
        "16",

        "--int-ln-lut-size",
        "256",

        "--epochs",
        str(
            epochs
        ),

        "--batch",
        "256",

        "--lr",
        "0.0006",

        "--weight-decay",
        "0.0008",

        "--grad-clip",
        "1.0",

        "--scheduler",
        "onecycle",

        "--warmup-epochs",
        "15",

        "--seed",
        str(
            seed
        ),

        "--device",
        "cuda",

        "--num-workers",
        str(
            num_workers
        ),

        "--ema-decay",
        "0.999",

        "--loss",
        "ce",

        "--focal-gamma",
        "2.0",

        "--label-smoothing",
        "0.05",

        "--class-weight",
        "none",

        "--sampler",
        "weighted",

        "--metric",
        "val_quant_macro_f1",

        "--early-stop",
        str(
            early_stop
        ),

        "--jitter",
        "0.005",

        "--scale",
        "0.08",

        "--time-mask",
        "0.10",

        "--time-warp",
        "0.03",

        "--p-drop-gyro",
        "0.30",

        "--p-drop-acc",
        "0.03",

        "--p-drop-axis",
        "0.15",

        "--mixup-alpha",
        "0.0",

        "--cutmix-alpha",
        "0.0",

        "--mix-prob",
        "0.5",

        "--drop-path",
        "0.0",

        "--feat-dropout",
        "0.0",

        "--sam",

        "--sam-rho",
        "0.05",

        "--rdrop-alpha",
        "0.0",

        "--iqat-percentile",
        "99.8",

        "--iqat-scale-jitter",
        "0.1",

        "--qat-momentum",
        "0.93",

        "--qat-lr-mult",
        "0.1",

        "--deploy-sim",
        "periodic",

        "--deploy-sim-every",
        "12",

        "--deploy-sim-last-epochs",
        "3",

        "--self-distill-epochs",
        "0",

        "--self-distill-temp",
        "3.0",

        "--self-distill-alpha",
        "0.5",

        "--self-distill-lr-mult",
        "0.3",

        "--tta",
        "0",

        "--tta-jitter",
        "0.005",

        "--tta-scale",
        "0.03",
    ]


    # IMPORTANT:
    #
    # DO NOT add:
    #
    #   --amp
    #   --iqat
    #   --qat
    #   --eval-quant
    #   --int-ln
    #
    # In released STORM train.py those are
    # store_false flags. Their absence means
    # the features remain enabled.


    if smoke:

        cmd += [
            "--max-train",
            "1024",

            "--max-val",
            "512",
        ]


    return cmd


def load_storm_checkpoint(
    path
):

    ckpt = torch.load(
        path,
        map_location="cpu",
        weights_only=False
    )


    cfg_dict = ckpt.get(
        "cfg",
        {}
    )


    allowed = (
        STORMConfig
        .__dataclass_fields__
        .keys()
    )


    cfg = STORMConfig(
        **{
            k: v
            for k, v
            in cfg_dict.items()
            if k in allowed
        }
    )


    model = STORM(
        cfg
    )


    state = ckpt.get(
        "state_dict",
        ckpt
    )


    model.load_state_dict(
        state,
        strict=True
    )


    params = int(
        sum(
            p.numel()
            for p in model.parameters()
        )
    )


    if params != EXPECTED_STORM_PARAMS:

        raise RuntimeError(
            "Loaded STORM parameter count "
            f"{params} != {EXPECTED_STORM_PARAMS}"
        )


    return model


# ============================================================
# V25 FROZEN CORRUPTION FUNCTION
# ============================================================

def load_frozen_v25_corruption():

    spec = (
        importlib.util
        .spec_from_file_location(
            "v25_ablation_frozen",
            V25_ABLATION
        )
    )


    if spec is None or spec.loader is None:

        raise RuntimeError(
            "Unable to import V25 ablation source"
        )


    module = importlib.util.module_from_spec(
        spec
    )


    spec.loader.exec_module(
        module
    )


    if not hasattr(
        module,
        "deterministic_corruption"
    ):

        raise RuntimeError(
            "Frozen V25 deterministic_corruption "
            "function missing"
        )


    fn = getattr(
        module,
        "deterministic_corruption"
    )


    sig = inspect.signature(
        fn
    )


    params = list(
        sig.parameters.items()
    )


    if not params:

        raise RuntimeError(
            "Invalid deterministic_corruption signature"
        )


    first_name = params[
        0
    ][
        0
    ]


    def call(
        x,
        seed,
        epoch,
        batch_index,
        schedule_hasher=None,
    ):

        kwargs = {
            first_name:
                x
        }


        for name, param in params[
            1:
        ]:

            lower = (
                name.lower()
            )


            if "seed" in lower:

                kwargs[
                    name
                ] = int(
                    seed
                )


            elif "epoch" in lower:

                kwargs[
                    name
                ] = int(
                    epoch
                )


            elif (
                "batch" in lower
                and
                (
                    "idx" in lower
                    or
                    "index" in lower
                )
            ):

                kwargs[
                    name
                ] = int(
                    batch_index
                )


            elif lower in {
                "p",
                "prob",
                "probability",
                "drop_prob",
                "corruption_prob",
            }:

                kwargs[
                    name
                ] = float(
                    V25_CORRUPTION_P
                )


            elif lower == "schedule_hasher":

                kwargs[
                    name
                ] = (
                    schedule_hasher
                    if schedule_hasher is not None
                    else hashlib.sha256()
                )


            elif (
                param.default
                is
                inspect._empty
            ):

                raise RuntimeError(
                    "Unsupported required "
                    "deterministic_corruption "
                    f"argument: {name}"
                )


        result = fn(
            **kwargs
        )


        if torch.is_tensor(
            result
        ):

            out = result


        elif isinstance(
            result,
            (
                tuple,
                list
            )
        ):

            tensors = [
                item
                for item
                in result
                if torch.is_tensor(
                    item
                )
            ]


            if not tensors:

                raise RuntimeError(
                    "deterministic_corruption "
                    "returned no tensor"
                )


            out = tensors[
                0
            ]


        else:

            raise RuntimeError(
                "Unexpected deterministic_corruption "
                f"return type={type(result)}"
            )


        if out.shape != x.shape:

            raise RuntimeError(
                "Corruption output shape mismatch"
            )


        return out


    return (
        call,
        str(
            sig
        )
    )


FROZEN_CORRUPTION, CORRUPTION_SIGNATURE = (
    load_frozen_v25_corruption()
)


def verify_v25_corruption_semantics():

    probe = (
        torch.arange(
            4
            *
            64
            *
            6,
            dtype=torch.float32
        )
        .reshape(
            4,
            64,
            6
        )
        +
        1.0
    )


    a = FROZEN_CORRUPTION(
        probe.clone(),
        42,
        1,
        0,
    )


    b = FROZEN_CORRUPTION(
        probe.clone(),
        42,
        1,
        0,
    )


    if not torch.equal(
        a,
        b
    ):

        raise RuntimeError(
            "Frozen corruption is not deterministic"
        )


    for sample in range(
        probe.shape[
            0
        ]
    ):

        for channel in range(
            probe.shape[
                2
            ]
        ):

            src = probe[
                sample,
                :,
                channel
            ]


            dst = a[
                sample,
                :,
                channel
            ]


            unchanged = torch.equal(
                dst,
                src
            )


            all_zero = bool(
                torch.all(
                    dst
                    ==
                    0
                )
            )


            if not (
                unchanged
                or
                all_zero
            ):

                raise RuntimeError(
                    "Frozen corruption is not "
                    "whole-channel zero exposure"
                )


    print(
        "V25_CORRUPTION_SIGNATURE=",
        CORRUPTION_SIGNATURE
    )

    print(
        "V25_FROZEN_CORRUPTION_DETERMINISTIC=True"
    )

    print(
        "V25_FROZEN_CORRUPTION_WHOLE_CHANNEL=True"
    )


# ============================================================
# EVALUATION
# ============================================================

@torch.no_grad()
def evaluate_model(
    model,
    X,
    y,
    *,
    batch_size=512,
    transform=None,
):

    model.eval()

    device = torch.device(
        "cuda"
    )


    model = model.to(
        device
    )


    ys = []

    preds = []


    for start in range(
        0,
        len(
            y
        ),
        batch_size
    ):

        stop = min(
            start
            +
            batch_size,
            len(
                y
            )
        )


        xb = torch.from_numpy(
            X[
                start:
                stop
            ]
        ).to(
            device
        )


        yb = y[
            start:
            stop
        ]


        if transform is not None:

            xb = transform(
                xb
            )


        logits = model(
            xb
        )


        pred = (
            logits
            .argmax(
                dim=1
            )
            .detach()
            .cpu()
            .numpy()
        )


        ys.append(
            yb
        )

        preds.append(
            pred
        )


    y_true = np.concatenate(
        ys
    )

    y_pred = np.concatenate(
        preds
    )


    return metrics_from_predictions(
        y_true,
        y_pred,
        k=8
    )


# ============================================================
# STORM TRAINING
# ============================================================

def run_storm_seed(
    seed,
    test_X,
    test_y,
):

    run_dir = (
        RAW /
        "STORM_native" /
        f"seed_{seed}"
    )


    if success_is_valid(
        run_dir
    ):

        print(
            "STORM_RUN_ALREADY_COMPLETE:",
            seed
        )

        return load_json(
            run_dir /
            "SUCCESS.json"
        )


    archive_incomplete_run(
        run_dir
    )


    run_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    ckpt = (
        run_dir /
        "best.pt"
    )


    cmd = storm_command(
        seed,
        ckpt,
        smoke=False
    )


    write_json(
        run_dir /
        "invocation.json",
        {
            "seed":
                seed,

            "command":
                cmd,

            "important_store_false_defaults":
                {
                    "amp":
                        True,

                    "iqat":
                        True,

                    "qat":
                        True,

                    "eval_quant":
                        True,

                    "int_ln":
                        True,
                },
        }
    )


    print()
    print(
        "=" * 90
    )

    print(
        "TRAIN_STORM_NATIVE_SEED=",
        seed
    )

    print(
        "=" * 90
    )


    start_time = time.time()


    env = os.environ.copy()

    env[
        "PYTHONUNBUFFERED"
    ] = "1"

    env[
        "OMP_NUM_THREADS"
    ] = "1"

    env[
        "MKL_NUM_THREADS"
    ] = "1"


    with (
        run_dir /
        "train_console.log"
    ).open(
        "w"
    ) as log:

        proc = subprocess.run(
            cmd,
            cwd=str(
                REPO
            ),
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
        )


    train_seconds = (
        time.time()
        -
        start_time
    )


    if proc.returncode != 0:

        raise RuntimeError(
            "STORM training failed "
            f"seed={seed}; inspect "
            f"{run_dir / 'train_console.log'}"
        )


    if not ckpt.exists():

        raise RuntimeError(
            "STORM best checkpoint missing "
            f"seed={seed}"
        )


    model = load_storm_checkpoint(
        ckpt
    )


    metrics = evaluate_model(
        model,
        test_X,
        test_y
    )


    success = {
        "model":
            "STORM_native",

        "seed":
            seed,

        "checkpoint":
            str(
                ckpt.relative_to(
                    REPO
                )
            ),

        "checkpoint_sha256":
            sha256_file(
                ckpt
            ),

        "parameters":
            EXPECTED_STORM_PARAMS,

        "train_seconds":
            train_seconds,

        "clean_test_accuracy":
            metrics[
                "accuracy"
            ],

        "clean_test_macro_f1":
            metrics[
                "macro_f1"
            ],

        "clean_test_n":
            metrics[
                "n"
            ],

        "selection":
            "validation quantized macro-F1",

        "test_used_for_selection":
            False,
    }


    write_json(
        run_dir /
        "SUCCESS.json",
        success
    )


    print(
        "STORM_NATIVE_SEED_PASS:",
        seed,
        "ACC=",
        f"{metrics['accuracy']:.6f}",
        "F1=",
        f"{metrics['macro_f1']:.6f}",
        "TIME_S=",
        f"{train_seconds:.1f}"
    )


    del model

    torch.cuda.empty_cache()


    return success


# ============================================================
# V25 TRAINING
# ============================================================

def make_tensor_loader(
    X,
    y,
    *,
    batch_size,
    shuffle,
    seed,
):

    dataset = torch.utils.data.TensorDataset(
        torch.from_numpy(
            X
        ),
        torch.from_numpy(
            y
        ),
    )


    generator = torch.Generator()

    generator.manual_seed(
        int(
            seed
        )
    )


    return torch.utils.data.DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=0,
        pin_memory=True,
        generator=(
            generator
            if shuffle
            else
            None
        ),
        drop_last=False,
    )


def evaluate_v25_loader(
    model,
    loader,
):

    model.eval()


    ys = []

    preds = []


    with torch.inference_mode():

        for xb, yb in loader:

            xb = xb.cuda(
                non_blocking=True
            )

            logits = model(
                xb
            )


            pred = (
                logits
                .argmax(
                    dim=1
                )
                .cpu()
                .numpy()
            )


            ys.append(
                yb.numpy()
            )

            preds.append(
                pred
            )


    return metrics_from_predictions(
        np.concatenate(
            ys
        ),
        np.concatenate(
            preds
        ),
        k=8
    )


def run_v25_seed(
    seed,
    train_X,
    train_y,
    val_X,
    val_y,
    test_X,
    test_y,
):

    run_dir = (
        RAW /
        "V25_native" /
        f"seed_{seed}"
    )


    if success_is_valid(
        run_dir
    ):

        print(
            "V25_RUN_ALREADY_COMPLETE:",
            seed
        )

        return load_json(
            run_dir /
            "SUCCESS.json"
        )


    archive_incomplete_run(
        run_dir
    )


    run_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    seed_everything(
        seed
    )


    torch.backends.cudnn.benchmark = False

    torch.backends.cudnn.deterministic = True


    model = create_candidate(
        "V25Dense64",
        8,
        input_channels=6
    ).cuda()


    params = int(
        sum(
            p.numel()
            for p in model.parameters()
        )
    )


    if params != EXPECTED_V25_PARAMS:

        raise RuntimeError(
            f"V25 params={params}, "
            f"expected={EXPECTED_V25_PARAMS}"
        )


    train_loader = make_tensor_loader(
        train_X,
        train_y,
        batch_size=64,
        shuffle=True,
        seed=seed,
    )


    val_loader = make_tensor_loader(
        val_X,
        val_y,
        batch_size=512,
        shuffle=False,
        seed=seed,
    )


    test_loader = make_tensor_loader(
        test_X,
        test_y,
        batch_size=512,
        shuffle=False,
        seed=seed,
    )


    criterion = nn.CrossEntropyLoss()


    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=1e-3
    )


    ckpt = (
        run_dir /
        "best_model.pt"
    )


    best_f1 = (
        -math.inf
    )

    best_epoch = (
        None
    )

    best_val_acc = (
        None
    )


    history = []


    schedule_hasher = hashlib.sha256()


    start_time = time.time()


    print()
    print(
        "=" * 90
    )

    print(
        "TRAIN_V25_NATIVE_SEED=",
        seed
    )

    print(
        "=" * 90
    )


    for epoch in range(
        1,
        101
    ):

        model.train()


        loss_sum = 0.0

        sample_count = 0


        epoch_start = time.time()


        for batch_index, (
            xb,
            yb,
        ) in enumerate(
            train_loader
        ):

            xb = xb.cuda(
                non_blocking=True
            )

            yb = yb.cuda(
                non_blocking=True
            )


            optimizer.zero_grad(
                set_to_none=True
            )


            logits = model(
                xb
            )


            loss = criterion(
                logits,
                yb
            )


            # Selected V25 method:
            #
            # clean CE supplies the gradient;
            # deterministic corrupt forward
            # runs in train mode under no_grad,
            # updating BN exposure statistics.
            corrupted = FROZEN_CORRUPTION(
                xb.detach(),
                seed,
                epoch,
                batch_index,
                schedule_hasher=schedule_hasher,
            )


            with torch.no_grad():

                model(
                    corrupted
                )


            loss.backward()


            optimizer.step()


            n = int(
                yb.shape[
                    0
                ]
            )


            loss_sum += (
                float(
                    loss.item()
                )
                *
                n
            )


            sample_count += n


        val_metrics = (
            evaluate_v25_loader(
                model,
                val_loader
            )
        )


        epoch_loss = (
            loss_sum
            /
            max(
                sample_count,
                1
            )
        )


        history.append(
            {
                "epoch":
                    epoch,

                "train_loss":
                    epoch_loss,

                "val_accuracy":
                    val_metrics[
                        "accuracy"
                    ],

                "val_macro_f1":
                    val_metrics[
                        "macro_f1"
                    ],

                "epoch_seconds":
                    time.time()
                    -
                    epoch_start,
            }
        )


        if (
            val_metrics[
                "macro_f1"
            ]
            >
            best_f1
        ):

            best_f1 = (
                val_metrics[
                    "macro_f1"
                ]
            )


            best_val_acc = (
                val_metrics[
                    "accuracy"
                ]
            )


            best_epoch = epoch


            torch.save(
                {
                    "model":
                        "ReliabilityCNN_v25",

                    "architecture":
                        "V25Dense64",

                    "seed":
                        seed,

                    "epoch":
                        epoch,

                    "state_dict":
                        model.state_dict(),

                    "val_accuracy":
                        best_val_acc,

                    "val_macro_f1":
                        best_f1,

                    "corruption_exposure":
                        True,

                    "corruption_p":
                        V25_CORRUPTION_P,

                    "corruption_function_signature":
                        CORRUPTION_SIGNATURE,
                },
                ckpt
            )


        print(
            "V25_EPOCH:",
            seed,
            epoch,
            "LOSS=",
            f"{epoch_loss:.6f}",
            "VAL_ACC=",
            f"{val_metrics['accuracy']:.6f}",
            "VAL_F1=",
            f"{val_metrics['macro_f1']:.6f}",
            "BEST_F1=",
            f"{best_f1:.6f}"
        )


    train_seconds = (
        time.time()
        -
        start_time
    )


    if not ckpt.exists():

        raise RuntimeError(
            "V25 best checkpoint missing"
        )


    saved = torch.load(
        ckpt,
        map_location="cpu",
        weights_only=False
    )


    model.load_state_dict(
        saved[
            "state_dict"
        ],
        strict=True
    )


    test_metrics = evaluate_v25_loader(
        model,
        test_loader
    )


    pd.DataFrame(
        history
    ).to_csv(
        run_dir /
        "training_history.csv",
        index=False
    )


    success = {
        "model":
            "V25_native",

        "seed":
            seed,

        "checkpoint":
            str(
                ckpt.relative_to(
                    REPO
                )
            ),

        "checkpoint_sha256":
            sha256_file(
                ckpt
            ),

        "parameters":
            params,

        "best_epoch":
            best_epoch,

        "best_val_accuracy":
            best_val_acc,

        "best_val_macro_f1":
            best_f1,

        "train_seconds":
            train_seconds,

        "clean_test_accuracy":
            test_metrics[
                "accuracy"
            ],

        "clean_test_macro_f1":
            test_metrics[
                "macro_f1"
            ],

        "clean_test_n":
            test_metrics[
                "n"
            ],

        "selection":
            "validation macro-F1",

        "test_used_for_selection":
            False,

        "corruption_exposure":
            True,

        "consistency_loss":
            False,

        "corruption_schedule_sha256":
            schedule_hasher.hexdigest(),

        "corruption_function_signature":
            CORRUPTION_SIGNATURE,
    }


    write_json(
        run_dir /
        "SUCCESS.json",
        success
    )


    print(
        "V25_NATIVE_SEED_PASS:",
        seed,
        "ACC=",
        f"{test_metrics['accuracy']:.6f}",
        "F1=",
        f"{test_metrics['macro_f1']:.6f}",
        "BEST_EPOCH=",
        best_epoch,
        "TIME_S=",
        f"{train_seconds:.1f}"
    )


    del model

    torch.cuda.empty_cache()


    return success


def load_v25_checkpoint(
    path
):

    ckpt = torch.load(
        path,
        map_location="cpu",
        weights_only=False
    )


    model = create_candidate(
        "V25Dense64",
        8,
        input_channels=6
    )


    model.load_state_dict(
        ckpt[
            "state_dict"
        ],
        strict=True
    )


    params = int(
        sum(
            p.numel()
            for p in model.parameters()
        )
    )


    if params != EXPECTED_V25_PARAMS:

        raise RuntimeError(
            "V25 checkpoint architecture mismatch"
        )


    return model


# ============================================================
# RELEASED STORM FAILURE SUITE — 33 CONDITIONS
# ============================================================

ACC = [
    0,
    1,
    2,
]

GYRO = [
    3,
    4,
    5,
]

ALL = ACC + GYRO


def build_fault_specs():

    specs = [
        {
            "name":
                "baseline_no_failure",

            "family":
                "baseline",

            "kind":
                "none",
        },

        {
            "name":
                "gyro_total_failure",

            "family":
                "modality_outage",

            "kind":
                "zero",

            "channels":
                GYRO,
        },

        {
            "name":
                "acc_total_failure",

            "family":
                "modality_outage",

            "kind":
                "zero",

            "channels":
                ACC,
        },

        {
            "name":
                "all_sensors_failure",

            "family":
                "modality_outage",

            "kind":
                "zero",

            "channels":
                ALL,
        },
    ]


    axis_names = [
        "acc_x",
        "acc_y",
        "acc_z",
        "gyro_x",
        "gyro_y",
        "gyro_z",
    ]


    for channel, axis in enumerate(
        axis_names
    ):

        specs.append(
            {
                "name":
                    (
                        "single_axis_failure_"
                        +
                        axis
                    ),

                "family":
                    "single_axis",

                "kind":
                    "zero",

                "channels":
                    [
                        channel
                    ],
            }
        )


    for sigma in [
        0.5,
        1.0,
        2.0,
    ]:

        for label, channels in [
            (
                "gyro",
                GYRO
            ),
            (
                "acc",
                ACC
            ),
            (
                "all",
                ALL
            ),
        ]:

            specs.append(
                {
                    "name":
                        (
                            f"{label}_noise_sigma"
                            f"{sigma}"
                        ),

                    "family":
                        "gaussian_noise",

                    "kind":
                        "noise",

                    "channels":
                        channels,

                    "sigma":
                        sigma,
                }
            )


    for fraction in [
        0.10,
        0.30,
        0.50,
    ]:

        pct = int(
            fraction
            *
            100
        )


        for label, channels in [
            (
                "gyro",
                GYRO
            ),
            (
                "acc",
                ACC
            ),
        ]:

            specs.append(
                {
                    "name":
                        (
                            f"{label}_intermittent_"
                            f"{pct}pct"
                        ),

                    "family":
                        "intermittent_dropout",

                    "kind":
                        "dropout",

                    "channels":
                        channels,

                    "fraction":
                        fraction,
                }
            )


    specs.extend(
        [
            {
                "name":
                    "gyro_stuck_value",

                "family":
                    "stuck_value",

                "kind":
                    "stuck",

                "channels":
                    GYRO,
            },

            {
                "name":
                    "acc_stuck_value",

                "family":
                    "stuck_value",

                "kind":
                    "stuck",

                "channels":
                    ACC,
            },
        ]
    )


    for drift in [
        1.5,
        2.0,
        3.0,
    ]:

        for label, channels in [
            (
                "acc",
                ACC
            ),
            (
                "gyro",
                GYRO
            ),
        ]:

            specs.append(
                {
                    "name":
                        (
                            f"{label}_scale_drift_"
                            f"{drift}x"
                        ),

                    "family":
                        "scale_drift",

                    "kind":
                        "drift",

                    "channels":
                        channels,

                    "factor":
                        drift,
                }
            )


    if len(
        specs
    ) != FAULT_CASES_EXPECTED:

        raise RuntimeError(
            f"Expected 33 fault cases, got {len(specs)}"
        )


    return specs


FAULT_SPECS = build_fault_specs()


def make_transform(
    spec,
    seed,
):

    kind = spec[
        "kind"
    ]


    if kind == "none":

        return None


    if kind == "zero":

        channels = list(
            spec[
                "channels"
            ]
        )


        def transform(
            x
        ):

            x = x.clone()


            for channel in channels:

                x[
                    ...,
                    channel
                ] = 0.0


            return x


        return transform


    if kind == "noise":

        channels = list(
            spec[
                "channels"
            ]
        )

        sigma = float(
            spec[
                "sigma"
            ]
        )


        generator = torch.Generator()

        generator.manual_seed(
            int(
                seed
            )
        )


        def transform(
            x
        ):

            x = x.clone()


            for channel in channels:

                noise = torch.randn(
                    x[
                        ...,
                        channel
                    ].shape,
                    generator=generator,
                ).to(
                    x.device
                )


                x[
                    ...,
                    channel
                ] = (
                    x[
                        ...,
                        channel
                    ]
                    +
                    noise
                    *
                    sigma
                )


            return x


        return transform


    if kind == "dropout":

        channels = list(
            spec[
                "channels"
            ]
        )

        fraction = float(
            spec[
                "fraction"
            ]
        )


        generator = torch.Generator()

        generator.manual_seed(
            int(
                seed
            )
        )


        def transform(
            x
        ):

            x = x.clone()


            B, T, C = (
                x.shape
            )


            mask = (
                torch.rand(
                    B,
                    T,
                    generator=generator,
                ).to(
                    x.device
                )
                <
                fraction
            )


            for channel in channels:

                x[
                    ...,
                    channel
                ] = (
                    x[
                        ...,
                        channel
                    ]
                    .masked_fill(
                        mask,
                        0.0
                    )
                )


            return x


        return transform


    if kind == "stuck":

        channels = list(
            spec[
                "channels"
            ]
        )


        rng = np.random.RandomState(
            int(
                seed
            )
        )


        def transform(
            x
        ):

            x = x.clone()


            B, T, C = (
                x.shape
            )


            for b in range(
                B
            ):

                freeze = int(
                    rng.randint(
                        T // 4,
                        3 * T // 4
                    )
                )


                for channel in channels:

                    x[
                        b,
                        freeze:,
                        channel
                    ] = x[
                        b,
                        freeze,
                        channel
                    ]


            return x


        return transform


    if kind == "drift":

        channels = list(
            spec[
                "channels"
            ]
        )

        factor = float(
            spec[
                "factor"
            ]
        )


        def transform(
            x
        ):

            x = x.clone()


            B, T, C = (
                x.shape
            )


            ramp = torch.linspace(
                1.0,
                factor,
                T,
                device=x.device,
            ).view(
                1,
                T,
                1
            )


            for channel in channels:

                x[
                    ...,
                    channel:
                    channel + 1
                ] = (
                    x[
                        ...,
                        channel:
                        channel + 1
                    ]
                    *
                    ramp
                )


            return x


        return transform


    raise RuntimeError(
        f"Unknown fault kind={kind}"
    )


# ============================================================
# FAULT EVALUATION
# ============================================================

def run_fault_evaluation(
    model_name,
    seed,
    checkpoint,
    test_X,
    test_y,
):

    out_dir = (
        FAULT_ROOT /
        model_name /
        f"seed_{seed}"
    )


    out_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    csv_path = (
        out_dir /
        "fault_cases_33.csv"
    )


    if csv_path.exists():

        existing = pd.read_csv(
            csv_path
        )


        if len(
            existing
        ) == FAULT_CASES_EXPECTED:

            print(
                "FAULT_EVAL_ALREADY_COMPLETE:",
                model_name,
                seed
            )

            return existing


    if model_name == "STORM_native":

        model = load_storm_checkpoint(
            checkpoint
        )


    elif model_name == "V25_native":

        model = load_v25_checkpoint(
            checkpoint
        )


    else:

        raise RuntimeError(
            model_name
        )


    rows = []


    print()
    print(
        "=" * 90
    )

    print(
        "FAULT_EVAL:",
        model_name,
        seed
    )

    print(
        "=" * 90
    )


    for spec in FAULT_SPECS:

        transform = make_transform(
            spec,
            seed
        )


        metrics = evaluate_model(
            model,
            test_X,
            test_y,
            batch_size=512,
            transform=transform,
        )


        row = {
            "model":
                model_name,

            "seed":
                seed,

            "fault_name":
                spec[
                    "name"
                ],

            "family":
                spec[
                    "family"
                ],

            "accuracy":
                metrics[
                    "accuracy"
                ],

            "macro_f1":
                metrics[
                    "macro_f1"
                ],

            "n":
                metrics[
                    "n"
                ],
        }


        rows.append(
            row
        )


        print(
            "FAULT_CASE_PASS:",
            model_name,
            seed,
            spec[
                "name"
            ],
            "ACC=",
            f"{metrics['accuracy']:.6f}",
            "F1=",
            f"{metrics['macro_f1']:.6f}"
        )


    df = pd.DataFrame(
        rows
    )


    df.to_csv(
        csv_path,
        index=False
    )


    del model

    torch.cuda.empty_cache()


    return df


# ============================================================
# STATISTICS
# ============================================================

def holm_adjust(
    p_values
):

    p_values = np.asarray(
        p_values,
        dtype=float
    )


    n = len(
        p_values
    )


    order = np.argsort(
        p_values
    )


    adjusted = np.empty(
        n,
        dtype=float
    )


    running = 0.0


    for rank, index in enumerate(
        order
    ):

        value = (
            (
                n
                -
                rank
            )
            *
            p_values[
                index
            ]
        )


        running = max(
            running,
            value
        )


        adjusted[
            index
        ] = min(
            running,
            1.0
        )


    return adjusted


def paired_test_row(
    metric,
    storm_values,
    v25_values,
):

    storm_values = np.asarray(
        storm_values,
        dtype=float
    )

    v25_values = np.asarray(
        v25_values,
        dtype=float
    )


    delta = (
        v25_values
        -
        storm_values
    )


    t_stat, t_p = ttest_rel(
        v25_values,
        storm_values
    )


    try:

        w_stat, w_p = wilcoxon(
            v25_values,
            storm_values,
            zero_method="wilcox",
            alternative="two-sided",
            mode="exact",
        )

    except Exception:

        w_stat = np.nan
        w_p = np.nan


    return {
        "metric":
            metric,

        "n":
            len(
                delta
            ),

        "storm_mean":
            float(
                storm_values.mean()
            ),

        "v25_mean":
            float(
                v25_values.mean()
            ),

        "mean_delta_v25_minus_storm":
            float(
                delta.mean()
            ),

        "median_delta":
            float(
                np.median(
                    delta
                )
            ),

        "v25_seed_wins":
            int(
                np.sum(
                    delta
                    >
                    0
                )
            ),

        "storm_seed_wins":
            int(
                np.sum(
                    delta
                    <
                    0
                )
            ),

        "ties":
            int(
                np.sum(
                    delta
                    ==
                    0
                )
            ),

        "paired_t_stat":
            float(
                t_stat
            ),

        "paired_t_p":
            float(
                t_p
            ),

        "wilcoxon_stat":
            (
                float(
                    w_stat
                )
                if np.isfinite(
                    w_stat
                )
                else
                np.nan
            ),

        "wilcoxon_p":
            (
                float(
                    w_p
                )
                if np.isfinite(
                    w_p
                )
                else
                np.nan
            ),
    }


# ============================================================
# FINAL ANALYSIS
# ============================================================

def final_analysis(
    clean_rows,
    fault_frames,
):

    clean = pd.DataFrame(
        clean_rows
    )


    if len(
        clean
    ) != 10:

        raise RuntimeError(
            f"Expected 10 clean rows, got {len(clean)}"
        )


    clean = clean.sort_values(
        [
            "model",
            "seed",
        ]
    )


    clean.to_csv(
        FINAL /
        "clean_per_seed_10.csv",
        index=False
    )


    faults = pd.concat(
        fault_frames,
        ignore_index=True
    )


    if len(
        faults
    ) != 330:

        raise RuntimeError(
            f"Expected 330 fault rows, got {len(faults)}"
        )


    faults.to_csv(
        FINAL /
        "fault_cases_330.csv",
        index=False
    )


    corrupted = faults[
        faults[
            "fault_name"
        ]
        !=
        "baseline_no_failure"
    ].copy()


    recoverable = corrupted[
        corrupted[
            "fault_name"
        ]
        !=
        "all_sensors_failure"
    ].copy()


    fault_seed = (
        corrupted
        .groupby(
            [
                "model",
                "seed",
            ],
            as_index=False
        )
        .agg(
            fault_accuracy_mean=(
                "accuracy",
                "mean"
            ),

            fault_macro_f1_mean=(
                "macro_f1",
                "mean"
            ),
        )
    )


    recoverable_seed = (
        recoverable
        .groupby(
            [
                "model",
                "seed",
            ],
            as_index=False
        )
        .agg(
            recoverable_fault_accuracy_mean=(
                "accuracy",
                "mean"
            ),

            recoverable_fault_macro_f1_mean=(
                "macro_f1",
                "mean"
            ),
        )
    )


    seed_summary = (
        clean
        .merge(
            fault_seed,
            on=[
                "model",
                "seed",
            ],
            how="inner"
        )
        .merge(
            recoverable_seed,
            on=[
                "model",
                "seed",
            ],
            how="inner"
        )
    )


    seed_summary.to_csv(
        FINAL /
        "model_seed_summary_10.csv",
        index=False
    )


    family_seed = (
        faults
        .groupby(
            [
                "model",
                "seed",
                "family",
            ],
            as_index=False
        )
        .agg(
            accuracy=(
                "accuracy",
                "mean"
            ),

            macro_f1=(
                "macro_f1",
                "mean"
            ),

            case_count=(
                "fault_name",
                "count"
            ),
        )
    )


    family_seed.to_csv(
        FINAL /
        "family_per_seed_70.csv",
        index=False
    )


    family_model = (
        family_seed
        .groupby(
            [
                "model",
                "family",
            ],
            as_index=False
        )
        .agg(
            accuracy_mean=(
                "accuracy",
                "mean"
            ),

            accuracy_std=(
                "accuracy",
                "std"
            ),

            macro_f1_mean=(
                "macro_f1",
                "mean"
            ),

            macro_f1_std=(
                "macro_f1",
                "std"
            ),
        )
    )


    family_model.to_csv(
        FINAL /
        "family_model_summary_14.csv",
        index=False
    )


    model_summary = (
        seed_summary
        .groupby(
            "model",
            as_index=False
        )
        .agg(
            parameters=(
                "parameters",
                "mean"
            ),

            clean_accuracy_mean=(
                "clean_test_accuracy",
                "mean"
            ),

            clean_accuracy_std=(
                "clean_test_accuracy",
                "std"
            ),

            clean_macro_f1_mean=(
                "clean_test_macro_f1",
                "mean"
            ),

            clean_macro_f1_std=(
                "clean_test_macro_f1",
                "std"
            ),

            fault_accuracy_mean=(
                "fault_accuracy_mean",
                "mean"
            ),

            fault_accuracy_std=(
                "fault_accuracy_mean",
                "std"
            ),

            fault_macro_f1_mean=(
                "fault_macro_f1_mean",
                "mean"
            ),

            fault_macro_f1_std=(
                "fault_macro_f1_mean",
                "std"
            ),

            recoverable_fault_accuracy_mean=(
                "recoverable_fault_accuracy_mean",
                "mean"
            ),

            recoverable_fault_macro_f1_mean=(
                "recoverable_fault_macro_f1_mean",
                "mean"
            ),

            train_seconds_mean=(
                "train_seconds",
                "mean"
            ),
        )
    )


    model_summary.to_csv(
        FINAL /
        "model_summary_2.csv",
        index=False
    )


    storm_summary = (
        model_summary[
            model_summary[
                "model"
            ]
            ==
            "STORM_native"
        ]
        .iloc[
            0
        ]
    )


    v25_summary = (
        model_summary[
            model_summary[
                "model"
            ]
            ==
            "V25_native"
        ]
        .iloc[
            0
        ]
    )


    published = {
        "STORM_published_fp32_accuracy":
            0.802,

        "STORM_published_fp32_macro_f1":
            0.804,

        "STORM_published_parameters":
            19753,

        "STORM_reproduced_accuracy_mean":
            float(
                storm_summary[
                    "clean_accuracy_mean"
                ]
            ),

        "STORM_reproduced_macro_f1_mean":
            float(
                storm_summary[
                    "clean_macro_f1_mean"
                ]
            ),

        "STORM_reproduced_minus_published_accuracy":
            float(
                storm_summary[
                    "clean_accuracy_mean"
                ]
                -
                0.802
            ),

        "STORM_reproduced_minus_published_macro_f1":
            float(
                storm_summary[
                    "clean_macro_f1_mean"
                ]
                -
                0.804
            ),

        "important_boundary":
            (
                "Published STORM values are single "
                "reported reference values. "
                "Reproduced results are five-seed "
                "estimates under the reconstructed "
                "benchmark and released/native recipe."
            ),
    }


    write_json(
        FINAL /
        "published_vs_reproduced_storm.json",
        published
    )


    storm_seed = (
        seed_summary[
            seed_summary[
                "model"
            ]
            ==
            "STORM_native"
        ]
        .sort_values(
            "seed"
        )
    )


    v25_seed = (
        seed_summary[
            seed_summary[
                "model"
            ]
            ==
            "V25_native"
        ]
        .sort_values(
            "seed"
        )
    )


    if (
        storm_seed[
            "seed"
        ].tolist()
        !=
        v25_seed[
            "seed"
        ].tolist()
    ):

        raise RuntimeError(
            "Seed pairing mismatch"
        )


    metric_pairs = [
        (
            "clean_accuracy",
            "clean_test_accuracy"
        ),

        (
            "clean_macro_f1",
            "clean_test_macro_f1"
        ),

        (
            "all_fault_accuracy",
            "fault_accuracy_mean"
        ),

        (
            "all_fault_macro_f1",
            "fault_macro_f1_mean"
        ),

        (
            "recoverable_fault_accuracy",
            "recoverable_fault_accuracy_mean"
        ),

        (
            "recoverable_fault_macro_f1",
            "recoverable_fault_macro_f1_mean"
        ),
    ]


    stats_rows = []


    for metric_name, column in metric_pairs:

        stats_rows.append(
            paired_test_row(
                metric_name,
                storm_seed[
                    column
                ].to_numpy(),
                v25_seed[
                    column
                ].to_numpy(),
            )
        )


    stats = pd.DataFrame(
        stats_rows
    )


    stats[
        "paired_t_holm"
    ] = holm_adjust(
        stats[
            "paired_t_p"
        ].to_numpy()
    )


    wilcoxon_values = (
        stats[
            "wilcoxon_p"
        ]
        .fillna(
            1.0
        )
        .to_numpy()
    )


    stats[
        "wilcoxon_holm"
    ] = holm_adjust(
        wilcoxon_values
    )


    stats.to_csv(
        FINAL /
        "paired_stats_6.csv",
        index=False
    )


    comparison = {
        "clean_accuracy_delta_v25_minus_storm":
            float(
                v25_summary[
                    "clean_accuracy_mean"
                ]
                -
                storm_summary[
                    "clean_accuracy_mean"
                ]
            ),

        "clean_macro_f1_delta_v25_minus_storm":
            float(
                v25_summary[
                    "clean_macro_f1_mean"
                ]
                -
                storm_summary[
                    "clean_macro_f1_mean"
                ]
            ),

        "all_fault_accuracy_delta_v25_minus_storm":
            float(
                v25_summary[
                    "fault_accuracy_mean"
                ]
                -
                storm_summary[
                    "fault_accuracy_mean"
                ]
            ),

        "all_fault_macro_f1_delta_v25_minus_storm":
            float(
                v25_summary[
                    "fault_macro_f1_mean"
                ]
                -
                storm_summary[
                    "fault_macro_f1_mean"
                ]
            ),

        "recoverable_fault_accuracy_delta_v25_minus_storm":
            float(
                v25_summary[
                    "recoverable_fault_accuracy_mean"
                ]
                -
                storm_summary[
                    "recoverable_fault_accuracy_mean"
                ]
            ),

        "recoverable_fault_macro_f1_delta_v25_minus_storm":
            float(
                v25_summary[
                    "recoverable_fault_macro_f1_mean"
                ]
                -
                storm_summary[
                    "recoverable_fault_macro_f1_mean"
                ]
            ),

        "storm_parameters":
            EXPECTED_STORM_PARAMS,

        "v25_parameters":
            EXPECTED_V25_PARAMS,

        "v25_parameter_ratio_vs_storm":
            float(
                EXPECTED_V25_PARAMS
                /
                EXPECTED_STORM_PARAMS
            ),

        "storm_parameter_advantage_percent":
            float(
                100.0
                *
                (
                    1.0
                    -
                    EXPECTED_STORM_PARAMS
                    /
                    EXPECTED_V25_PARAMS
                )
            ),
    }


    write_json(
        FINAL /
        "direct_comparison.json",
        comparison
    )


    output_files = [
        FINAL /
        "clean_per_seed_10.csv",

        FINAL /
        "fault_cases_330.csv",

        FINAL /
        "model_seed_summary_10.csv",

        FINAL /
        "family_per_seed_70.csv",

        FINAL /
        "family_model_summary_14.csv",

        FINAL /
        "model_summary_2.csv",

        FINAL /
        "paired_stats_6.csv",

        FINAL /
        "published_vs_reproduced_storm.json",

        FINAL /
        "direct_comparison.json",
    ]


    receipt = {
        "experiment":
            "storm_v25_direct_r2",

        "status":
            "PASS",

        "dataset":
            "storm_external_r2",

        "dataset_total":
            87530,

        "models":
            [
                "STORM_native",
                "V25_native",
            ],

        "seeds":
            SEEDS,

        "training_runs_expected":
            10,

        "training_runs_complete":
            10,

        "fault_cases_per_checkpoint":
            33,

        "fault_evaluations_expected":
            330,

        "fault_evaluations_complete":
            330,

        "storm_parameters":
            EXPECTED_STORM_PARAMS,

        "v25_parameters":
            EXPECTED_V25_PARAMS,

        "storm_published_fp32_accuracy":
            0.802,

        "storm_published_fp32_macro_f1":
            0.804,

        "storm_reproduced_clean_accuracy":
            float(
                storm_summary[
                    "clean_accuracy_mean"
                ]
            ),

        "storm_reproduced_clean_macro_f1":
            float(
                storm_summary[
                    "clean_macro_f1_mean"
                ]
            ),

        "v25_clean_accuracy":
            float(
                v25_summary[
                    "clean_accuracy_mean"
                ]
            ),

        "v25_clean_macro_f1":
            float(
                v25_summary[
                    "clean_macro_f1_mean"
                ]
            ),

        "v25_fault_accuracy":
            float(
                v25_summary[
                    "fault_accuracy_mean"
                ]
            ),

        "v25_fault_macro_f1":
            float(
                v25_summary[
                    "fault_macro_f1_mean"
                ]
            ),

        "storm_fault_accuracy":
            float(
                storm_summary[
                    "fault_accuracy_mean"
                ]
            ),

        "storm_fault_macro_f1":
            float(
                storm_summary[
                    "fault_macro_f1_mean"
                ]
            ),

        "fault_application_space":
            (
                "The released STORM fault-suite "
                "transforms are applied to the "
                "already train-normalized test "
                "windows, matching the historical "
                "released experiment implementation."
            ),

        "test_used_for_checkpoint_selection":
            False,

        "original_v3r1_rerun":
            False,

        "original_v25_final_r2_rerun":
            False,

        "output_hashes":
            {
                str(
                    path.relative_to(
                        REPO
                    )
                ):
                    sha256_file(
                        path
                    )
                for path in output_files
            },

        "important_interpretation_boundary":
            (
                "Primary comparison is complete-method "
                "vs complete-method: STORM uses its "
                "native released training recipe and "
                "V25 uses the previously selected "
                "corruption-exposure recipe. "
                "This does not isolate architecture "
                "alone."
            ),

        "next_scientific_control":
            (
                "Shared-training architecture control "
                "and V25 clean-vs-exposure control may "
                "be run after inspecting this primary "
                "head-to-head result."
            ),
    }


    receipt_path = (
        FINAL /
        "storm_v25_direct_r2_final_receipt.json"
    )


    write_json(
        receipt_path,
        receipt
    )


    print()
    print(
        "=" * 100
    )

    print(
        "FINAL MODEL SUMMARY"
    )

    print(
        "=" * 100
    )

    print(
        model_summary.to_string(
            index=False
        )
    )


    print()
    print(
        "=" * 100
    )

    print(
        "DIRECT V25 - STORM COMPARISON"
    )

    print(
        "=" * 100
    )


    for key, value in comparison.items():

        print(
            key,
            "=",
            value
        )


    print()
    print(
        "=" * 100
    )

    print(
        "PAIRED STATISTICS"
    )

    print(
        "=" * 100
    )

    print(
        stats.to_string(
            index=False
        )
    )


    print()
    print(
        "FINAL_RECEIPT=",
        receipt_path
    )

    print(
        "FINAL_RECEIPT_SHA256=",
        sha256_file(
            receipt_path
        )
    )


    print(
        "DIRECT_TRAINING_RUNS=10/10"
    )

    print(
        "DIRECT_FAULT_EVALUATIONS=330/330"
    )

    print(
        "ORIGINAL_V3R1_RERUN=False"
    )

    print(
        "ORIGINAL_V25_FINAL_R2_RERUN=False"
    )

    print(
        "STORM_V25_DIRECT_R1_FINAL_ANALYSIS_PASS=True"
    )


# ============================================================
# SMOKE
# ============================================================

def run_smoke():

    verify_frozen_evidence()

    verify_v25_corruption_semantics()


    if not torch.cuda.is_available():

        raise RuntimeError(
            "CUDA unavailable"
        )


    # --------------------------------------------------------
    # STORM native QAT/deploy-sim smoke
    # --------------------------------------------------------

    storm_dir = (
        SMOKE /
        "storm_native"
    )


    if storm_dir.exists():

        shutil.rmtree(
            storm_dir
        )


    storm_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    storm_ckpt = (
        storm_dir /
        "best.pt"
    )


    cmd = storm_command(
        42,
        storm_ckpt,
        smoke=True
    )


    print()
    print(
        "RUNNING_STORM_NATIVE_SMOKE=True"
    )


    with (
        storm_dir /
        "console.log"
    ).open(
        "w"
    ) as log:

        proc = subprocess.run(
            cmd,
            cwd=str(
                REPO
            ),
            stdout=log,
            stderr=subprocess.STDOUT,
            env=os.environ.copy(),
        )


    if proc.returncode != 0:

        print(
            (
                storm_dir /
                "console.log"
            ).read_text()[
                -8000:
            ]
        )

        raise RuntimeError(
            "STORM native smoke failed"
        )


    if not storm_ckpt.exists():

        raise RuntimeError(
            "STORM smoke checkpoint missing"
        )


    storm_model = load_storm_checkpoint(
        storm_ckpt
    )


    with torch.inference_mode():

        out = storm_model(
            torch.zeros(
                2,
                64,
                6
            )
        )


    if tuple(
        out.shape
    ) != (
        2,
        8
    ):

        raise RuntimeError(
            "STORM smoke output shape failed"
        )


    print(
        "STORM_NATIVE_QAT_SMOKE_PASS=True"
    )


    # --------------------------------------------------------
    # V25 exposure backward smoke
    # --------------------------------------------------------

    seed_everything(
        42
    )


    model = create_candidate(
        "V25Dense64",
        8,
        input_channels=6
    ).cuda()


    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=1e-3
    )


    criterion = nn.CrossEntropyLoss()


    X, y = load_split_numpy(
        "train"
    )


    xb = torch.from_numpy(
        X[
            :64
        ]
    ).cuda()


    yb = torch.from_numpy(
        y[
            :64
        ]
    ).cuda()


    model.train()

    optimizer.zero_grad(
        set_to_none=True
    )


    logits = model(
        xb
    )


    loss = criterion(
        logits,
        yb
    )


    corrupted = FROZEN_CORRUPTION(
        xb.detach(),
        42,
        1,
        0,
    )


    with torch.no_grad():

        model(
            corrupted
        )


    loss.backward()

    optimizer.step()


    if not math.isfinite(
        float(
            loss.item()
        )
    ):

        raise RuntimeError(
            "V25 smoke nonfinite loss"
        )


    print(
        "V25_NATIVE_EXPOSURE_SMOKE_PASS=True"
    )


    write_json(
        SMOKE /
        "SMOKE_PASS.json",
        {
            "storm_native_qat_smoke":
                True,

            "v25_native_exposure_smoke":
                True,

            "v25_corruption_signature":
                CORRUPTION_SIGNATURE,

            "training_scope":
                "smoke_only",

            "scientific_result":
                False,
        }
    )


    print(
        "STAGE23_FULL_SMOKE_PASS=True"
    )


# ============================================================
# FULL EXPERIMENT
# ============================================================

def run_full():

    verify_frozen_evidence()

    verify_v25_corruption_semantics()


    smoke_receipt = (
        SMOKE /
        "SMOKE_PASS.json"
    )


    if not smoke_receipt.exists():

        raise RuntimeError(
            "Full run prohibited: smoke did not pass"
        )


    if not torch.cuda.is_available():

        raise RuntimeError(
            "CUDA unavailable"
        )


    train, val, test = load_all_data()


    train_X, train_y = train
    val_X, val_y = val
    test_X, test_y = test


    clean_rows = []


    print()
    print(
        "=" * 100
    )

    print(
        "PHASE A — STORM NATIVE 5-SEED TRAINING"
    )

    print(
        "=" * 100
    )


    for seed in SEEDS:

        result = run_storm_seed(
            seed,
            test_X,
            test_y,
        )


        clean_rows.append(
            result
        )


    print()
    print(
        "=" * 100
    )

    print(
        "PHASE B — V25 NATIVE EXPOSURE 5-SEED TRAINING"
    )

    print(
        "=" * 100
    )


    for seed in SEEDS:

        result = run_v25_seed(
            seed,
            train_X,
            train_y,
            val_X,
            val_y,
            test_X,
            test_y,
        )


        clean_rows.append(
            result
        )


    if len(
        clean_rows
    ) != 10:

        raise RuntimeError(
            "Expected 10 completed training runs"
        )


    print()
    print(
        "=" * 100
    )

    print(
        "PHASE C — RELEASED STORM 33-CONDITION FAULT SUITE"
    )

    print(
        "=" * 100
    )


    fault_frames = []


    for model_name in [
        "STORM_native",
        "V25_native",
    ]:

        for seed in SEEDS:

            run_dir = (
                RAW /
                model_name /
                f"seed_{seed}"
            )


            success = load_json(
                run_dir /
                "SUCCESS.json"
            )


            checkpoint = (
                REPO /
                success[
                    "checkpoint"
                ]
            )


            frame = run_fault_evaluation(
                model_name,
                seed,
                checkpoint,
                test_X,
                test_y,
            )


            fault_frames.append(
                frame
            )


    print()
    print(
        "=" * 100
    )

    print(
        "PHASE D — FINAL DIRECT ANALYSIS"
    )

    print(
        "=" * 100
    )


    final_analysis(
        clean_rows,
        fault_frames,
    )


    (
        ROOT /
        "COMPLETE"
    ).write_text(
        "STORM_V25_DIRECT_R1_COMPLETE=True\n"
    )


    print()
    print(
        "=" * 100
    )

    print(
        "STORM_V25_DIRECT_R1_WORKER_COMPLETE=True"
    )

    print(
        "=" * 100
    )


# ============================================================
# MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--mode",
        required=True,
        choices=[
            "smoke",
            "full",
        ]
    )


    args = parser.parse_args()


    if args.mode == "smoke":

        run_smoke()


    elif args.mode == "full":

        run_full()


if __name__ == "__main__":

    main()
