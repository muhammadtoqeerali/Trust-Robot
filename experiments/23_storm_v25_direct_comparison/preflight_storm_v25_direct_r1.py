from pathlib import Path
import ast
import hashlib
import inspect
import json
import re
import sys

import numpy as np
import torch


REPO = Path.cwd()

ROOT = (
    REPO /
    "results" /
    "storm_v25_direct_r1"
)

PREFLIGHT = (
    ROOT /
    "preflight"
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

STORM_REF = (
    REPO /
    "external_references" /
    "storm_2026_upstream"
)

V25_CODE = (
    REPO /
    "experiments" /
    "17_v25_screening"
)

V25_ABLATION_CODE = (
    REPO /
    "experiments" /
    "18_v25_training_ablation"
)


sys.path.insert(
    0,
    str(STORM_REF)
)

sys.path.insert(
    0,
    str(V25_CODE)
)


from storm import STORM, STORMConfig

from v25_candidates import create_candidate


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


SEEDS = [
    42,
    123,
    456,
    789,
    2026,
]


def sha256(path):

    h = hashlib.sha256()

    with Path(path).open("rb") as f:

        for block in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(block)

    return h.hexdigest()


def load_json(path):

    return json.loads(
        Path(path).read_text()
    )


print("=" * 100)
print("STORM vs V25 DIRECT COMPARISON R1 — PREFLIGHT")
print("=" * 100)


# ==========================================================
# 1. Data
# ==========================================================

receipt = load_json(
    DATA_RECEIPT
)


if receipt.get(
    "published_table2_exact_match"
) is not True:

    raise RuntimeError(
        "Stage-22 Table-2 evidence not PASS"
    )


data_rows = {}


all_subjects = {}


for split in [
    "train",
    "val",
    "test",
]:

    path = (
        DATA_ROOT /
        f"{split}.npz"
    )


    if not path.exists():

        raise FileNotFoundError(
            path
        )


    d = np.load(
        path,
        allow_pickle=False
    )


    X = d["X"]

    y = d["y"].astype(
        np.int64
    )

    subj = d["subj"].astype(
        np.int64
    )


    if X.shape[1:] != (
        64,
        6
    ):

        raise RuntimeError(
            f"{split}: shape mismatch {X.shape}"
        )


    if y.min() != 0 or y.max() != 7:

        raise RuntimeError(
            f"{split}: labels not 0..7"
        )


    data_rows[
        split
    ] = {
        "N":
            int(len(y)),

        "subjects":
            int(
                np.unique(
                    subj
                ).size
            ),

        "class_counts":
            np.bincount(
                y,
                minlength=8
            ).tolist(),
    }


    all_subjects[
        split
    ] = set(
        subj.tolist()
    )


if (
    all_subjects["train"]
    &
    all_subjects["val"]
):

    raise RuntimeError(
        "train/val subject overlap"
    )


if (
    all_subjects["train"]
    &
    all_subjects["test"]
):

    raise RuntimeError(
        "train/test subject overlap"
    )


if (
    all_subjects["val"]
    &
    all_subjects["test"]
):

    raise RuntimeError(
        "val/test subject overlap"
    )


if (
    data_rows["train"]["N"]
    +
    data_rows["val"]["N"]
    +
    data_rows["test"]["N"]
    !=
    87530
):

    raise RuntimeError(
        "Dataset total is not 87,530"
    )


print(
    "DATA_TRAIN_N=",
    data_rows[
        "train"
    ][
        "N"
    ]
)

print(
    "DATA_VAL_N=",
    data_rows[
        "val"
    ][
        "N"
    ]
)

print(
    "DATA_TEST_N=",
    data_rows[
        "test"
    ][
        "N"
    ]
)

print(
    "DATA_TOTAL_N=87530"
)

print(
    "DATA_INPUT_SHAPE=[B,64,6]"
)

print(
    "DATA_CLASSES=8"
)

print(
    "DATA_SUBJECT_DISJOINT=True"
)


# ==========================================================
# 2. Instantiate published STORM architecture
# ==========================================================

storm_cfg = STORMConfig(
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


storm_model = STORM(
    storm_cfg
)


storm_params = int(
    sum(
        p.numel()
        for p in storm_model.parameters()
    )
)


x = torch.zeros(
    4,
    64,
    6
)


storm_model.eval()


with torch.inference_mode():

    storm_logits = storm_model(
        x
    )


if tuple(
    storm_logits.shape
) != (
    4,
    8
):

    raise RuntimeError(
        f"STORM output shape={storm_logits.shape}"
    )


print()
print(
    "STORM_PAPER_ARCH="
    "d32_depth2_heads4_window16"
)

print(
    "STORM_PARAMETERS=",
    storm_params
)

print(
    "STORM_FORWARD_T64_PASS=True"
)


# Published count is used as a verification target,
# but allow a tiny implementation-accounting difference
# to be reported rather than silently hidden.
published_storm_params = 19753

storm_param_delta = (
    storm_params
    -
    published_storm_params
)


print(
    "STORM_PUBLISHED_PARAMETERS=",
    published_storm_params
)

print(
    "STORM_PARAMETER_DELTA_VS_PUBLISHED=",
    storm_param_delta
)


# ==========================================================
# 3. Instantiate V25 on the exact same task
# ==========================================================

v25 = create_candidate(
    "V25Dense64",
    8,
    input_channels=6
)


v25_params = int(
    sum(
        p.numel()
        for p in v25.parameters()
    )
)


v25.eval()


with torch.inference_mode():

    v25_logits = v25(
        x
    )


if tuple(
    v25_logits.shape
) != (
    4,
    8
):

    raise RuntimeError(
        f"V25 output shape={v25_logits.shape}"
    )


print()
print(
    "V25_ARCH=V25Dense64"
)

print(
    "V25_PARAMETERS=",
    v25_params
)

print(
    "V25_FORWARD_T64_PASS=True"
)


# ==========================================================
# 4. Inspect released train.py defaults directly
# ==========================================================

train_source_path = (
    PREFLIGHT /
    "storm_train_507dc30.py"
)


train_source = (
    train_source_path.read_text()
)


expected_released_tokens = [
    'default=200',
    'default=256',
    'default=6e-4',
    'default=8e-4',
    'default="weighted"',
    'default=0.30',
    'default=0.03',
    'default=0.15',
    'default="periodic"',
]


for token in expected_released_tokens:

    if token not in train_source:

        raise RuntimeError(
            "Expected released STORM training "
            f"token absent: {token}"
        )


print()
print(
    "STORM_RELEASED_TRAIN_SOURCE_AUDIT_PASS=True"
)


# ==========================================================
# 5. Inspect historical experiments.py recipe
# ==========================================================

hist_path = (
    PREFLIGHT /
    "storm_historical_experiments_cef59e1.py"
)


hist_source = hist_path.read_text()


historical_required = {
    '"batch": 256':
        "batch",

    '"lr": 6e-4':
        "lr",

    '"weight_decay": 8e-4':
        "weight_decay",

    '"scheduler": "onecycle"':
        "scheduler",

    '"early_stop": 15':
        "early_stop",

    '"ema_decay": 0.999':
        "ema",

    '"label_smoothing": 0.05':
        "label_smoothing",

    '"sampler": "weighted"':
        "weighted_sampler",

    '"metric": "val_quant_macro_f1"':
        "selection_metric",

    '"jitter": 0.005':
        "jitter",

    '"scale": 0.08':
        "scale",

    '"time_mask": 0.10':
        "time_mask",

    '"time_warp": 0.03':
        "time_warp",

    '"p_drop_gyro": 0.30':
        "drop_gyro",

    '"p_drop_acc": 0.03':
        "drop_acc",

    '"p_drop_axis": 0.15':
        "drop_axis",

    '"sam": True':
        "sam",

    '"iqat": True':
        "iqat",

    '"eval_quant": True':
        "eval_quant",

    '"qat": True':
        "qat",

    '"deploy_sim": "periodic"':
        "deploy_sim",

    '"deploy_sim_every": 12':
        "deploy_sim_every",

    '"int_ln": True':
        "integer_layernorm",
}


historical_features = {}


for token, name in historical_required.items():

    present = (
        token
        in
        hist_source
    )

    historical_features[
        name
    ] = present


    if not present:

        raise RuntimeError(
            "Historical STORM recipe token "
            f"not found: {token}"
        )


print(
    "STORM_HISTORICAL_RECIPE_AUDIT_PASS=True"
)


# ==========================================================
# 6. Verify V25 exposure source still exists and is frozen
# ==========================================================

v25_ablation = (
    V25_ABLATION_CODE /
    "run_v25_ablation_r1.py"
)


v25_final = (
    REPO /
    "experiments" /
    "19_v25_final_confirmation" /
    "run_v25_final_r2.py"
)


for path in [
    v25_ablation,
    v25_final,
]:

    if not path.exists():

        raise FileNotFoundError(
            path
        )


final_source = v25_final.read_text()


required_v25_terms = [
    "deterministic_corruption",
    "corruption",
    "no_grad",
]


for term in required_v25_terms:

    if term not in final_source:

        raise RuntimeError(
            f"V25 final source missing expected term: {term}"
        )


print(
    "V25_FINAL_EXPOSURE_SOURCE_AUDIT_PASS=True"
)


# ==========================================================
# 7. Define comparison design
# ==========================================================

comparison_design = {

    "experiment":
        "storm_v25_direct_r1",

    "goal":
        (
            "Direct apples-to-apples comparison "
            "between published/reproduced STORM "
            "and ReliabilityCNN_v25 on the exact "
            "reconstructed STORM cross-source task."
        ),

    "dataset": {

        "source":
            "storm_external_r2",

        "N_total":
            87530,

        "N_train":
            data_rows[
                "train"
            ][
                "N"
            ],

        "N_val":
            data_rows[
                "val"
            ][
                "N"
            ],

        "N_test":
            data_rows[
                "test"
            ][
                "N"
            ],

        "shape":
            [
                64,
                6
            ],

        "classes":
            LABELS,

        "subject_disjoint":
            True,

        "source_stratified":
            True,

        "normalization":
            "train split only",

        "reproduction_derived_min_purity":
            0.8125,
    },

    "seeds":
        SEEDS,

    "published_reference": {

        "model":
            "STORM",

        "reported_parameters":
            19753,

        "reported_fp32_accuracy":
            0.802,

        "reported_fp32_macro_f1":
            0.804,

        "reported_int8_accuracy":
            0.799,

        "reported_int8_macro_f1":
            0.801,
    },

    "models": {

        "STORM_native": {

            "architecture":
                {
                    "d_model":
                        32,

                    "depth":
                        2,

                    "heads":
                        4,

                    "ffn_mult":
                        2,

                    "attention_window":
                        16,

                    "integer_layernorm":
                        True,
                },

            "instantiated_parameters":
                storm_params,

            "training_recipe":
                (
                    "historical/released STORM native "
                    "recipe, with paper-selected "
                    "architecture explicitly forced"
                ),

            "epochs_max":
                200,

            "batch":
                256,

            "optimizer":
                "AdamW",

            "lr":
                6e-4,

            "weight_decay":
                8e-4,

            "scheduler":
                "onecycle",

            "early_stop_patience":
                15,

            "ema_decay":
                0.999,

            "loss":
                "cross_entropy",

            "label_smoothing":
                0.05,

            "sampler":
                "weighted",

            "selection_metric":
                "val_quant_macro_f1",

            "augmentations":
                {
                    "jitter":
                        0.005,

                    "scale":
                        0.08,

                    "time_mask":
                        0.10,

                    "time_warp":
                        0.03,

                    "p_drop_gyro":
                        0.30,

                    "p_drop_acc":
                        0.03,

                    "p_drop_axis":
                        0.15,
                },

            "SAM":
                True,

            "IQAT":
                True,

            "QAT":
                True,

            "eval_quant":
                True,

            "deploy_sim":
                "periodic",

            "deploy_sim_every":
                12,
        },

        "V25_native": {

            "architecture":
                "V25Dense64",

            "instantiated_parameters":
                v25_params,

            "training_recipe":
                (
                    "selected V25 corruption-exposure "
                    "method transferred unchanged in "
                    "principle to T=64"
                ),

            "epochs_max":
                100,

            "batch":
                64,

            "optimizer":
                "Adam",

            "lr":
                1e-3,

            "selection_metric":
                "validation macro-F1",

            "loss":
                "clean cross entropy",

            "corruption_exposure":
                True,

            "consistency_loss":
                False,

            "note":
                (
                    "The exposure forward updates "
                    "training-mode BN statistics but "
                    "does not contribute an additional "
                    "gradient objective."
                ),
        },
    },

    "primary_comparison_track":
        "native_method_vs_native_method",

    "primary_reason":
        (
            "Each complete method is evaluated using "
            "its own frozen training procedure while "
            "sharing exactly the same data, splits, "
            "test set and downstream fault protocol."
        ),

    "architecture_control_track":
        (
            "A shared clean-training recipe may be "
            "added after the primary track to isolate "
            "architecture effects. It must not replace "
            "the primary method-level comparison."
        ),

    "test_set_use":
        (
            "Test set is not used for checkpoint "
            "selection. Final clean and fault results "
            "are evaluated after validation-based "
            "selection."
        ),

    "next_after_training":
        (
            "Exact STORM failure-suite evaluation "
            "for every seed and both methods."
        ),
}


protocol_path = (
    PROTO /
    "storm_v25_direct_protocol_r1.json"
)


protocol_path.write_text(
    json.dumps(
        comparison_design,
        indent=2,
        sort_keys=True
    )
)


# ==========================================================
# 8. Freeze critical inputs
# ==========================================================

critical_paths = [

    DATA_RECEIPT,

    DATA_ROOT /
    "train.npz",

    DATA_ROOT /
    "val.npz",

    DATA_ROOT /
    "test.npz",

    DATA_ROOT /
    "meta.json",

    STORM_REF /
    "storm.py",

    STORM_REF /
    "train.py",

    PREFLIGHT /
    "storm_historical_experiments_cef59e1.py",

    V25_CODE /
    "v25_candidates.py",

    v25_ablation,

    v25_final,

    protocol_path,
]


hashes = {}


for path in critical_paths:

    if not path.exists():

        raise FileNotFoundError(
            path
        )


    hashes[
        str(
            path.relative_to(
                REPO
            )
        )
    ] = sha256(
        path
    )


manifest = {
    "manifest":
        "storm_v25_direct_r1_preflight",

    "hash_count":
        len(hashes),

    "hashes":
        hashes,
}


manifest_path = (
    PROTO /
    "preflight_manifest_r1.json"
)


manifest_path.write_text(
    json.dumps(
        manifest,
        indent=2,
        sort_keys=True
    )
)


# ==========================================================
# 9. Final preflight receipt
# ==========================================================

receipt = {
    "preflight":
        "storm_v25_direct_r1",

    "stage22_dataset_pass":
        True,

    "dataset_exact_table2":
        True,

    "dataset_total":
        87530,

    "storm_source_commit":
        "507dc30c0cab936f1a04f5cb665e9731c962f6b3",

    "storm_historical_recipe_commit":
        "cef59e18c69720e4ecc0d70991ba9a60b49a62f3",

    "storm_forward_t64_pass":
        True,

    "storm_parameters":
        storm_params,

    "storm_published_parameters":
        published_storm_params,

    "storm_parameter_delta":
        storm_param_delta,

    "v25_forward_t64_pass":
        True,

    "v25_parameters":
        v25_params,

    "seed_count":
        len(SEEDS),

    "seeds":
        SEEDS,

    "training_started":
        False,

    "fault_evaluation_started":
        False,

    "preflight_manifest_sha256":
        sha256(
            manifest_path
        ),

    "protocol_sha256":
        sha256(
            protocol_path
        ),
}


receipt_path = (
    PREFLIGHT /
    "storm_v25_direct_preflight_receipt_r1.json"
)


receipt_path.write_text(
    json.dumps(
        receipt,
        indent=2,
        sort_keys=True
    )
)


print()
print("=" * 100)
print("COMPARISON DESIGN")
print("=" * 100)

print(
    json.dumps(
        comparison_design,
        indent=2,
        sort_keys=True
    )
)


print()
print("=" * 100)
print("FINAL PREFLIGHT")
print("=" * 100)

print(
    "STORM_PARAMETERS=",
    storm_params
)

print(
    "STORM_PUBLISHED_PARAMETERS=",
    published_storm_params
)

print(
    "STORM_PARAMETER_DELTA=",
    storm_param_delta
)

print(
    "V25_PARAMETERS=",
    v25_params
)

print(
    "SEEDS=",
    SEEDS
)

print(
    "FROZEN_PREFLIGHT_HASHES=",
    len(hashes)
)

print(
    "PROTOCOL_SHA256=",
    sha256(
        protocol_path
    )
)

print(
    "MANIFEST_SHA256=",
    sha256(
        manifest_path
    )
)

print(
    "PREFLIGHT_RECEIPT_SHA256=",
    sha256(
        receipt_path
    )
)

print()
print(
    "TRAINING_STARTED=False"
)

print(
    "FAULT_EVALUATION_STARTED=False"
)

print(
    "STORM_V25_DIRECT_R1_PREFLIGHT_PASS=True"
)

print("=" * 100)
