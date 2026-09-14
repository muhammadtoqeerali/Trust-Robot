from __future__ import annotations

import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import torch


ROOT = Path(
    __file__
).resolve().parents[2]

SRC = (
    ROOT
    / "src"
)

if str(
    SRC
) not in sys.path:
    sys.path.insert(
        0,
        str(
            SRC
        ),
    )

from imu_reliability.baseline.date2025_cnn400 import (  # noqa: E402
    Date2025CNN400,
)


EVALUATOR_TAG = (
    "ood-calibration-evaluator-v1b"
)

PROTOCOL_TAG = (
    "ood-calibration-protocol-v1"
)

PROTOCOL_COMMIT = (
    "9297a81411df9cfb3b3812f8eecd3b630c45bae4"
)

PROTOCOL_CONTENT_SHA256 = (
    "47c1f3b21c069953e76d3c9bc92ee29c"
    "f577675204c653a29e4844a4b35c38f5"
)

PROTOCOL_RAW_SHA256 = (
    "a118d39cee4847dd86f41662ffd036a8b"
    "ae8bcc0551ff5572f83d52ea5c2a862"
)

INTEGRITY_FINAL_RESULT_COMMIT = (
    "b1aaa28a5cd2222bd3acc7d5d86289ba9fd71c74"
)

BASELINE_COMMIT = (
    "d6fe744b292139d18fd4dee37c96066bcf2d38c6"
)

REGISTRY_COMMIT = (
    "416cc9d8895646c38edc6b7be1dfdc042d0c2219"
)

CHECKPOINT_SHA256 = (
    "ee7c0079bfb8555bff45c3077cc24eaa"
    "4373c57729045d92a831a1d7a3ea9bb1"
)

MODEL_SOURCE_RAW_SHA256 = (
    "def71b3cebc0649c0d909e4ffd5dc04f"
    "177fcb795ff6ebfd13f90e214c67581d"
)

FAILED_EVALUATOR_V1_TAG = (
    "ood-calibration-evaluator-v1"
)

FAILED_EVALUATOR_V1_COMMIT = (
    "50110f0217e8fa81e4851777ee3a8dcd44c184a2"
)

FAILED_EVALUATOR_V1_RAW_SHA256 = (
    "19dbd4d1d8b6753be64a020dec3c0e4f"
    "a77fd4c9dd1a30f2e3c273b8dba85f56"
)

FAILED_EVALUATOR_V1_SOURCE = (
    ROOT
    / "experiments/03_ood/"
      "evaluate_ood_calibration_v1.py"
)

LEGACY_COMPATIBILITY_ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/"
    "Protechto-master"
)

LEGACY_CHECKPOINT_HPARAMS = Path(
    "/mnt/hdd16T/protechto/lightning_logs/"
    "KFall/version_587/hparams.yaml"
)

LEGACY_CHECKPOINT_HPARAMS_RAW_SHA256 = (
    "45a12c4ca9749e37cfd9fff34b26cfbf"
    "e0c304f91e38609891b4ee9ebf769c42"
)

LEGACY_COMPATIBILITY_FILES = {
    "models/__init__.py":
        (
            "4b1e0413ed559b968758e0f9468e9d15"
            "34ca28a2aad1d8a1fa3581b312d8b7f5"
        ),

    "models/CNN.py":
        (
            "5e1ddac378c80929068b6fb8f62fff0d"
            "351bacbf047297829bd0531ad9c43eb2"
        ),

    "models/helper.py":
        (
            "b495165985efdbbe57323c3de2efb0b8"
            "004d94384e7f61d79f38af8b1c15aafd"
        ),

    "models/modules/IMUNormalizer.py":
        (
            "ec9abd57a3df5bd10bf73ee495a44daa"
            "0fa4294a9d094d353831fb98d193f9a2"
        ),

    "models/configs/CNN_config.py":
        (
            "89d74a3141565cda1429e43d967584c0"
            "09e850164db3e7e404c6e6a2f864ee46"
        ),
}

LEGACY_CNN_AST_CLASS_SOURCE_SHA256 = (
    "08cf5f8f0ae4ea679fc12e9cb9cdcb05"
    "1fd20c5ab96a797ff7629323b0c544f7"
)

EXPECTED_CALIBRATION_ROWS = (
    447
)

EXPECTED_CALIBRATION_WINDOWS = (
    89868
)

EXPECTED_ACTIVITY = (
    89544
)

EXPECTED_FALLING = (
    324
)

EXPECTED_DATASET_ROWS = {
    "KFALL":
        314,
    "UNIVRFALL":
        132,
    "ONFIELD":
        1,
}

EXPECTED_DATASET_WINDOWS = {
    "KFALL":
        9585,
    "UNIVRFALL":
        5951,
    "ONFIELD":
        74332,
}

EXPECTED_STRATA = {
    (
        "KFALL",
        "Activity",
    ):
        9342,

    (
        "KFALL",
        "Falling",
    ):
        243,

    (
        "UNIVRFALL",
        "Activity",
    ):
        5870,

    (
        "UNIVRFALL",
        "Falling",
    ):
        81,

    (
        "ONFIELD",
        "Activity",
    ):
        74332,
}

BATCH_SIZE = (
    2048
)

PROTOCOL = (
    ROOT
    / "configs/ood/"
      "ood_calibration_protocol_v1.json"
)

REGISTRY = (
    ROOT
    / "data/manifests/"
      "reliability_eval_registry_v1.json"
)

MODEL_SOURCE = (
    ROOT
    / "src/imu_reliability/baseline/"
      "date2025_cnn400.py"
)

DATA = Path(
    "/mnt/hdd16T/protechto/data/back/"
    "UniVrFall_KFall/segments/"
    "400ms_50ov_npseg_filt_binary"
)

CHECKPOINT = Path(
    "/mnt/hdd16T/protechto/checkpoints/CNN/400ms/"
    "2025-02-25_12_24_47/best-checkpoint.ckpt"
)

RESULT = (
    ROOT
    / "results/raw/"
      "ood_calibration_v1_candidate.json"
)

OPERATING_POINT_CANDIDATE = (
    ROOT
    / "configs/ood/"
      "ood_operating_point_v1_candidate.json"
)


