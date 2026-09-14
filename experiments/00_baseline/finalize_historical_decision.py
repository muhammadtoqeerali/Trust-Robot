from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

INPUT = (
    ROOT
    / "results/raw/baseline/"
      "date2025_cnn400_clean_predictions_v1.csv"
)

OUTPUT = (
    ROOT
    / "results/summaries/baseline/"
      "date2025_cnn400_historical_decision_metrics_v1.json"
)

BIAS = 0.9


counts = defaultdict(
    lambda: {
        "tn": 0,
        "fp": 0,
        "fn": 0,
        "tp": 0,
    }
)


with INPUT.open(
    newline="",
) as f:
    reader = csv.DictReader(f)

    for row in reader:
        split = row["split"]

        y_true = int(
            row["y_true"]
        )

        p_fall = float(
            row["fall_probability"]
        )

        # Exact binary simplification of recovered Simulator.get_output
        # for prediction_bias=0.9.
        y_pred = int(
            p_fall > BIAS
        )

        c = counts[split]

        if y_true == 0 and y_pred == 0:
            c["tn"] += 1
        elif y_true == 0 and y_pred == 1:
            c["fp"] += 1
        elif y_true == 1 and y_pred == 0:
            c["fn"] += 1
        elif y_true == 1 and y_pred == 1:
            c["tp"] += 1


def safe_div(a, b):
    return (
        a / b
        if b
        else 0.0
    )


def metrics(c):
    tn = c["tn"]
    fp = c["fp"]
    fn = c["fn"]
    tp = c["tp"]

    n = tn + fp + fn + tp

    precision_activity = safe_div(
        tn,
        tn + fn,
    )

    recall_activity = safe_div(
        tn,
        tn + fp,
    )

    f1_activity = safe_div(
        2
        * precision_activity
        * recall_activity,
        precision_activity
        + recall_activity,
    )

    precision_fall = safe_div(
        tp,
        tp + fp,
    )

    recall_fall = safe_div(
        tp,
        tp + fn,
    )

    f1_fall = safe_div(
        2
        * precision_fall
        * recall_fall,
        precision_fall
        + recall_fall,
    )

    return {
        "n_windows": n,
        "confusion_matrix": [
            [tn, fp],
            [fn, tp],
        ],
        "accuracy": safe_div(
            tn + tp,
            n,
        ),
        "macro_precision": (
            precision_activity
            + precision_fall
        ) / 2,
        "macro_recall": (
            recall_activity
            + recall_fall
        ) / 2,
        "macro_f1": (
            f1_activity
            + f1_fall
        ) / 2,
        "fall_precision":
            precision_fall,
        "fall_recall":
            recall_fall,
        "fall_f1":
            f1_fall,
        "fall_false_negative_rate":
            safe_div(
                fn,
                fn + tp,
            ),
    }


result = {
    "baseline_id":
        "DATE2025_CNN_400MS_RECONSTRUCTED_V1",

    "scope":
        "window_level_historical_simulator_decision",

    "decision_rule": {
        "source":
            "recovered Simulator.get_output",

        "prediction_bias":
            BIAS,

        "general_rule":
            (
                "default Activity; accept argmax only "
                "when max(softmax(logits)) > 0.9"
            ),

        "binary_equivalent":
            "Falling iff P(Falling) > 0.9",

        "comparison":
            "strict_greater_than",

        "threshold_filter_active":
            False,

        "smoothing_active":
            False,
    },

    "validation":
        metrics(
            counts["validation"]
        ),

    "test":
        metrics(
            counts["test"]
        ),
}

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT.write_text(
    json.dumps(
        result,
        indent=2,
    )
    + "\n"
)

print(
    json.dumps(
        result,
        indent=2,
    )
)

print()
print(
    "OUTPUT =",
    OUTPUT,
)
