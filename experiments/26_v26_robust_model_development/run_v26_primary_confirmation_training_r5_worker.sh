#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
PY="/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/protechto311/bin/python"

OUT="$ROOT/results/v26_primary_confirmation_training_r5"

RUNNER="$ROOT/experiments/26_v26_robust_model_development/run_v26_primary_confirmation_training_r5.py"

rm -f "$OUT/COMPLETE"

echo "============================================================"
echo "V26 PRIMARY CONFIRMATION TRAINING R5 WORKER START"
date --iso-8601=seconds
echo "============================================================"

CUDA_VISIBLE_DEVICES=0 \
"$PY" -u "$RUNNER"


echo
echo "============================================================"
echo "R5 FINAL RECEIPT VALIDATION"
echo "============================================================"

"$PY" - \
"$OUT/v26_primary_confirmation_training_receipt_r5.json" \
"$OUT/frozen_confirmation_checkpoint_manifest_14.csv" \
<<'PY'
import csv
import hashlib
import json
import sys
from pathlib import Path

root = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

receipt = json.loads(
    Path(
        sys.argv[1]
    ).read_text()
)


required = {
    "status":
        "PASS",

    "promoted_candidate":
        "V26C_DualGateLiteCons",

    "confirmation_training_manifest":
        "PASS_14_OF_14",

    "confirmation_training_runs":
        "PASS_14_OF_14",

    "confirmation_checkpoints":
        "FROZEN_SHA_PASS_14_OF_14",

    "training_run_count":
        14,

    "train_only_normalization":
        "PASS_4_OF_4",

    "validation_only_checkpoint_selection":
        True,

    "candidate_modified":
        False,

    "training_protocol_modified":
        False,

    "fault_protocol_modified":
        False,

    "loss_weight_modified":
        False,

    "protected_test_split_loaded":
        False,

    "protected_test_inference_performed":
        False,

    "storm_inference_performed":
        False,

    "storm_used_for_selection":
        False,

    "all_14_checkpoints_frozen_before_test":
        True,
}


for key, expected in required.items():

    actual = receipt.get(
        key
    )

    if actual != expected:

        raise RuntimeError(
            f"R5 receipt mismatch: "
            f"{key}={actual!r}, "
            f"expected={expected!r}"
        )


manifest_path = Path(
    sys.argv[2]
)


with manifest_path.open(
    newline="",
    encoding="utf-8",
) as f:

    rows = list(
        csv.DictReader(f)
    )


if len(rows) != 14:

    raise RuntimeError(
        f"Expected 14 frozen checkpoints, "
        f"found {len(rows)}"
    )


def sha(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):

            h.update(block)

    return h.hexdigest()


for row in rows:

    checkpoint = (
        root
        / row[
            "checkpoint"
        ]
    )


    if not checkpoint.exists():

        raise FileNotFoundError(
            checkpoint
        )


    actual = sha(
        checkpoint
    )


    if actual != row[
        "checkpoint_sha256"
    ]:

        raise RuntimeError(
            f"Checkpoint SHA mismatch: "
            f"{checkpoint}"
        )


print(
    "V26_R5_FINAL_RECEIPT_GATE_PASS=True"
)

print(
    "V26_R5_CHECKPOINT_MANIFEST_SHA_PASS_14_OF_14=True"
)

print(
    "PROTECTED_TEST_REMAINS_LOCKED=True"
)
PY


# ============================================================
# Freeze R5 evidence, including all 14 checkpoints
# ============================================================

echo
echo "============================================================"
echo "FREEZE V26 CONFIRMATION TRAINING R5"
echo "============================================================"

(
    cd "$OUT"

    find . -type f \
        ! -name SHA256SUMS.txt \
        ! -name COMPLETE \
        -print0 |
        sort -z |
        xargs -0 sha256sum \
        > SHA256SUMS.txt
)

sha256sum \
    "$OUT/SHA256SUMS.txt"

touch "$OUT/COMPLETE"


echo
echo "V26_PRIMARY_CONFIRMATION_TRAINING_R5_FROZEN_COMPLETE=True"
date --iso-8601=seconds