def canonical_digest(
    payload,
):
    normalized = json.loads(
        json.dumps(
            payload,
            separators=(",", ":"),
            allow_nan=False,
        )
    )

    return sha256(
        json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def file_sha256(
    path: Path,
) -> str:
    return sha256(
        path.read_bytes()
    ).hexdigest()


def git(
    *args: str,
) -> str:
    return subprocess.check_output(
        [
            "git",
            *args,
        ],
        cwd=ROOT,
        text=True,
    ).strip()


def normalize_label(
    value,
) -> int:
    if isinstance(
        value,
        bytes,
    ):
        value = value.decode()

    if isinstance(
        value,
        np.generic,
    ):
        value = value.item()

    text = str(
        value
    ).strip()

    if text in {
        "Activity",
        "0",
        "0.0",
    }:
        return 0

    if text in {
        "Falling",
        "1",
        "1.0",
    }:
        return 1

    raise ValueError(
        f"Unknown historical label: {value!r}"
    )


def label_name(
    value: int,
) -> str:
    if value == 0:
        return "Activity"

    if value == 1:
        return "Falling"

    raise ValueError(
        f"Unexpected label: {value}"
    )


def stratum_rank(
    n: int,
) -> int:
    if n <= 0:
        raise ValueError(
            "Stratum must be nonempty"
        )

    return int(
        math.floor(
            0.01
            * n
        )
    )


def stratum_boundary(
    margins: Sequence[float],
) -> float:
    if not margins:
        raise ValueError(
            "Margins must be nonempty"
        )

    ordered = np.sort(
        np.asarray(
            margins,
            dtype=np.float64,
        ),
        kind="mergesort",
    )

    rank = stratum_rank(
        len(
            ordered
        )
    )

    return float(
        ordered[
            rank
        ]
    )


def finite_sample_threshold(
    strata: Mapping[
        tuple[str, str],
        Sequence[float],
    ],
) -> tuple[
    float,
    dict[
        tuple[str, str],
        float,
    ],
]:
    if not strata:
        raise ValueError(
            "No strata supplied"
        )

    boundaries = {}

    for key, values in strata.items():
        if len(
            values
        ) == 0:
            continue

        boundaries[
            key
        ] = stratum_boundary(
            values
        )

    if not boundaries:
        raise ValueError(
            "No nonempty strata supplied"
        )

    threshold = float(
        min(
            boundaries.values()
        )
    )

    return (
        threshold,
        boundaries,
    )


def empirical_acceptance(
    margins: Iterable[float],
    threshold: float,
) -> float:
    values = np.asarray(
        list(
            margins
        ),
        dtype=np.float64,
    )

    if values.size == 0:
        raise ValueError(
            "Margins must be nonempty"
        )

    return float(
        np.mean(
            values
            >= threshold
        )
    )


def empty_task_bucket():
    return {
        "true_activity_pred_activity":
            0,
        "true_activity_pred_falling":
            0,
        "true_falling_pred_activity":
            0,
        "true_falling_pred_falling":
            0,
    }


def update_task_bucket(
    bucket,
    y_true: np.ndarray,
    y_pred: np.ndarray,
):
    if (
        y_true.shape
        != y_pred.shape
    ):
        raise ValueError(
            "Task vectors differ in shape"
        )

    bucket[
        "true_activity_pred_activity"
    ] += int(
        np.sum(
            (y_true == 0)
            & (y_pred == 0)
        )
    )

    bucket[
        "true_activity_pred_falling"
    ] += int(
        np.sum(
            (y_true == 0)
            & (y_pred == 1)
        )
    )

    bucket[
        "true_falling_pred_activity"
    ] += int(
        np.sum(
            (y_true == 1)
            & (y_pred == 0)
        )
    )

    bucket[
        "true_falling_pred_falling"
    ] += int(
        np.sum(
            (y_true == 1)
            & (y_pred == 1)
        )
    )


def _safe_div(
    numerator: float,
    denominator: float,
) -> float:
    if denominator == 0:
        return 0.0

    return float(
        numerator
        / denominator
    )


def finalize_task_bucket(
    bucket,
):
    tn = int(
        bucket[
            "true_activity_pred_activity"
        ]
    )

    fp = int(
        bucket[
            "true_activity_pred_falling"
        ]
    )

    fn = int(
        bucket[
            "true_falling_pred_activity"
        ]
    )

    tp = int(
        bucket[
            "true_falling_pred_falling"
        ]
    )

    total = (
        tn
        + fp
        + fn
        + tp
    )

    accuracy = _safe_div(
        tn + tp,
        total,
    )

    activity_precision = _safe_div(
        tn,
        tn + fn,
    )

    activity_recall = _safe_div(
        tn,
        tn + fp,
    )

    falling_precision = _safe_div(
        tp,
        tp + fp,
    )

    falling_recall = _safe_div(
        tp,
        tp + fn,
    )

    activity_f1 = _safe_div(
        2.0
        * activity_precision
        * activity_recall,
        activity_precision
        + activity_recall,
    )

    falling_f1 = _safe_div(
        2.0
        * falling_precision
        * falling_recall,
        falling_precision
        + falling_recall,
    )

    return {
        "n_windows":
            total,

        "confusion_matrix_activity_falling": [
            [
                tn,
                fp,
            ],
            [
                fn,
                tp,
            ],
        ],

        "accuracy":
            accuracy,

        "macro_precision":
            float(
                (
                    activity_precision
                    + falling_precision
                )
                / 2.0
            ),

        "macro_recall":
            float(
                (
                    activity_recall
                    + falling_recall
                )
                / 2.0
            ),

        "macro_f1":
            float(
                (
                    activity_f1
                    + falling_f1
                )
                / 2.0
            ),

        "fall_precision":
            falling_precision,

        "fall_recall":
            falling_recall,

        "fall_f1":
            falling_f1,

        "fall_false_negative_rate":
            _safe_div(
                fn,
                fn + tp,
            ),
    }


def load_protocol():
    if not PROTOCOL.is_file():
        raise RuntimeError(
            "Frozen OOD protocol absent"
        )

    observed_raw = file_sha256(
        PROTOCOL
    )

    if (
        observed_raw
        != PROTOCOL_RAW_SHA256
    ):
        raise RuntimeError(
            "OOD protocol raw SHA changed"
        )

    data = json.loads(
        PROTOCOL.read_text()
    )

    payload = deepcopy(
        data
    )

    stored = payload.pop(
        "content_sha256"
    )

    computed = canonical_digest(
        payload
    )

    if stored != computed:
        raise RuntimeError(
            "OOD protocol canonical SHA mismatch"
        )

    if (
        stored
        != PROTOCOL_CONTENT_SHA256
    ):
        raise RuntimeError(
            "Frozen OOD protocol content changed"
        )

    if (
        data[
            "score"
        ][
            "selected_method"
        ]
        != "top_two_logit_margin"
    ):
        raise RuntimeError(
            "Unexpected OOD score method"
        )

    if (
        data[
            "threshold_selection"
        ][
            "clean_id_acceptance_target"
        ]
        != 0.99
    ):
        raise RuntimeError(
            "OOD clean-ID coverage target changed"
        )

    if (
        data[
            "score"
        ][
            "requires_second_task_model_forward"
        ]
        is not False
    ):
        raise RuntimeError(
            "Second task forward unexpectedly allowed"
        )

    if (
        data[
            "calibration_outputs_predeclared"
        ][
            "true_ood_detection_metrics_allowed"
        ]
        is not False
    ):
        raise RuntimeError(
            "True-OOD calibration metrics unexpectedly allowed"
        )

    return data


def verify_legacy_pickle_compatibility_dependencies():
    import ast
    import importlib

    if not LEGACY_COMPATIBILITY_ROOT.is_dir():
        raise RuntimeError(
            "Pinned legacy compatibility root absent"
        )

    for relative, expected_sha in (
        LEGACY_COMPATIBILITY_FILES.items()
    ):
        candidate = (
            LEGACY_COMPATIBILITY_ROOT
            / relative
        )

        if not candidate.is_file():
            raise RuntimeError(
                f"Pinned legacy dependency absent: {candidate}"
            )

        observed_sha = file_sha256(
            candidate
        )

        if observed_sha != expected_sha:
            raise RuntimeError(
                f"Pinned legacy dependency changed: {relative}"
            )

    if not LEGACY_CHECKPOINT_HPARAMS.is_file():
        raise RuntimeError(
            "Pinned checkpoint-era hparams absent"
        )

    if (
        file_sha256(
            LEGACY_CHECKPOINT_HPARAMS
        )
        != LEGACY_CHECKPOINT_HPARAMS_RAW_SHA256
    ):
        raise RuntimeError(
            "Checkpoint-era hparams changed"
        )

    hparams_text = (
        LEGACY_CHECKPOINT_HPARAMS
        .read_text(
            encoding="utf-8",
            errors="ignore",
        )
    )

    expected_checkpoint_text = str(
        CHECKPOINT
    )

    if (
        expected_checkpoint_text
        not in hparams_text
    ):
        raise RuntimeError(
            "Pinned hparams no longer references "
            "the protected checkpoint"
        )

    if (
        "models.CNN.CNN"
        not in hparams_text
    ):
        raise RuntimeError(
            "Pinned hparams no longer references "
            "models.CNN.CNN"
        )

    cnn_source_path = (
        LEGACY_COMPATIBILITY_ROOT
        / "models/CNN.py"
    )

    cnn_source = cnn_source_path.read_text(
        encoding="utf-8"
    )

    cnn_tree = ast.parse(
        cnn_source
    )

    cnn_node = next(
        (
            node
            for node in cnn_tree.body
            if (
                isinstance(
                    node,
                    ast.ClassDef,
                )
                and node.name
                == "CNN"
            )
        ),
        None,
    )

    if cnn_node is None:
        raise RuntimeError(
            "Pinned legacy CNN class absent"
        )

    cnn_class_source = (
        ast.get_source_segment(
            cnn_source,
            cnn_node,
        )
    )

    if cnn_class_source is None:
        raise RuntimeError(
            "Unable to extract pinned CNN class source"
        )

    cnn_class_source_sha = sha256(
        cnn_class_source.encode(
            "utf-8"
        )
    ).hexdigest()

    if (
        cnn_class_source_sha
        != LEGACY_CNN_AST_CLASS_SOURCE_SHA256
    ):
        raise RuntimeError(
            "Pinned legacy CNN class source changed"
        )

    legacy_root_text = str(
        LEGACY_COMPATIBILITY_ROOT
    )

    if legacy_root_text in sys.path:
        sys.path.remove(
            legacy_root_text
        )

    sys.path.insert(
        0,
        legacy_root_text,
    )

    existing = sys.modules.get(
        "models.CNN"
    )

    expected_module_file = (
        LEGACY_COMPATIBILITY_ROOT
        / "models/CNN.py"
    ).resolve()

    if existing is not None:
        existing_file = Path(
            existing.__file__
        ).resolve()

        if existing_file != expected_module_file:
            raise RuntimeError(
                "models.CNN was already imported "
                "from an unpinned location"
            )

    legacy_module = importlib.import_module(
        "models.CNN"
    )

    resolved_module_file = Path(
        legacy_module.__file__
    ).resolve()

    if (
        resolved_module_file
        != expected_module_file
    ):
        raise RuntimeError(
            "models.CNN resolved from wrong source"
        )

    LegacyCNN = getattr(
        legacy_module,
        "CNN",
        None,
    )

    if LegacyCNN is None:
        raise RuntimeError(
            "Pinned models.CNN.CNN symbol absent"
        )

    if (
        getattr(
            LegacyCNN,
            "__module__",
            None,
        )
        != "models.CNN"
        or getattr(
            LegacyCNN,
            "__name__",
            None,
        )
        != "CNN"
    ):
        raise RuntimeError(
            "Pinned legacy CNN symbol identity mismatch"
        )

    return {
        "legacy_cnn_class":
            LegacyCNN,

        "legacy_root":
            str(
                LEGACY_COMPATIBILITY_ROOT
            ),

        "legacy_module_file":
            str(
                resolved_module_file
            ),

        "hparams_raw_sha256":
            LEGACY_CHECKPOINT_HPARAMS_RAW_SHA256,

        "cnn_file_raw_sha256":
            LEGACY_COMPATIBILITY_FILES[
                "models/CNN.py"
            ],
    }


def verify_frozen_inputs():
    refs = {
        "ood-calibration-evaluator-v1^{commit}":
            FAILED_EVALUATOR_V1_COMMIT,

        "ood-calibration-protocol-v1^{commit}":
            PROTOCOL_COMMIT,

        "integrity-final-test-result-v1^{commit}":
            INTEGRITY_FINAL_RESULT_COMMIT,

        "baseline-date2025-cnn400-v1^{commit}":
            BASELINE_COMMIT,

        "reliability-eval-registry-v1^{commit}":
            REGISTRY_COMMIT,
    }

    for ref, expected in refs.items():
        observed = git(
            "rev-parse",
            ref,
        )

        if observed != expected:
            raise RuntimeError(
                f"Frozen ref changed: "
                f"{ref}: {observed}"
            )

    for ref in (
        "ood-calibration-evaluator-v1",
        "ood-calibration-protocol-v1",
        "integrity-final-test-result-v1",
        "baseline-date2025-cnn400-v1",
        "reliability-eval-registry-v1",
    ):
        rc = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                ref,
                "HEAD",
            ],
            cwd=ROOT,
            check=False,
        ).returncode

        if rc != 0:
            raise RuntimeError(
                f"Frozen ref is not an ancestor: {ref}"
            )

    if file_sha256(
        MODEL_SOURCE
    ) != MODEL_SOURCE_RAW_SHA256:
        raise RuntimeError(
            "Protected model source SHA changed"
        )

    if file_sha256(
        CHECKPOINT
    ) != CHECKPOINT_SHA256:
        raise RuntimeError(
            "Protected checkpoint SHA changed"
        )

    if subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            "baseline-date2025-cnn400-v1",
            "HEAD",
            "--",
            str(
                MODEL_SOURCE.relative_to(
                    ROOT
                )
            ),
        ],
        cwd=ROOT,
        check=False,
    ).returncode != 0:
        raise RuntimeError(
            "Protected model source changed since baseline freeze"
        )

    if subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            "reliability-eval-registry-v1",
            "HEAD",
            "--",
            str(
                REGISTRY.relative_to(
                    ROOT
                )
            ),
        ],
        cwd=ROOT,
        check=False,
    ).returncode != 0:
        raise RuntimeError(
            "Registry changed since registry freeze"
        )

    for path in (
        PROTOCOL,
        MODEL_SOURCE,
        REGISTRY,
    ):
        if subprocess.run(
            [
                "git",
                "diff",
                "--quiet",
                "--",
                str(
                    path.relative_to(
                        ROOT
                    )
                ),
            ],
            cwd=ROOT,
            check=False,
        ).returncode != 0:
            raise RuntimeError(
                f"Frozen input has worktree changes: {path}"
            )

    if (
        file_sha256(
            FAILED_EVALUATOR_V1_SOURCE
        )
        != FAILED_EVALUATOR_V1_RAW_SHA256
    ):
        raise RuntimeError(
            "Failed evaluator v1 bytes changed"
        )

    verify_legacy_pickle_compatibility_dependencies()

    load_protocol()


