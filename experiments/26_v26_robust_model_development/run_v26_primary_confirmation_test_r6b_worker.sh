#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
PY="/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/protechto311/bin/python"

OUT="$ROOT/results/v26_primary_confirmation_test_r6b"

RUNNER="$ROOT/experiments/26_v26_robust_model_development/run_v26_primary_confirmation_test_r6b.py"


if [ -f "$OUT/COMPLETE" ]; then
    echo "R6B_ALREADY_COMPLETE=True"
    exit 1
fi


if [ -f "$OUT/MODEL_FORWARD_STARTED" ]; then
    echo "MODEL_FORWARD_ALREADY_STARTED=True"
    echo "REFUSING_AUTOMATIC_PROTECTED_RERUN=True"
    exit 1
fi


if [ -f "$OUT/PROTECTED_TEST_CONSUMED" ]; then
    echo "PROTECTED_TEST_ALREADY_CONSUMED=True"
    echo "REFUSING_AUTOMATIC_PROTECTED_RERUN=True"
    exit 1
fi


echo "============================================================"
echo "V26 R6B PROTECTED CONFIRMATION WORKER START"
date --iso-8601=seconds
echo "============================================================"


CUDA_VISIBLE_DEVICES=0 \
"$PY" -u "$RUNNER"


echo
echo "============================================================"
echo "V26 R6B FINAL RECEIPT VALIDATION"
echo "============================================================"


"$PY" - \
"$OUT/v26_primary_confirmation_test_receipt_r6b.json" \
"$OUT/protected_confirmation_cases_252.csv" \
<<'PY'
import csv
import json
import sys
from pathlib import Path

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

    "evaluation_domain":
        "pre_normalization_sensor_domain",

    "frozen_checkpoint_sha":
        "PASS_14_OF_14",

    "r4a_tensor_sha_preflight":
        "PASS_140_OF_140",

    "protected_tensor_sha_preflight":
        "PASS_72_OF_72",

    "all_protected_tensors_verified_before_first_forward":
        True,

    "protected_confirmation_checkpoints":
        14,

    "conditions_per_checkpoint":
        18,

    "protected_test_case_rows":
        252,

    "checkpoint_physical_summary_rows":
        14,

    "dataset_summary_rows":
        4,

    "comparison_model_count":
        11,

    "comparison_ranking_rows":
        88,

    "protected_test_split_loaded":
        True,

    "protected_test_tensor_loaded":
        True,

    "protected_test_inference_performed":
        True,

    "training_performed":
        False,

    "optimizer_created":
        False,

    "backward_performed":
        False,

    "candidate_modified":
        False,

    "training_protocol_modified":
        False,

    "fault_protocol_modified":
        False,

    "checkpoint_modified":
        False,

    "storm_used":
        False,

    "candidate_retraining_after_confirmation_allowed":
        False,
}


for key, expected in required.items():

    actual = receipt.get(
        key
    )

    if actual != expected:

        raise RuntimeError(
            f"R6B receipt mismatch: "
            f"{key}={actual!r}; "
            f"expected={expected!r}"
        )


with Path(
    sys.argv[2]
).open(
    newline="",
    encoding="utf-8",
) as f:

    rows = list(
        csv.DictReader(f)
    )


if len(rows) != 252:

    raise RuntimeError(
        f"Expected 252 protected rows, "
        f"found {len(rows)}"
    )


identity_count = len({
    (
        row["dataset"],
        int(row["seed"]),
        row["condition"],
    )
    for row in rows
})


if identity_count != 252:

    raise RuntimeError(
        f"Protected identity count "
        f"{identity_count} != 252"
    )


print(
    "V26_R6B_FINAL_RECEIPT_GATE_PASS=True"
)

print(
    "V26_R6B_CASE_CARDINALITY_PASS_252_OF_252=True"
)

print(
    "V26_R6B_NO_RETRAINING_GATE_PASS=True"
)
PY


echo
echo "============================================================"
echo "FREEZE V26 R6B PROTECTED CONFIRMATION"
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
echo "V26_PRIMARY_CONFIRMATION_TEST_R6B_FROZEN_COMPLETE=True"
date --iso-8601=seconds
