from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import importlib.util
import inspect
import json
import math
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

R23_RUNNER = (
    ROOT
    / "experiments/23_storm_v25_direct_comparison"
    / "run_storm_v25_direct_full_r2.py"
)

R23_RESULTS = ROOT / "results/storm_v25_direct_r2"

DATA_DIR = ROOT / "results/storm_external_r2/data/unified"

TEST_NPZ = DATA_DIR / "test.npz"
META_JSON = DATA_DIR / "meta.json"

OUT_ROOT = ROOT / "results/storm_paper_domain_r1"

SEEDS = [42, 123, 456, 789, 2026]

MODELS = [
    "STORM_native",
    "V25_native",
]

FAULT_SEED = 42

NUM_CLASSES = 8

BATCH_SIZE = 512

EXPECTED_R5_SHA = (
    "187256f9302cc84a94920b0f6ff88a6b966aa1f48acc3b9a1a2a950b09ae420c"
)

EXPECTED_PREFLIGHT_SHA = (
    "3450a5441d4240562a9623b250bed2ce2b27435b366dbe1609247699197bb86d"
)


# ============================================================
# Utility
# ============================================================

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)

            if not b:
                break

            h.update(b)

    return h.hexdigest()


def sha256_array(x: np.ndarray) -> str:
    a = np.ascontiguousarray(x)

    h = hashlib.sha256()
    h.update(str(a.dtype).encode())
    h.update(str(tuple(a.shape)).encode())
    h.update(a.tobytes(order="C"))

    return h.hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(
            obj,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n"
    )


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)

    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ============================================================
# Stage23 import
# ============================================================

def import_stage23():
    if not R23_RUNNER.exists():
        raise FileNotFoundError(R23_RUNNER)

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(R23_RUNNER.parent))

    spec = importlib.util.spec_from_file_location(
        "stage23_frozen_runner",
        R23_RUNNER,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Could not construct Stage23 import spec"
        )

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    required = [
        "load_storm_checkpoint",
        "load_v25_checkpoint",
    ]

    for name in required:
        if not hasattr(module, name):
            raise RuntimeError(
                f"Stage23 missing required interface: {name}"
            )

    return module


def call_checkpoint_loader(
    fn,
    checkpoint: Path,
    device: str,
):
    """
    Call frozen Stage23 checkpoint loader without assuming its exact
    positional signature.

    Only checkpoint path and device may be supplied automatically.
    Any other required argument causes a hard stop rather than guessing.
    """

    sig = inspect.signature(fn)

    args = []
    kwargs = {}

    for p in sig.parameters.values():

        if p.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        name = p.name.lower()

        value_known = False
        value = None

        if (
            "checkpoint" in name
            or "ckpt" in name
            or name in {"path", "pt_path", "model_path"}
        ):
            value = checkpoint
            value_known = True

        elif name == "device" or "device" in name:
            value = device
            value_known = True

        if value_known:

            if p.kind == inspect.Parameter.POSITIONAL_ONLY:
                args.append(value)
            else:
                kwargs[p.name] = value

        elif p.default is inspect.Parameter.empty:
            raise RuntimeError(
                "Unknown required Stage23 loader parameter: "
                f"{fn.__name__}{sig}, parameter={p.name}"
            )

    return fn(*args, **kwargs)


def unwrap_model(obj):
    if isinstance(obj, torch.nn.Module):
        return obj

    if isinstance(obj, (tuple, list)):
        for item in obj:
            if isinstance(item, torch.nn.Module):
                return item

    if isinstance(obj, dict):
        for key in [
            "model",
            "network",
            "net",
        ]:
            item = obj.get(key)

            if isinstance(item, torch.nn.Module):
                return item

    raise TypeError(
        "Stage23 checkpoint loader did not return a recognizable model: "
        f"{type(obj)}"
    )


# ============================================================
# Frozen inputs
# ============================================================

def load_test_and_normalization():
    meta = json.loads(META_JSON.read_text())

    with np.load(TEST_NPZ, allow_pickle=True) as z:

        if "X" in z:
            X = np.asarray(z["X"])
        elif "x" in z:
            X = np.asarray(z["x"])
        else:
            raise RuntimeError(
                f"X/x missing in {TEST_NPZ}"
            )

        if "y" in z:
            y = np.asarray(z["y"])
        elif "Y" in z:
            y = np.asarray(z["Y"])
        else:
            raise RuntimeError(
                f"y/Y missing in {TEST_NPZ}"
            )

    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y, dtype=np.int64)

    st = meta["standardization"]

    mu = np.asarray(
        st["mean"],
        dtype=np.float64,
    )

    sd = np.asarray(
        st["std"],
        dtype=np.float64,
    )

    if X.shape != (13993, 64, 6):
        raise RuntimeError(
            f"Unexpected test shape: {X.shape}"
        )

    if y.shape != (13993,):
        raise RuntimeError(
            f"Unexpected labels shape: {y.shape}"
        )

    if mu.shape != (6,) or sd.shape != (6,):
        raise RuntimeError(
            f"Unexpected normalization shapes: {mu.shape}, {sd.shape}"
        )

    if np.any(sd <= 0):
        raise RuntimeError(
            "Non-positive normalization std"
        )

    return X, y, mu, sd, meta