def verify_evaluator_is_frozen():
    tag_ref = (
        f"{EVALUATOR_TAG}^{{commit}}"
    )

    tag_commit = git(
        "rev-parse",
        tag_ref,
    )

    head = git(
        "rev-parse",
        "HEAD",
    )

    if head != tag_commit:
        raise RuntimeError(
            "HEAD must be exactly at frozen OOD evaluator tag "
            "before calibration outputs may be exposed"
        )

    evaluator_rel = str(
        Path(
            __file__
        ).resolve().relative_to(
            ROOT
        )
    )

    last_touch = git(
        "log",
        "-1",
        "--format=%H",
        "--",
        evaluator_rel,
    )

    if last_touch != tag_commit:
        raise RuntimeError(
            "OOD evaluator changed after evaluator freeze"
        )

    return tag_commit


def calibration_rows():
    registry = json.loads(
        REGISTRY.read_text()
    )

    rows = [
        row
        for row in registry[
            "records"
        ]
        if row[
            "partition"
        ]
        == "calibration"
    ]

    rows.sort(
        key=lambda row:
            (
                row[
                    "dataset"
                ],
                row[
                    "trial_id"
                ],
            )
    )

    if len(
        rows
    ) != EXPECTED_CALIBRATION_ROWS:
        raise RuntimeError(
            "Calibration registry row count changed"
        )

    row_counts = Counter(
        row[
            "dataset"
        ]
        for row in rows
    )

    if dict(
        row_counts
    ) != EXPECTED_DATASET_ROWS:
        raise RuntimeError(
            "Calibration registry dataset-row counts changed"
        )

    window_counts = Counter()

    for row in rows:
        if (
            row[
                "prospective_constraints"
            ][
                "may_select_ood_operating_point"
            ]
            is not True
        ):
            raise RuntimeError(
                "Calibration OOD-selection permission changed"
            )

        window_counts[
            row[
                "dataset"
            ]
        ] += int(
            row[
                "historical_windows"
            ]
        )

    if dict(
        window_counts
    ) != EXPECTED_DATASET_WINDOWS:
        raise RuntimeError(
            "Calibration historical-window counts changed"
        )

    return rows


