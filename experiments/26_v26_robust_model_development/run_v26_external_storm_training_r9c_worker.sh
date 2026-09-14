#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
PY="/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/protechto311/bin/python"

PROTOCOL="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability/results/v26_external_storm_training_protocol_r9c1"
SMOKE="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability/results/v26_external_storm_training_smoke_r9c1"
OUT="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability/results/v26_external_storm_training_r9c"
SCRIPT="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability/experiments/26_v26_robust_model_development/run_v26_external_storm_training_r9c.py"

EXPECTED_PROTOCOL_SHA="f05680c68fcf0cc9884ca74ca4d416eb3cc796828714773b203a3ac44d2a1853"
EXPECTED_SMOKE_SHA="c1bc3725c92750b8e89a2f27936ac5d410756317da64df933c9799b7503301bc"
EXPECTED_TRAINER_SHA="6fce7afb94139cf9ffdc453646c041ebe38469ab197890fc0974138e5e3554e6"


if [ -f "$OUT/COMPLETE" ]; then
    echo "R9C_ALREADY_COMPLETE=True"
    exit 1
fi

if [ -f "$OUT/TRAINING_STARTED" ]; then
    echo "R9C_TRAINING_ALREADY_STARTED=True"
    echo "REFUSING_SECOND_R9C_RUN=True"
    exit 1
fi


test "$(
    sha256sum "$PROTOCOL/SHA256SUMS.txt" |
    awk '{print $1}'
)" = "$EXPECTED_PROTOCOL_SHA"

test "$(
    sha256sum "$SMOKE/SHA256SUMS.txt" |
    awk '{print $1}'
)" = "$EXPECTED_SMOKE_SHA"

test "$(
    sha256sum "$SCRIPT" |
    awk '{print $1}'
)" = "$EXPECTED_TRAINER_SHA"


echo "R9C1_PROTOCOL_RUNTIME_SHA_GATE_PASS=True"
echo "R9C1_SMOKE_RUNTIME_SHA_GATE_PASS=True"
echo "R9C1_TRAINER_RUNTIME_SHA_GATE_PASS=True"


echo "============================================================"
echo "V26 EXTERNAL STORM FIVE-SEED TRAINING R9C START"
date --iso-8601=seconds
echo "============================================================"


CUDA_VISIBLE_DEVICES=0 "$PY" -u "$SCRIPT"     --mode train-all     --out-dir "$OUT"     --device cuda:0


echo
echo "============================================================"
echo "R9C FINAL FIVE-CHECKPOINT VALIDATION"
echo "============================================================"


"$PY" - "$OUT" <<'PY'
import csv
import hashlib
import json
import sys
from pathlib import Path

root = Path(
    "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
)

out = Path(
    sys.argv[1]
)

manifest = (
    out
    / "external_v26c_checkpoint_manifest_5.csv"
)

with manifest.open(
    newline="",
    encoding="utf-8",
) as f:

    rows = list(
        csv.DictReader(f)
    )


if len(rows) != 5:
    raise RuntimeError(
        f"Checkpoint manifest rows={len(rows)} != 5"
    )


expected_seeds = {
    42,
    123,
    456,
    789,
    2026,
}


actual_seeds = {
    int(row["seed"])
    for row in rows
}


if actual_seeds != expected_seeds:
    raise RuntimeError(
        f"Seed mismatch: {actual_seeds}"
    )


for row in rows:

    checkpoint = (
        root
        / row["checkpoint"]
    )

    actual = hashlib.sha256(
        checkpoint.read_bytes()
    ).hexdigest()

    if actual != row[
        "checkpoint_sha256"
    ]:
        raise RuntimeError(
            f"Checkpoint SHA mismatch: "
            f"{checkpoint}"
        )


summary = json.loads(
    (
        out
        / "external_v26c_training_summary_r9c.json"
    ).read_text()
)


required = {
    "candidate":
        "V26C_DualGateLiteCons",

    "completed_runs":
        5,

    "parameter_count":
        23210,

    "all_checkpoints_frozen_before_external_test":
        True,

    "external_test_loaded":
        False,

    "external_test_inference":
        False,

    "candidate_modified":
        False,
}


for key, expected in required.items():

    actual = summary.get(key)

    if actual != expected:
        raise RuntimeError(
            f"{key}: {actual!r} != "
            f"{expected!r}"
        )


print(
    "R9C_EXTERNAL_CHECKPOINT_MANIFEST_PASS_5_OF_5=True"
)

print(
    "R9C_EXTERNAL_CHECKPOINT_SHA_PASS_5_OF_5=True"
)

print(
    "R9C_EXTERNAL_TEST_REMAINS_UNTOUCHED=True"
)
PY


cp     "$SCRIPT"     "$OUT/run_v26_external_storm_training_r9c.py"


(
    cd "$OUT"

    find . -type f         ! -name SHA256SUMS.txt         ! -name COMPLETE         -print0 |
        sort -z |
        xargs -0 sha256sum         > SHA256SUMS.txt
)

touch "$OUT/COMPLETE"


echo
echo "============================================================"
echo "V26 EXTERNAL STORM R9C FROZEN SHA"
echo "============================================================"

sha256sum     "$OUT/SHA256SUMS.txt"


echo
echo "V26_EXTERNAL_STORM_TRAINING_R9C_FROZEN_COMPLETE=True"
date --iso-8601=seconds