# ============================================================
# Paper Table-4 fault protocol
# ============================================================

def conditions():
    return [
        {
            "name": "baseline",
            "family": "baseline",
            "channels": [],
        },

        {
            "name": "gyro_total_failure",
            "family": "modality_outage",
            "channels": [3, 4, 5],
        },
        {
            "name": "acc_total_failure",
            "family": "modality_outage",
            "channels": [0, 1, 2],
        },
        {
            "name": "all_sensors_failure",
            "family": "modality_outage",
            "channels": [0, 1, 2, 3, 4, 5],
        },

        {
            "name": "single_axis_failure_acc_x",
            "family": "single_axis_outage",
            "channels": [0],
        },
        {
            "name": "single_axis_failure_acc_y",
            "family": "single_axis_outage",
            "channels": [1],
        },
        {
            "name": "single_axis_failure_acc_z",
            "family": "single_axis_outage",
            "channels": [2],
        },
        {
            "name": "single_axis_failure_gyro_x",
            "family": "single_axis_outage",
            "channels": [3],
        },
        {
            "name": "single_axis_failure_gyro_y",
            "family": "single_axis_outage",
            "channels": [4],
        },
        {
            "name": "single_axis_failure_gyro_z",
            "family": "single_axis_outage",
            "channels": [5],
        },

        {
            "name": "acc_intermittent_30pct",
            "family": "intermittent_dropout",
            "channels": [0, 1, 2],
        },
        {
            "name": "gyro_intermittent_30pct",
            "family": "intermittent_dropout",
            "channels": [3, 4, 5],
        },

        {
            "name": "acc_noise_sigma0.5",
            "family": "gaussian_noise",
            "channels": [0, 1, 2],
        },
        {
            "name": "gyro_noise_sigma0.5",
            "family": "gaussian_noise",
            "channels": [3, 4, 5],
        },

        {
            "name": "acc_stuck_value",
            "family": "stuck_value",
            "channels": [0, 1, 2],
        },
        {
            "name": "gyro_stuck_value",
            "family": "stuck_value",
            "channels": [3, 4, 5],
        },

        {
            "name": "acc_scale_drift_2.0x",
            "family": "scale_drift",
            "channels": [0, 1, 2],
        },
        {
            "name": "gyro_scale_drift_2.0x",
            "family": "scale_drift",
            "channels": [3, 4, 5],
        },
    ]


def paper_domain_transform(
    X_normalized: np.ndarray,
    condition: dict,
    mu: np.ndarray,
    sd: np.ndarray,
) -> np.ndarray:

    name = condition["name"]
    channels = np.asarray(
        condition["channels"],
        dtype=np.int64,
    )

    if name == "baseline":
        return np.asarray(
            X_normalized,
            dtype=np.float32,
        ).copy()

    # Exact inversion of the frozen train-split standardization.
    raw = (
        X_normalized.astype(np.float64)
        * sd.reshape(1, 1, 6)
        + mu.reshape(1, 1, 6)
    )

    N, T, C = raw.shape

    if name.endswith("_total_failure") or name == "all_sensors_failure":

        raw[:, :, channels] = 0.0

    elif name.startswith("single_axis_failure_"):

        raw[:, :, channels] = 0.0

    elif "intermittent_30pct" in name:

        # Fresh RNG with the single pre-registered evaluator seed for
        # each condition. Thus each model sees exactly the same windows.
        rng = np.random.RandomState(FAULT_SEED)

        temporal_mask = (
            rng.random_sample((N, T))
            < 0.30
        )

        # Same temporal mask across all selected modality channels.
        for ch in channels:
            plane = raw[:, :, ch]
            plane[temporal_mask] = 0.0
            raw[:, :, ch] = plane

    elif "noise_sigma0.5" in name:

        rng = np.random.RandomState(FAULT_SEED)

        for ch in channels:

            # sigma=0.5 in normalized-channel units means
            # raw-domain sigma = 0.5 * frozen training std.
            noise = rng.normal(
                loc=0.0,
                scale=0.5 * float(sd[ch]),
                size=(N, T),
            )

            raw[:, :, ch] += noise

    elif "stuck_value" in name:

        rng = np.random.RandomState(FAULT_SEED)

        low = T // 4
        high = (3 * T) // 4

        taus = rng.randint(
            low,
            high,
            size=N,
        )

        for b, tau in enumerate(taus):
            for ch in channels:
                raw[b, tau:, ch] = raw[b, tau, ch]

    elif "scale_drift_2.0x" in name:

        ramp = np.linspace(
            1.0,
            2.0,
            T,
            dtype=np.float64,
        ).reshape(1, T, 1)

        raw[:, :, channels] *= ramp

    else:
        raise RuntimeError(
            f"Unknown condition: {name}"
        )

    # Reapply exactly the SAME frozen training normalization.
    out = (
        raw - mu.reshape(1, 1, 6)
    ) / sd.reshape(1, 1, 6)

    out = np.asarray(
        out,
        dtype=np.float32,
    )

    if out.shape != X_normalized.shape:
        raise RuntimeError(
            f"Transform changed shape: {out.shape}"
        )

    if not np.all(np.isfinite(out)):
        raise RuntimeError(
            f"Nonfinite values after {name}"
        )

    return out


# ============================================================
# Metrics
# ============================================================

def confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    num_classes: int,
):
    cm = np.zeros(
        (num_classes, num_classes),
        dtype=np.int64,
    )

    np.add.at(
        cm,
        (y_true, y_pred),
        1,
    )

    return cm


def metrics_from_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
):
    cm = confusion_matrix(
        y_true,
        y_pred,
        NUM_CLASSES,
    )

    accuracy = float(
        np.trace(cm) / max(1, cm.sum())
    )

    f1s = []

    for c in range(NUM_CLASSES):

        tp = float(cm[c, c])
        fp = float(cm[:, c].sum() - cm[c, c])
        fn = float(cm[c, :].sum() - cm[c, c])

        denom = 2.0 * tp + fp + fn

        f1 = (
            0.0
            if denom <= 0.0
            else (2.0 * tp) / denom
        )

        f1s.append(f1)

    macro_f1 = float(np.mean(f1s))

    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "confusion_matrix": cm.tolist(),
    }


def extract_logits(output):
    if torch.is_tensor(output):
        return output

    if isinstance(output, (tuple, list)):
        if not output:
            raise RuntimeError(
                "Empty model output tuple"
            )

        return extract_logits(output[0])

    if isinstance(output, dict):
        for key in [
            "logits",
            "output",
            "pred",
            "prediction",
        ]:
            if key in output:
                return extract_logits(output[key])

    raise TypeError(
        f"Unsupported model output type: {type(output)}"
    )


def evaluate_model(
    model: torch.nn.Module,
    X: np.ndarray,
    y: np.ndarray,
    device: str,
):
    model.eval()

    preds = []

    with torch.inference_mode():

        for start in range(
            0,
            len(X),
            BATCH_SIZE,
        ):
            xb = torch.from_numpy(
                np.ascontiguousarray(
                    X[start:start + BATCH_SIZE]
                )
            ).to(
                device=device,
                dtype=torch.float32,
                non_blocking=True,
            )

            output = model(xb)

            logits = extract_logits(output)

            if logits.ndim != 2:
                raise RuntimeError(
                    f"Expected [B,K] logits, got {tuple(logits.shape)}"
                )

            if logits.shape[1] != NUM_CLASSES:
                raise RuntimeError(
                    f"Expected {NUM_CLASSES} classes, got {logits.shape[1]}"
                )

            pred = torch.argmax(
                logits,
                dim=1,
            )

            preds.append(
                pred.detach().cpu().numpy()
            )

    y_pred = np.concatenate(preds)

    if len(y_pred) != len(y):
        raise RuntimeError(
            "Prediction count mismatch"
        )

    return metrics_from_predictions(
        y,
        y_pred,
    )


# ============================================================
# Checkpoints
# ============================================================

def checkpoint_path(
    model_name: str,
    seed: int,
) -> Path:

    if model_name == "STORM_native":
        filename = "best.pt"

    elif model_name == "V25_native":
        filename = "best_model.pt"

    else:
        raise RuntimeError(
            f"Unknown model checkpoint locator: {model_name}"
        )

    p = (
        R23_RESULTS
        / "raw_runs"
        / model_name
        / f"seed_{seed}"
        / filename
    )

    if not p.exists():
        raise FileNotFoundError(
            f"Frozen Stage23 checkpoint missing: {p}"
        )

    return p


def load_all_models(stage23, device: str):
    loaded = {}

    for model_name in MODELS:
        for seed in SEEDS:

            ckpt = checkpoint_path(
                model_name,
                seed,
            )

            if model_name == "STORM_native":
                loader = stage23.load_storm_checkpoint
            elif model_name == "V25_native":
                loader = stage23.load_v25_checkpoint
            else:
                raise RuntimeError(model_name)

            print(
                f"LOADING model={model_name} seed={seed} "
                f"checkpoint={ckpt}"
            )

            obj = call_checkpoint_loader(
                loader,
                ckpt,
                device,
            )

            model = unwrap_model(obj).to(device)

            model.eval()

            loaded[(model_name, seed)] = {
                "model": model,
                "checkpoint": ckpt,
                "checkpoint_sha256": sha256_file(ckpt),
            }

    return loaded


# ============================================================
# Stage23 clean reference gate
# ============================================================

def find_column(
    fieldnames,
    candidates,
):
    lowered = {
        str(c).lower(): c
        for c in fieldnames
    }

    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]

    return None


def load_stage23_clean_reference():
    """
    Read canonical per-seed clean metrics directly from the
    frozen Stage23 SUCCESS.json receipts.

    This avoids relying on any newly guessed final-analysis
    filename and preserves the original per-run evidence.
    """

    ref = {}

    receipt_paths = []

    for model_name in MODELS:
        for seed in SEEDS:

            success_path = (
                R23_RESULTS
                / "raw_runs"
                / model_name
                / f"seed_{seed}"
                / "SUCCESS.json"
            )

            if not success_path.exists():
                raise FileNotFoundError(
                    "Canonical Stage23 SUCCESS receipt missing: "
                    f"{success_path}"
                )

            obj = json.loads(
                success_path.read_text()
            )

            required = [
                "clean_test_accuracy",
                "clean_test_macro_f1",
            ]

            missing = [
                key
                for key in required
                if key not in obj
            ]

            if missing:
                raise RuntimeError(
                    "Stage23 SUCCESS receipt missing clean fields: "
                    f"path={success_path}, missing={missing}"
                )

            key = (
                model_name,
                int(seed),
            )

            ref[key] = {
                "accuracy":
                    float(
                        obj["clean_test_accuracy"]
                    ),
                "macro_f1":
                    float(
                        obj["clean_test_macro_f1"]
                    ),
            }

            receipt_paths.append(
                str(success_path)
            )

    expected = {
        (m, s)
        for m in MODELS
        for s in SEEDS
    }

    if set(ref) != expected:
        raise RuntimeError(
            "Stage23 SUCCESS clean reference keys do not "
            f"match expected 10 model/seed pairs: {sorted(ref)}"
        )

    return receipt_paths, ref