def load_protected_model():
    compatibility = (
        verify_legacy_pickle_compatibility_dependencies()
    )

    LegacyCNN = compatibility[
        "legacy_cnn_class"
    ]

    if file_sha256(
        CHECKPOINT
    ) != CHECKPOINT_SHA256:
        raise RuntimeError(
            "Checkpoint SHA mismatch at load boundary"
        )

    ckpt = torch.load(
        CHECKPOINT,
        map_location="cpu",
        weights_only=False,
    )

    if (
        not isinstance(
            ckpt,
            dict,
        )
        or "state_dict"
        not in ckpt
    ):
        raise RuntimeError(
            "Unexpected checkpoint structure"
        )

    if (
        ckpt.get(
            "epoch"
        )
        != 60
    ):
        raise RuntimeError(
            "Protected checkpoint epoch changed"
        )

    if (
        ckpt.get(
            "global_step"
        )
        != 702476
    ):
        raise RuntimeError(
            "Protected checkpoint global_step changed"
        )

    hyper = ckpt.get(
        "hyper_parameters"
    )

    if not isinstance(
        hyper,
        dict,
    ):
        raise RuntimeError(
            "Protected checkpoint hyper_parameters absent"
        )

    if (
        hyper.get(
            "model"
        )
        is not LegacyCNN
    ):
        raise RuntimeError(
            "Checkpoint legacy model symbol did not resolve "
            "to the pinned compatibility class"
        )

    if (
        hyper.get(
            "n_features"
        )
        != 9
        or hyper.get(
            "n_classes"
        )
        != 2
    ):
        raise RuntimeError(
            "Protected checkpoint task dimensions changed"
        )

    cfg = hyper.get(
        "cfg"
    )

    if not isinstance(
        cfg,
        dict,
    ):
        raise RuntimeError(
            "Protected checkpoint cfg absent"
        )

    expected_cfg = {
        "conv_1_dim":
            32,

        "conv_1_filter":
            4,

        "conv_dropout":
            0.4,

        "conv_pool":
            2,

        "fc":
            256,

        "fc_dropout":
            0.2,

        "prediction_bias":
            0.9,
    }

    for key, expected in expected_cfg.items():
        if cfg.get(
            key
        ) != expected:
            raise RuntimeError(
                f"Protected checkpoint cfg changed: {key}"
            )

    state = {
        key.removeprefix(
            "model."
        ):
            value
        for key, value
        in ckpt[
            "state_dict"
        ].items()
        if key.startswith(
            "model."
        )
    }

    if not state:
        raise RuntimeError(
            "No protected model state found"
        )

    expected_shapes = {
        "conv_1.0.weight":
            (
                32,
                6,
                4,
            ),

        "conv_2.0.weight":
            (
                32,
                32,
                4,
            ),

        "fc.1.weight":
            (
                256,
                224,
            ),

        "fc.4.weight":
            (
                2,
                256,
            ),
    }

    for key, expected_shape in expected_shapes.items():
        if key not in state:
            raise RuntimeError(
                f"Required protected tensor absent: {key}"
            )

        observed_shape = tuple(
            int(
                dimension
            )
            for dimension
            in state[
                key
            ].shape
        )

        if observed_shape != expected_shape:
            raise RuntimeError(
                f"Protected tensor geometry changed: "
                f"{key}: {observed_shape}"
            )

    model = (
        Date2025CNN400()
    )

    model.load_state_dict(
        state,
        strict=True,
    )

    parameter_count = sum(
        int(
            parameter.numel()
        )
        for parameter
        in model.parameters()
    )

    if parameter_count != 63173:
        raise RuntimeError(
            "Protected reconstructed parameter count changed"
        )

    model.eval()

    del ckpt

    return model


def evaluate_calibration(
    model,
):
    rows = calibration_rows()

    margins_by_stratum = defaultdict(
        list
    )

    margins_by_dataset = defaultdict(
        list
    )

    margins_by_class = defaultdict(
        list
    )

    all_margins = []

    overall_task = empty_task_bucket()

    task_by_dataset = defaultdict(
        empty_task_bucket
    )

    observed_rows = Counter()
    observed_windows = Counter()
    observed_classes = Counter()

    raw_trial_arrays_opened = 0
    model_batch_forward_calls = 0
    model_windows_forwarded = 0

    for row in rows:
        dataset = row[
            "dataset"
        ]

        trial_id = row[
            "trial_id"
        ]

        trial_dir = (
            DATA
            / row[
                "relative_trial"
            ]
        )

        x_path = (
            trial_dir
            / "segments.npy"
        )

        y_path = (
            trial_dir
            / "labels.npy"
        )

        if (
            not x_path.is_file()
            or not y_path.is_file()
        ):
            raise RuntimeError(
                f"Protected calibration pair absent: {trial_id}"
            )

        x = np.load(
            x_path,
            mmap_mode="r",
            allow_pickle=False,
        )

        y_raw = np.load(
            y_path,
            allow_pickle=True,
        )

        raw_trial_arrays_opened += 1

        if (
            x.ndim != 3
            or tuple(
                x.shape[
                    1:
                ]
            )
            != (
                40,
                9,
            )
        ):
            raise RuntimeError(
                f"Unexpected protected shape: "
                f"{trial_id}: {x.shape}"
            )

        if len(
            x
        ) != len(
            y_raw
        ):
            raise RuntimeError(
                f"X/Y mismatch: {trial_id}"
            )

        if len(
            x
        ) != int(
            row[
                "historical_windows"
            ]
        ):
            raise RuntimeError(
                f"Registry window mismatch: {trial_id}"
            )

        y = np.asarray(
            [
                normalize_label(
                    value
                )
                for value in y_raw
            ],
            dtype=np.int64,
        )

        observed_rows[
            dataset
        ] += 1

        observed_windows[
            dataset
        ] += int(
            len(
                y
            )
        )

        observed_classes[
            "Activity"
        ] += int(
            np.sum(
                y == 0
            )
        )

        observed_classes[
            "Falling"
        ] += int(
            np.sum(
                y == 1
            )
        )

        for start in range(
            0,
            len(
                x
            ),
            BATCH_SIZE,
        ):
            end = min(
                start
                + BATCH_SIZE,
                len(
                    x
                ),
            )

            xb = torch.from_numpy(
                np.asarray(
                    x[
                        start:end
                    ],
                    dtype=np.float32,
                )
            )

            with torch.inference_mode():
                logits, features = (
                    model.forward_with_features(
                        xb
                    )
                )

            model_batch_forward_calls += 1
            model_windows_forwarded += int(
                end
                - start
            )

            if tuple(
                logits.shape
            ) != (
                end
                - start,
                2,
            ):
                raise RuntimeError(
                    "Unexpected logits shape"
                )

            if tuple(
                features.shape
            ) != (
                end
                - start,
                256,
            ):
                raise RuntimeError(
                    "Unexpected feature shape"
                )

            margin = torch.abs(
                logits[
                    :,
                    0
                ]
                - logits[
                    :,
                    1
                ]
            )

            pred = torch.argmax(
                logits,
                dim=1,
            )

            margin_np = (
                margin
                .cpu()
                .numpy()
                .astype(
                    np.float64
                )
            )

            pred_np = (
                pred
                .cpu()
                .numpy()
                .astype(
                    np.int64
                )
            )

            y_batch = y[
                start:end
            ]

            update_task_bucket(
                overall_task,
                y_batch,
                pred_np,
            )

            update_task_bucket(
                task_by_dataset[
                    dataset
                ],
                y_batch,
                pred_np,
            )

            for offset in range(
                end
                - start
            ):
                true_class = label_name(
                    int(
                        y_batch[
                            offset
                        ]
                    )
                )

                value = float(
                    margin_np[
                        offset
                    ]
                )

                key = (
                    dataset,
                    true_class,
                )

                margins_by_stratum[
                    key
                ].append(
                    value
                )

                margins_by_dataset[
                    dataset
                ].append(
                    value
                )

                margins_by_class[
                    true_class
                ].append(
                    value
                )

                all_margins.append(
                    value
                )

        del x
        del y_raw
        del y

    if dict(
        observed_rows
    ) != EXPECTED_DATASET_ROWS:
        raise RuntimeError(
            "Observed calibration trial rows changed"
        )

    if dict(
        observed_windows
    ) != EXPECTED_DATASET_WINDOWS:
        raise RuntimeError(
            "Observed calibration windows changed"
        )

    if (
        observed_classes[
            "Activity"
        ],
        observed_classes[
            "Falling"
        ],
    ) != (
        EXPECTED_ACTIVITY,
        EXPECTED_FALLING,
    ):
        raise RuntimeError(
            "Observed calibration class totals changed"
        )

    if len(
        all_margins
    ) != EXPECTED_CALIBRATION_WINDOWS:
        raise RuntimeError(
            "Margin count mismatch"
        )

    if (
        model_windows_forwarded
        != EXPECTED_CALIBRATION_WINDOWS
    ):
        raise RuntimeError(
            "Not every calibration window received exactly "
            "one protected task-model forward"
        )

    observed_strata = {
        key:
            len(
                values
            )
        for key, values
        in margins_by_stratum.items()
    }

    if (
        observed_strata
        != EXPECTED_STRATA
    ):
        raise RuntimeError(
            "Observed dataset x class strata changed"
        )

    threshold, boundaries = (
        finite_sample_threshold(
            margins_by_stratum
        )
    )

    stratum_metrics = []

    for key in sorted(
        margins_by_stratum
    ):
        dataset, class_name = key

        margins = np.asarray(
            margins_by_stratum[
                key
            ],
            dtype=np.float64,
        )

        n = int(
            len(
                margins
            )
        )

        rank = stratum_rank(
            n
        )

        q_s = float(
            boundaries[
                key
            ]
        )

        accepted = int(
            np.sum(
                margins
                >= threshold
            )
        )

        rejected = int(
            n
            - accepted
        )

        acceptance = float(
            accepted
            / n
        )

        if acceptance < 0.99:
            raise RuntimeError(
                f"Frozen clean-ID coverage constraint failed: "
                f"{dataset}/{class_name}: {acceptance}"
            )

        stratum_metrics.append(
            {
                "dataset":
                    dataset,

                "class":
                    class_name,

                "n":
                    n,

                "r_s":
                    rank,

                "q_s":
                    q_s,

                "accepted_count":
                    accepted,

                "rejected_count":
                    rejected,

                "empirical_acceptance":
                    acceptance,

                "empirical_ood_unknown_rate":
                    float(
                        rejected
                        / n
                    ),

                "binding_global_threshold":
                    bool(
                        q_s
                        == threshold
                    ),
            }
        )

    dataset_metrics = {}

    for dataset in sorted(
        margins_by_dataset
    ):
        margins = np.asarray(
            margins_by_dataset[
                dataset
            ],
            dtype=np.float64,
        )

        accepted = int(
            np.sum(
                margins
                >= threshold
            )
        )

        n = int(
            len(
                margins
            )
        )

        dataset_metrics[
            dataset
        ] = {
            "n":
                n,

            "accepted_count":
                accepted,

            "rejected_count":
                int(
                    n
                    - accepted
                ),

            "empirical_acceptance":
                float(
                    accepted
                    / n
                ),

            "empirical_ood_unknown_rate":
                float(
                    (
                        n
                        - accepted
                    )
                    / n
                ),
        }

    class_metrics = {}

    for class_name in sorted(
        margins_by_class
    ):
        margins = np.asarray(
            margins_by_class[
                class_name
            ],
            dtype=np.float64,
        )

        accepted = int(
            np.sum(
                margins
                >= threshold
            )
        )

        n = int(
            len(
                margins
            )
        )

        class_metrics[
            class_name
        ] = {
            "n":
                n,

            "accepted_count":
                accepted,

            "rejected_count":
                int(
                    n
                    - accepted
                ),

            "empirical_acceptance":
                float(
                    accepted
                    / n
                ),

            "empirical_ood_unknown_rate":
                float(
                    (
                        n
                        - accepted
                    )
                    / n
                ),
        }

    all_margin_array = np.asarray(
        all_margins,
        dtype=np.float64,
    )

    overall_accepted = int(
        np.sum(
            all_margin_array
            >= threshold
        )
    )

    overall_n = int(
        all_margin_array.size
    )

    return {
        "selected_threshold":
            threshold,

        "per_stratum":
            stratum_metrics,

        "overall_clean_id": {
            "n":
                overall_n,

            "accepted_count":
                overall_accepted,

            "rejected_count":
                int(
                    overall_n
                    - overall_accepted
                ),

            "empirical_acceptance":
                float(
                    overall_accepted
                    / overall_n
                ),

            "empirical_ood_unknown_rate":
                float(
                    (
                        overall_n
                        - overall_accepted
                    )
                    / overall_n
                ),
        },

        "by_dataset":
            dataset_metrics,

        "by_class":
            class_metrics,

        "task_metrics_descriptive_only": {
            "overall":
                finalize_task_bucket(
                    overall_task
                ),

            "by_dataset": {
                dataset:
                    finalize_task_bucket(
                        bucket
                    )
                for dataset, bucket
                in sorted(
                    task_by_dataset.items()
                )
            },
        },

        "access_audit": {
            "calibration_registry_trial_rows":
                EXPECTED_CALIBRATION_ROWS,

            "calibration_trial_array_pairs_opened":
                raw_trial_arrays_opened,

            "calibration_windows_forwarded":
                model_windows_forwarded,

            "model_batch_forward_calls":
                model_batch_forward_calls,

            "task_model_forwards_per_window":
                1,

            "checkpoint_deserialized_for_ood":
                True,

            "model_weights_loaded_for_ood":
                True,

            "model_forward_executed_for_ood":
                True,

            "task_logits_read_for_ood":
                True,

            "penultimate_feature_tensor_returned":
                True,

            "penultimate_feature_used_by_selected_score":
                False,

            "second_full_task_model_forward_used":
                False,

            "ood_score_computed":
                True,

            "ood_threshold_selected":
                True,

            "external_domain_shift_data_used":
                False,

            "final_test_data_opened":
                False,

            "final_test_ood_outputs_read":
                False,

            "legacy_pickle_compatibility_source_verified":
                True,

            "legacy_pickle_compatibility_class_used_for_symbol_resolution":
                True,

            "legacy_pickle_compatibility_class_instantiated":
                False,

            "legacy_pickle_compatibility_class_forward_executed":
                False,

            "failed_evaluator_v1_calibration_windows_forwarded":
                0,

            "failed_evaluator_v1_ood_margins_exposed":
                False,

            "integrity_operating_point_reopened":
                False,
        },
    }