# ============================================================
# Paper published reference
# ============================================================

PUBLISHED_TABLE10 = {
    "gyro_total_failure": (0.603, 0.615),
    "acc_total_failure": (0.471, 0.396),
    "all_sensors_failure": (0.173, 0.037),

    "single_axis_failure_acc_x": (0.686, 0.675),
    "single_axis_failure_acc_z": (0.597, 0.576),
    "single_axis_failure_gyro_y": (0.634, 0.657),
    "single_axis_failure_gyro_z": (0.756, 0.772),

    "gyro_noise_sigma0.5": (0.478, 0.491),
    "acc_noise_sigma0.5": (0.314, 0.313),

    "gyro_intermittent_30pct": (0.716, 0.726),
    "acc_intermittent_30pct": (0.487, 0.475),

    "gyro_stuck_value": (0.636, 0.643),
    "acc_stuck_value": (0.714, 0.722),

    "acc_scale_drift_2.0x": (0.478, 0.494),
    "gyro_scale_drift_2.0x": (0.705, 0.692),
}


# ============================================================
# Statistical helpers
# ============================================================

def mean_std(values):
    a = np.asarray(values, dtype=np.float64)

    return (
        float(np.mean(a)),
        float(np.std(a, ddof=1))
        if len(a) > 1
        else 0.0,
    )


def holm_adjust(pvalues):
    p = np.asarray(
        pvalues,
        dtype=np.float64,
    )

    n = len(p)

    order = np.argsort(p)

    adjusted = np.empty(
        n,
        dtype=np.float64,
    )

    running = 0.0

    for rank, idx in enumerate(order):

        adj = (
            (n - rank)
            * float(p[idx])
        )

        running = max(
            running,
            adj,
        )

        adjusted[idx] = min(
            1.0,
            running,
        )

    return adjusted.tolist()


# ============================================================
# Smoke
# ============================================================

def run_smoke():
    out = OUT_ROOT / "smoke_r1"

    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    seed_everything(FAULT_SEED)

    X, y, mu, sd, meta = (
        load_test_and_normalization()
    )

    # Deterministic transformation checks.
    smoke_conditions = [
        conditions()[0],
        conditions()[2],
        conditions()[12],
    ]

    transformation_checks = []

    n = 512

    for cond in smoke_conditions:

        a = paper_domain_transform(
            X[:n],
            cond,
            mu,
            sd,
        )

        b = paper_domain_transform(
            X[:n],
            cond,
            mu,
            sd,
        )

        deterministic = bool(
            np.array_equal(a, b)
        )

        if not deterministic:
            raise RuntimeError(
                f"Nondeterministic transform: {cond['name']}"
            )

        transformation_checks.append({
            "condition": cond["name"],
            "shape": list(a.shape),
            "sha256": sha256_array(a),
            "deterministic": deterministic,
            "finite": bool(
                np.all(np.isfinite(a))
            ),
        })

    # Strong raw-zero semantic check for acc outage.
    acc_out = paper_domain_transform(
        X[:n],
        {
            "name": "acc_total_failure",
            "family": "modality_outage",
            "channels": [0, 1, 2],
        },
        mu,
        sd,
    )

    expected_zero_norm = (
        -mu / sd
    ).astype(np.float32)

    for ch in [0, 1, 2]:

        expected = float(
            expected_zero_norm[ch]
        )

        max_err = float(
            np.max(
                np.abs(
                    acc_out[:, :, ch]
                    - expected
                )
            )
        )

        if max_err > 1e-6:
            raise RuntimeError(
                "Raw outage normalization semantic mismatch "
                f"channel={ch}, max_err={max_err}"
            )

    stage23 = import_stage23()

    device = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    smoke_metrics = []

    # Only two seed-42 models for smoke.
    for model_name in MODELS:

        seed = 42

        ckpt = checkpoint_path(
            model_name,
            seed,
        )

        loader = (
            stage23.load_storm_checkpoint
            if model_name == "STORM_native"
            else stage23.load_v25_checkpoint
        )

        obj = call_checkpoint_loader(
            loader,
            ckpt,
            device,
        )

        model = unwrap_model(obj).to(device)

        for cond in smoke_conditions:

            Xc = paper_domain_transform(
                X[:n],
                cond,
                mu,
                sd,
            )

            m = evaluate_model(
                model,
                Xc,
                y[:n],
                device,
            )

            smoke_metrics.append({
                "model": model_name,
                "seed": seed,
                "condition": cond["name"],
                "accuracy": m["accuracy"],
                "macro_f1": m["macro_f1"],
            })

        del model
        del obj

        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    receipt = {
        "protocol":
            "STORM_PAPER_DOMAIN_FAULTS_R1",
        "mode":
            "smoke",
        "n":
            n,
        "fault_seed":
            FAULT_SEED,
        "transformations":
            transformation_checks,
        "metrics":
            smoke_metrics,
        "training_performed":
            False,
        "full_test_evaluation_performed":
            False,
        "smoke_pass":
            True,
    }

    write_json(
        out / "smoke_receipt.json",
        receipt,
    )

    print()
    print("SMOKE RESULTS")

    for r in smoke_metrics:
        print(
            r["model"],
            r["condition"],
            f"acc={r['accuracy']:.6f}",
            f"f1={r['macro_f1']:.6f}",
        )

    print()
    print(
        "PAPER_DOMAIN_SMOKE_R1_PASS=True"
    )

    print(
        "TRAINING_PERFORMED=False"
    )

    print(
        "FULL_TEST_EVALUATION_PERFORMED=False"
    )