def build_result(
    evaluator_commit: str,
    calibration,
):
    protocol = load_protocol()

    result = {
        "result_id":
            "OOD_CALIBRATION_V1_CANDIDATE",

        "status":
            "calibration_complete_operating_point_candidate_not_yet_frozen",

        "partition":
            "calibration",

        "source_anchors": {
            "ood_calibration_protocol": {
                "tag":
                    PROTOCOL_TAG,

                "tag_commit":
                    PROTOCOL_COMMIT,

                "content_sha256":
                    PROTOCOL_CONTENT_SHA256,

                "raw_sha256":
                    PROTOCOL_RAW_SHA256,
            },

            "ood_calibration_evaluator": {
                "tag":
                    EVALUATOR_TAG,

                "tag_commit":
                    evaluator_commit,

                "raw_sha256":
                    file_sha256(
                        Path(
                            __file__
                        ).resolve()
                    ),
            },

            "failed_ood_calibration_evaluator_v1": {
                "tag":
                    FAILED_EVALUATOR_V1_TAG,

                "tag_commit":
                    FAILED_EVALUATOR_V1_COMMIT,

                "raw_sha256":
                    FAILED_EVALUATOR_V1_RAW_SHA256,

                "failure_boundary":
                    (
                        "checkpoint_deserialization_failed_before_"
                        "protected_model_load_or_any_calibration_forward"
                    ),

                "calibration_windows_forwarded":
                    0,

                "ood_margins_exposed":
                    False,
            },

            "legacy_pickle_compatibility": {
                "root":
                    str(
                        LEGACY_COMPATIBILITY_ROOT
                    ),

                "checkpoint_hparams_path":
                    str(
                        LEGACY_CHECKPOINT_HPARAMS
                    ),

                "checkpoint_hparams_raw_sha256":
                    LEGACY_CHECKPOINT_HPARAMS_RAW_SHA256,

                "files":
                    dict(
                        LEGACY_COMPATIBILITY_FILES
                    ),

                "cnn_ast_class_source_sha256":
                    LEGACY_CNN_AST_CLASS_SOURCE_SHA256,

                "role":
                    "pickle_symbol_resolution_only",

                "legacy_cnn_instantiated":
                    False,

                "legacy_cnn_forward_executed":
                    False,
            },

            "integrity_final_test_result": {
                "tag":
                    "integrity-final-test-result-v1",

                "tag_commit":
                    INTEGRITY_FINAL_RESULT_COMMIT,
            },

            "protected_baseline": {
                "tag":
                    "baseline-date2025-cnn400-v1",

                "tag_commit":
                    BASELINE_COMMIT,

                "model_source_raw_sha256":
                    MODEL_SOURCE_RAW_SHA256,

                "checkpoint_sha256":
                    CHECKPOINT_SHA256,
            },

            "reliability_registry": {
                "tag":
                    "reliability-eval-registry-v1",

                "tag_commit":
                    REGISTRY_COMMIT,

                "raw_sha256":
                    file_sha256(
                        REGISTRY
                    ),
            },
        },

        "evaluation_contract": {
            "selected_method":
                "top_two_logit_margin",

            "score_formula":
                "abs(logit_0 - logit_1)",

            "smaller_margin_is_more_unfamiliar":
                True,

            "unknown_rule":
                "margin < threshold",

            "accepted_rule":
                "margin >= threshold",

            "ties_at_threshold_accepted":
                True,

            "single_global_threshold":
                True,

            "clean_id_acceptance_target_per_nonempty_dataset_x_class_stratum":
                0.99,

            "method_selected_before_calibration_output_exposure":
                True,

            "method_comparison_performed":
                False,

            "feature_distance_method_evaluated":
                False,

            "energy_method_evaluated":
                False,

            "msp_method_evaluated":
                False,

            "true_ood_positive_calibration_population_used":
                False,

            "true_ood_metrics_claimed":
                False,

            "auroc_claimed":
                False,

            "ood_recall_claimed":
                False,

            "external_extra_recordings_used":
                False,

            "second_full_task_forward_used":
                False,

            "final_test_outputs_used":
                False,

            "integrity_operating_point_reopened":
                False,

            "threshold_may_change_after_result_review":
                False,
        },

        "threshold_selection": {
            "selected_threshold":
                calibration[
                    "selected_threshold"
                ],

            "per_stratum":
                calibration[
                    "per_stratum"
                ],

            "binding_strata": [
                {
                    "dataset":
                        row[
                            "dataset"
                        ],

                    "class":
                        row[
                            "class"
                        ],

                    "q_s":
                        row[
                            "q_s"
                        ],
                }
                for row
                in calibration[
                    "per_stratum"
                ]
                if row[
                    "binding_global_threshold"
                ]
            ],

            "selection_rule":
                (
                    "threshold = min(sorted_margin_s[floor(0.01*n_s)] "
                    "over all nonempty protected calibration "
                    "dataset_x_class strata)"
                ),
        },

        "clean_id_metrics": {
            "overall":
                calibration[
                    "overall_clean_id"
                ],

            "by_dataset":
                calibration[
                    "by_dataset"
                ],

            "by_class":
                calibration[
                    "by_class"
                ],
        },

        "task_metrics_descriptive_only":
            calibration[
                "task_metrics_descriptive_only"
            ],

        "access_audit":
            calibration[
                "access_audit"
            ],

        "claim_boundary": {
            "ood_unknown_means":
                (
                    "coverage-controlled residual task-model "
                    "unfamiliarity on an otherwise integrity-valid window"
                ),

            "ood_unknown_does_not_mean":
                [
                    "proven_novel_activity_class",
                    "proven_sensor_failure",
                    "qualified_integrity_cause",
                    "calibrated_true_ood_probability",
                ],

            "calibration_result_contains_true_ood_detection_performance":
                False,
        },

        "protocol_snapshot": {
            "runtime_decision_precedence":
                protocol[
                    "runtime_contract"
                ][
                    "decision_precedence"
                ],

            "classifier_bypass_enabled":
                protocol[
                    "runtime_contract"
                ][
                    "classifier_bypass_enabled"
                ],

            "task_prediction_still_returned":
                protocol[
                    "runtime_contract"
                ][
                    "task_prediction_still_returned"
                ],
        },
    }

    result[
        "content_sha256"
    ] = canonical_digest(
        result
    )

    return result