# ============================================================
# Full evaluation
# ============================================================

def run_full():
    out = OUT_ROOT / "full_r1"

    out.mkdir(
        parents=True,
        exist_ok=True,
    )

    seed_everything(FAULT_SEED)

    X, y, mu, sd, meta = (
        load_test_and_normalization()
    )

    stage23 = import_stage23()

    device = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(
        "DEVICE=",
        device,
    )

    if device != "cuda":
        print(
            "WARNING: CUDA unavailable; evaluation remains valid "
            "but will be slower."
        )

    clean_ref_path, clean_ref = (
        load_stage23_clean_reference()
    )

    print(
        "STAGE23_CLEAN_REFERENCE=",
        clean_ref_path,
    )

    # --------------------------------------------------------
    # Load all ten already-trained checkpoints.
    # --------------------------------------------------------

    models = load_all_models(
        stage23,
        device,
    )

    if len(models) != 10:
        raise RuntimeError(
            f"Expected 10 loaded models, got {len(models)}"
        )

    per_case = []
    transform_manifest = []

    conds = conditions()

    if len(conds) != 18:
        raise RuntimeError(
            "Expected exactly 18 paper-domain conditions"
        )

    # --------------------------------------------------------
    # Condition outer loop:
    # one corrupted tensor shared identically by all ten models.
    # --------------------------------------------------------

    for ci, cond in enumerate(conds):

        name = cond["name"]

        print()
        print(
            "=" * 100
        )
        print(
            f"CONDITION {ci + 1:02d}/{len(conds)}: {name}"
        )
        print(
            "=" * 100
        )

        t_transform = time.time()

        Xc = paper_domain_transform(
            X,
            cond,
            mu,
            sd,
        )

        transform_seconds = (
            time.time()
            - t_transform
        )

        xhash = sha256_array(Xc)

        transform_manifest.append({
            "condition": name,
            "family": cond["family"],
            "channels":
                json.dumps(cond["channels"]),
            "tensor_sha256":
                xhash,
            "shape":
                json.dumps(list(Xc.shape)),
            "dtype":
                str(Xc.dtype),
            "transform_seconds":
                transform_seconds,
        })

        print(
            "TRANSFORM_SHA256=",
            xhash,
        )

        for model_name in MODELS:
            for seed in SEEDS:

                rec = models[
                    (model_name, seed)
                ]

                t0 = time.time()

                m = evaluate_model(
                    rec["model"],
                    Xc,
                    y,
                    device,
                )

                elapsed = (
                    time.time()
                    - t0
                )

                row = {
                    "model":
                        model_name,
                    "seed":
                        seed,
                    "condition":
                        name,
                    "family":
                        cond["family"],
                    "accuracy":
                        m["accuracy"],
                    "macro_f1":
                        m["macro_f1"],
                    "n":
                        len(y),
                    "checkpoint":
                        str(rec["checkpoint"]),
                    "checkpoint_sha256":
                        rec["checkpoint_sha256"],
                    "condition_tensor_sha256":
                        xhash,
                    "evaluation_seconds":
                        elapsed,
                }

                per_case.append(row)

                print(
                    f"{model_name:12s}",
                    f"seed={seed:4d}",
                    f"acc={m['accuracy']:.6f}",
                    f"f1={m['macro_f1']:.6f}",
                    f"time={elapsed:.2f}s",
                )

                # --------------------------------------------
                # Clean-baseline gate against canonical Stage23
                # --------------------------------------------

                if name == "baseline":

                    ref = clean_ref[
                        (model_name, seed)
                    ]

                    acc_err = abs(
                        m["accuracy"]
                        - ref["accuracy"]
                    )

                    f1_err = abs(
                        m["macro_f1"]
                        - ref["macro_f1"]
                    )

                    # Metrics must be the SAME predictions under clean
                    # input. Allow only floating reporting noise.
                    if (
                        acc_err > 1e-10
                        or f1_err > 1e-10
                    ):
                        raise RuntimeError(
                            "CLEAN_BASELINE_GATE_FAILED "
                            f"model={model_name} seed={seed} "
                            f"computed_acc={m['accuracy']} "
                            f"reference_acc={ref['accuracy']} "
                            f"computed_f1={m['macro_f1']} "
                            f"reference_f1={ref['macro_f1']} "
                            f"acc_err={acc_err} "
                            f"f1_err={f1_err}"
                        )

        del Xc
        gc.collect()

    print()
    print(
        "CLEAN_BASELINE_GATE_PASS_10_OF_10=True"
    )

    # --------------------------------------------------------
    # Write per-case results.
    # --------------------------------------------------------

    case_csv = (
        out
        / "paper_domain_cases_180.csv"
    )

    fields = list(
        per_case[0].keys()
    )

    with case_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        w.writeheader()
        w.writerows(per_case)

    manifest_csv = (
        out
        / "condition_tensor_manifest_18.csv"
    )

    with manifest_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(
                transform_manifest[0].keys()
            ),
        )

        w.writeheader()
        w.writerows(
            transform_manifest
        )

    # --------------------------------------------------------
    # Model-condition summaries: 36 rows.
    # --------------------------------------------------------

    model_condition = []

    for model_name in MODELS:
        for cond in conds:

            rows = [
                r
                for r in per_case
                if r["model"] == model_name
                and r["condition"] == cond["name"]
            ]

            if len(rows) != 5:
                raise RuntimeError(
                    f"Expected 5 rows for {model_name}/{cond['name']}"
                )

            acc_mean, acc_std = mean_std(
                [r["accuracy"] for r in rows]
            )

            f1_mean, f1_std = mean_std(
                [r["macro_f1"] for r in rows]
            )

            model_condition.append({
                "model":
                    model_name,
                "condition":
                    cond["name"],
                "family":
                    cond["family"],
                "accuracy_mean":
                    acc_mean,
                "accuracy_std":
                    acc_std,
                "macro_f1_mean":
                    f1_mean,
                "macro_f1_std":
                    f1_std,
                "n_seeds":
                    5,
            })

    with (
        out / "model_condition_summary_36.csv"
    ).open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(
                model_condition[0].keys()
            ),
        )

        w.writeheader()
        w.writerows(
            model_condition
        )

    # --------------------------------------------------------
    # Family per-seed + summaries.
    # --------------------------------------------------------

    fault_families = [
        "modality_outage",
        "single_axis_outage",
        "intermittent_dropout",
        "gaussian_noise",
        "stuck_value",
        "scale_drift",
    ]

    family_seed_rows = []

    for model_name in MODELS:
        for seed in SEEDS:
            for family in fault_families:

                rows = [
                    r
                    for r in per_case
                    if r["model"] == model_name
                    and r["seed"] == seed
                    and r["family"] == family
                ]

                if not rows:
                    raise RuntimeError(
                        f"No rows for {model_name}/{seed}/{family}"
                    )

                family_seed_rows.append({
                    "model":
                        model_name,
                    "seed":
                        seed,
                    "family":
                        family,
                    "conditions":
                        len(rows),
                    "accuracy":
                        float(np.mean(
                            [r["accuracy"] for r in rows]
                        )),
                    "macro_f1":
                        float(np.mean(
                            [r["macro_f1"] for r in rows]
                        )),
                })

    with (
        out / "family_per_seed_60.csv"
    ).open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(
                family_seed_rows[0].keys()
            ),
        )

        w.writeheader()
        w.writerows(
            family_seed_rows
        )

    family_summary = []

    for model_name in MODELS:
        for family in fault_families:

            rows = [
                r
                for r in family_seed_rows
                if r["model"] == model_name
                and r["family"] == family
            ]

            acc_mean, acc_std = mean_std(
                [r["accuracy"] for r in rows]
            )

            f1_mean, f1_std = mean_std(
                [r["macro_f1"] for r in rows]
            )

            family_summary.append({
                "model":
                    model_name,
                "family":
                    family,
                "accuracy_mean":
                    acc_mean,
                "accuracy_std":
                    acc_std,
                "macro_f1_mean":
                    f1_mean,
                "macro_f1_std":
                    f1_std,
                "n_seeds":
                    5,
            })

    with (
        out / "family_model_summary_12.csv"
    ).open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(
                family_summary[0].keys()
            ),
        )

        w.writeheader()
        w.writerows(
            family_summary
        )

    # --------------------------------------------------------
    # Per-seed aggregate.
    # --------------------------------------------------------

    aggregate_seed = []

    for model_name in MODELS:
        for seed in SEEDS:

            rows = [
                r
                for r in per_case
                if r["model"] == model_name
                and r["seed"] == seed
            ]

            baseline = [
                r for r in rows
                if r["condition"] == "baseline"
            ]

            if len(baseline) != 1:
                raise RuntimeError(
                    "Baseline row mismatch"
                )

            faults = [
                r for r in rows
                if r["condition"] != "baseline"
            ]

            recoverable = [
                r for r in faults
                if r["condition"] != "all_sensors_failure"
            ]

            family_rows = [
                r
                for r in family_seed_rows
                if r["model"] == model_name
                and r["seed"] == seed
            ]

            if (
                len(faults) != 17
                or len(recoverable) != 16
                or len(family_rows) != 6
            ):
                raise RuntimeError(
                    "Aggregate condition-count mismatch"
                )

            aggregate_seed.append({
                "model":
                    model_name,
                "seed":
                    seed,

                "clean_accuracy":
                    baseline[0]["accuracy"],
                "clean_macro_f1":
                    baseline[0]["macro_f1"],

                "all_fault_accuracy":
                    float(np.mean(
                        [r["accuracy"] for r in faults]
                    )),
                "all_fault_macro_f1":
                    float(np.mean(
                        [r["macro_f1"] for r in faults]
                    )),

                "recoverable_fault_accuracy":
                    float(np.mean(
                        [r["accuracy"] for r in recoverable]
                    )),
                "recoverable_fault_macro_f1":
                    float(np.mean(
                        [r["macro_f1"] for r in recoverable]
                    )),

                "family_balanced_accuracy":
                    float(np.mean(
                        [r["accuracy"] for r in family_rows]
                    )),
                "family_balanced_macro_f1":
                    float(np.mean(
                        [r["macro_f1"] for r in family_rows]
                    )),
            })

    with (
        out / "aggregate_per_seed_10.csv"
    ).open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(
                aggregate_seed[0].keys()
            ),
        )

        w.writeheader()
        w.writerows(
            aggregate_seed
        )

    # --------------------------------------------------------
    # Aggregate model summary.
    # --------------------------------------------------------

    aggregate_model = []

    metric_names = [
        "clean_accuracy",
        "clean_macro_f1",
        "all_fault_accuracy",
        "all_fault_macro_f1",
        "recoverable_fault_accuracy",
        "recoverable_fault_macro_f1",
        "family_balanced_accuracy",
        "family_balanced_macro_f1",
    ]

    for model_name in MODELS:

        rows = [
            r
            for r in aggregate_seed
            if r["model"] == model_name
        ]

        rec = {
            "model":
                model_name,
            "n_seeds":
                len(rows),
        }

        for metric in metric_names:

            mean, std = mean_std(
                [r[metric] for r in rows]
            )

            rec[f"{metric}_mean"] = mean
            rec[f"{metric}_std"] = std

        aggregate_model.append(rec)

    with (
        out / "aggregate_model_summary_2.csv"
    ).open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(
                aggregate_model[0].keys()
            ),
        )

        w.writeheader()
        w.writerows(
            aggregate_model
        )

    # --------------------------------------------------------
    # Paired V25 - STORM statistics.
    # --------------------------------------------------------

    paired = []

    try:
        from scipy import stats
        scipy_available = True
    except Exception:
        stats = None
        scipy_available = False

    for metric in metric_names:

        storm = np.asarray(
            [
                next(
                    r[metric]
                    for r in aggregate_seed
                    if r["model"] == "STORM_native"
                    and r["seed"] == seed
                )
                for seed in SEEDS
            ],
            dtype=np.float64,
        )

        v25 = np.asarray(
            [
                next(
                    r[metric]
                    for r in aggregate_seed
                    if r["model"] == "V25_native"
                    and r["seed"] == seed
                )
                for seed in SEEDS
            ],
            dtype=np.float64,
        )

        delta = v25 - storm

        row = {
            "metric":
                metric,
            "delta_v25_minus_storm_mean":
                float(np.mean(delta)),
            "delta_v25_minus_storm_std":
                float(np.std(delta, ddof=1)),
            "v25_wins":
                int(np.sum(delta > 0)),
            "storm_wins":
                int(np.sum(delta < 0)),
            "ties":
                int(np.sum(delta == 0)),
            "paired_t_p":
                None,
            "wilcoxon_p":
                None,
        }

        if scipy_available:

            try:
                row["paired_t_p"] = float(
                    stats.ttest_rel(
                        v25,
                        storm,
                    ).pvalue
                )
            except Exception:
                pass

            try:
                row["wilcoxon_p"] = float(
                    stats.wilcoxon(
                        v25,
                        storm,
                        zero_method="wilcox",
                        alternative="two-sided",
                        method="auto",
                    ).pvalue
                )
            except Exception:
                pass

        paired.append(row)

    valid_t = [
        r["paired_t_p"]
        for r in paired
        if r["paired_t_p"] is not None
        and math.isfinite(r["paired_t_p"])
    ]

    if len(valid_t) == len(paired):

        adjusted = holm_adjust(
            valid_t
        )

        for row, p_adj in zip(
            paired,
            adjusted,
        ):
            row["paired_t_p_holm"] = p_adj

    else:
        for row in paired:
            row["paired_t_p_holm"] = None

    with (
        out / "paired_aggregate_stats_8.csv"
    ).open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(
                paired[0].keys()
            ),
        )

        w.writeheader()
        w.writerows(paired)

    # --------------------------------------------------------
    # Published Table-10 comparison.
    #
    # Descriptive ONLY.
    # Exact paper training provenance remains unresolved.
    # --------------------------------------------------------

    published_rows = []

    for condition, (
        paper_acc,
        paper_f1,
    ) in PUBLISHED_TABLE10.items():

        reproduced = next(
            r
            for r in model_condition
            if r["model"] == "STORM_native"
            and r["condition"] == condition
        )

        published_rows.append({
            "condition":
                condition,
            "published_accuracy":
                paper_acc,
            "reproduced_accuracy_mean":
                reproduced["accuracy_mean"],
            "accuracy_gap_reproduced_minus_published":
                reproduced["accuracy_mean"]
                - paper_acc,

            "published_macro_f1":
                paper_f1,
            "reproduced_macro_f1_mean":
                reproduced["macro_f1_mean"],
            "macro_f1_gap_reproduced_minus_published":
                reproduced["macro_f1_mean"]
                - paper_f1,

            "interpretation":
                "DESCRIPTIVE_ONLY_EXACT_PAPER_TRAINING_PROVENANCE_OPEN",
        })

    with (
        out / "published_table10_comparison.csv"
    ).open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        w = csv.DictWriter(
            f,
            fieldnames=list(
                published_rows[0].keys()
            ),
        )

        w.writeheader()
        w.writerows(
            published_rows
        )

    # --------------------------------------------------------
    # Final receipt.
    # --------------------------------------------------------

    receipt = {
        "protocol":
            "STORM_PAPER_DOMAIN_FAULTS_R1",

        "status":
            "COMPLETE",

        "scientific_scope": (
            "Paper Table-4 raw-sensor-domain faults applied "
            "before frozen train-split normalization to the "
            "existing Stage23 STORM and V25 checkpoints."
        ),

        "models":
            MODELS,

        "seeds":
            SEEDS,

        "conditions":
            [c["name"] for c in conds],

        "condition_count":
            18,

        "fault_count_excluding_baseline":
            17,

        "evaluations":
            len(per_case),

        "expected_evaluations":
            180,

        "fault_seed":
            FAULT_SEED,

        "fault_seed_is_paper_proven":
            False,

        "fault_seed_status":
            "PRE_REGISTERED_COMPARATIVE_EVALUATOR_SEED",

        "clean_stage23_gate":
            "PASS_10_OF_10",

        "paper_domain_preflight_sha256":
            EXPECTED_PREFLIGHT_SHA,

        "public_provenance_r5_sha256":
            EXPECTED_R5_SHA,

        "stage23_clean_reference":
            str(clean_ref_path),

        "training_performed":
            False,

        "checkpoints_modified":
            False,

        "stage23_results_modified":
            False,

        "paper_training_provenance":
            "UNRESOLVED_CASE_C",

        "important_separation": {
            "stage23":
                "released-code normalized-space 33-condition suite",
            "stage24":
                "paper Table-4 raw-domain 18-condition suite",
            "results_should_not_be_merged":
                True,
        },

        "output_files": {
            "cases":
                "paper_domain_cases_180.csv",
            "condition_summary":
                "model_condition_summary_36.csv",
            "family_per_seed":
                "family_per_seed_60.csv",
            "family_summary":
                "family_model_summary_12.csv",
            "aggregate_per_seed":
                "aggregate_per_seed_10.csv",
            "aggregate_model":
                "aggregate_model_summary_2.csv",
            "paired_stats":
                "paired_aggregate_stats_8.csv",
            "published_reference":
                "published_table10_comparison.csv",
            "condition_tensor_manifest":
                "condition_tensor_manifest_18.csv",
        },
    }

    if len(per_case) != 180:
        raise RuntimeError(
            f"Expected 180 case rows, got {len(per_case)}"
        )

    write_json(
        out / "final_receipt.json",
        receipt,
    )

    # --------------------------------------------------------
    # Console summary.
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print("PAPER-DOMAIN STAGE24 FINAL SUMMARY")
    print("=" * 100)

    for rec in aggregate_model:

        print()
        print(
            rec["model"]
        )

        print(
            " clean_accuracy=",
            f"{rec['clean_accuracy_mean']:.6f}",
            "clean_f1=",
            f"{rec['clean_macro_f1_mean']:.6f}",
        )

        print(
            " all_fault_accuracy=",
            f"{rec['all_fault_accuracy_mean']:.6f}",
            "all_fault_f1=",
            f"{rec['all_fault_macro_f1_mean']:.6f}",
        )

        print(
            " recoverable_accuracy=",
            f"{rec['recoverable_fault_accuracy_mean']:.6f}",
            "recoverable_f1=",
            f"{rec['recoverable_fault_macro_f1_mean']:.6f}",
        )

        print(
            " family_balanced_accuracy=",
            f"{rec['family_balanced_accuracy_mean']:.6f}",
            "family_balanced_f1=",
            f"{rec['family_balanced_macro_f1_mean']:.6f}",
        )

    print()
    print(
        "CASE_ROWS=",
        len(per_case),
    )

    print(
        "CLEAN_BASELINE_GATE_PASS_10_OF_10=True"
    )

    print(
        "STAGE24_PAPER_DOMAIN_FULL_R1_COMPLETE=True"
    )

    print(
        "TRAINING_PERFORMED=False"
    )

    print(
        "CHECKPOINTS_MODIFIED=False"
    )

    print(
        "STAGE23_RESULTS_MODIFIED=False"
    )


# ============================================================
# Main
# ============================================================

def main():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--mode",
        choices=[
            "smoke",
            "full",
        ],
        required=True,
    )

    args = ap.parse_args()

    print(
        "=" * 100
    )

    print(
        "STORM PAPER-DOMAIN FAULT EVALUATOR R1"
    )

    print(
        "=" * 100
    )

    print(
        "MODE=",
        args.mode,
    )

    print(
        "TRAINING_ALLOWED=False"
    )

    print(
        "STAGE23_CHECKPOINTS_READ_ONLY=True"
    )

    if args.mode == "smoke":
        run_smoke()
    else:
        run_full()


if __name__ == "__main__":
    main()