def build_operating_point_candidate(
    result,
):
    threshold = float(
        result[
            "threshold_selection"
        ][
            "selected_threshold"
        ]
    )

    op = {
        "operating_point_id":
            "OOD_OPERATING_POINT_V1_CANDIDATE",

        "status":
            "candidate_from_frozen_calibration_result_not_yet_frozen",

        "selected_method":
            "top_two_logit_margin",

        "score_formula":
            "abs(logit_0 - logit_1)",

        "threshold":
            threshold,

        "unknown_rule":
            "margin < threshold",

        "accepted_rule":
            "margin >= threshold",

        "ties_at_threshold_accepted":
            True,

        "clean_id_acceptance_target":
            0.99,

        "threshold_selection_rule":
            (
                "minimum per-stratum one-percent lower-tail "
                "order statistic over all nonempty protected "
                "calibration dataset_x_class strata"
            ),

        "binding_strata":
            result[
                "threshold_selection"
            ][
                "binding_strata"
            ],

        "runtime_contract": {
            "decision_precedence": [
                "qualified_integrity_hard_cause",
                "ood_margin_gate",
                "valid",
            ],

            "integrity_alert_state":
                "INTEGRITY_ALERT(C_t)",

            "ood_state":
                "OOD_UNKNOWN",

            "valid_state":
                "VALID",

            "classifier_bypass_enabled":
                False,

            "task_prediction_still_computed":
                True,

            "task_prediction_still_returned":
                True,

            "task_model_forwards_per_window":
                1,

            "second_full_task_forward_allowed":
                False,

            "selected_score_uses":
                "task_logits_from_same_single_forward",

            "feature_vector_used_by_selected_score":
                False,
        },

        "claim_boundary": {
            "calibrated_from_clean_id_coverage_only":
                True,

            "true_ood_positive_calibration_data_used":
                False,

            "true_ood_detection_probability_claimed":
                False,

            "external_domain_shift_result_used_for_selection":
                False,
        },

        "source_result": {
            "result_id":
                result[
                    "result_id"
                ],

            "content_sha256":
                result[
                    "content_sha256"
                ],
        },

        "source_protocol": {
            "tag":
                PROTOCOL_TAG,

            "tag_commit":
                PROTOCOL_COMMIT,

            "content_sha256":
                PROTOCOL_CONTENT_SHA256,
        },

        "source_evaluator": {
            "tag":
                result[
                    "source_anchors"
                ][
                    "ood_calibration_evaluator"
                ][
                    "tag"
                ],

            "tag_commit":
                result[
                    "source_anchors"
                ][
                    "ood_calibration_evaluator"
                ][
                    "tag_commit"
                ],

            "raw_sha256":
                result[
                    "source_anchors"
                ][
                    "ood_calibration_evaluator"
                ][
                    "raw_sha256"
                ],
        },

        "final_test_contract": {
            "final_test_outputs_used_for_selection":
                False,

            "threshold_may_change_after_final_test":
                False,

            "method_may_change_after_final_test":
                False,

            "integrity_operating_point_may_change":
                False,
        },
    }

    op[
        "content_sha256"
    ] = canonical_digest(
        op
    )

    return op


def main():
    verify_frozen_inputs()

    evaluator_commit = (
        verify_evaluator_is_frozen()
    )

    for path in (
        RESULT,
        OPERATING_POINT_CANDIDATE,
    ):
        if path.exists():
            raise RuntimeError(
                f"Refusing to overwrite existing calibration artifact: "
                f"{path}"
            )

    model = (
        load_protected_model()
    )

    calibration = (
        evaluate_calibration(
            model
        )
    )

    result = build_result(
        evaluator_commit,
        calibration,
    )

    op = build_operating_point_candidate(
        result
    )

    RESULT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OPERATING_POINT_CANDIDATE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    RESULT.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    OPERATING_POINT_CANDIDATE.write_text(
        json.dumps(
            op,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "OOD_CALIBRATION_V1_COMPLETE = True"
    )

    print(
        "CALIBRATION_WINDOWS_FORWARDED =",
        result[
            "access_audit"
        ][
            "calibration_windows_forwarded"
        ],
    )

    print(
        "MODEL_BATCH_FORWARD_CALLS =",
        result[
            "access_audit"
        ][
            "model_batch_forward_calls"
        ],
    )

    print(
        "SELECTED_METHOD =",
        op[
            "selected_method"
        ],
    )

    print(
        "SELECTED_THRESHOLD =",
        op[
            "threshold"
        ],
    )

    print(
        "OVERALL_CLEAN_ID_ACCEPTANCE =",
        result[
            "clean_id_metrics"
        ][
            "overall"
        ][
            "empirical_acceptance"
        ],
    )

    for row in result[
        "threshold_selection"
    ][
        "per_stratum"
    ]:
        print(
            "STRATUM",
            row[
                "dataset"
            ],
            row[
                "class"
            ],
            "n=",
            row[
                "n"
            ],
            "r_s=",
            row[
                "r_s"
            ],
            "q_s=",
            row[
                "q_s"
            ],
            "accepted=",
            row[
                "accepted_count"
            ],
            "acceptance=",
            row[
                "empirical_acceptance"
            ],
            "binding=",
            row[
                "binding_global_threshold"
            ],
        )

    print(
        "RESULT_CONTENT_SHA256 =",
        result[
            "content_sha256"
        ],
    )

    print(
        "OPERATING_POINT_CANDIDATE_CONTENT_SHA256 =",
        op[
            "content_sha256"
        ],
    )

    print(
        "FEATURE_VECTOR_USED_BY_SELECTED_SCORE = False"
    )

    print(
        "SECOND_FULL_TASK_MODEL_FORWARD_USED = False"
    )

    print(
        "TRUE_OOD_METRICS_CLAIMED = False"
    )

    print(
        "FINAL_TEST_OOD_OUTPUTS_READ = False"
    )

    print(
        "INTEGRITY_OPERATING_POINT_REOPENED = False"
    )


if __name__ == "__main__":
    main()
