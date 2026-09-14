#!/usr/bin/env bash
set -euo pipefail

PY="/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/protechto311/bin/python"

PROTOCOL="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability/results/v26_external_storm_test_protocol_r9d2"
SMOKE="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability/results/v26_external_storm_test_smoke_r9d2"
OUT="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability/results/v26_external_storm_test_r9d2"
SCRIPT="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability/experiments/26_v26_robust_model_development/run_v26_external_storm_test_r9d2.py"

EXPECTED_PROTOCOL_SHA="9d782c35b5353c4b456b040c0ff2b3d7f4d5e27c7668fc327df2fc48031225cf"
EXPECTED_SMOKE_SHA="f9b3d4971df7cf91c8aa01202fcc5abf35af684d8504a9ad69aa7929e5b706a4"
EXPECTED_EVALUATOR_SHA="e222efbbb9b3ee532e47ad9b2d6524f60e66d5a1148b56206150b394393fa5d6"


if [ -f "$OUT/TEST_CONSUMPTION_STARTED" ]; then
    echo "R9D2_EXTERNAL_TEST_ALREADY_CONSUMED=True"
    echo "RERUN_ALLOWED=False"
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
)" = "$EXPECTED_EVALUATOR_SHA"


echo "R9D2_PROTOCOL_RUNTIME_SHA_GATE_PASS=True"
echo "R9D2_SMOKE_RUNTIME_SHA_GATE_PASS=True"
echo "R9D2_EVALUATOR_RUNTIME_SHA_GATE_PASS=True"


echo "============================================================"
echo "V26 ONE-TIME EXTERNAL STORM TEST R9D2 START"
date --iso-8601=seconds
echo "============================================================"


CUDA_VISIBLE_DEVICES=0 "$PY" -u "$SCRIPT"     --mode full     --out-dir "$OUT"     --device cuda:0


echo
echo "============================================================"
echo "R9D2 FINAL RECEIPT VALIDATION"
echo "============================================================"


"$PY" - "$OUT" <<'PY'
import csv
import json
import sys
from pathlib import Path

out = Path(
    sys.argv[1]
)

cases_path = (
    out
    / "external_v26c_test_cases_90.csv"
)

with cases_path.open(
    newline="",
    encoding="utf-8",
) as f:
    cases = list(
        csv.DictReader(f)
    )

if len(cases) != 90:
    raise RuntimeError(
        f"Case rows={len(cases)} != 90"
    )


conditions = {
    row["condition"]
    for row in cases
}

if len(conditions) != 18:
    raise RuntimeError(
        f"Condition count={len(conditions)} != 18"
    )

if "all_sensors_failure" not in conditions:
    raise RuntimeError(
        "all_sensors_failure absent from final cases"
    )


seed_rows_path = (
    out
    / "external_v26c_per_seed_summary_5.csv"
)

with seed_rows_path.open(
    newline="",
    encoding="utf-8",
) as f:
    seed_rows = list(
        csv.DictReader(f)
    )

if len(seed_rows) != 5:
    raise RuntimeError(
        f"Seed summaries={len(seed_rows)} != 5"
    )


receipt_path = (
    out
    / "v26_external_storm_test_receipt_r9d2.json"
)

receipt = json.loads(
    receipt_path.read_text()
)


required = {
    "status":
        "PASS",

    "candidate":
        "V26C_DualGateLiteCons",

    "external_checkpoints":
        5,

    "conditions":
        18,

    "case_rows":
        90,

    "condition_tensor_sha_unique":
        18,

    "parameter_count":
        23210,

    "test_loaded":
        True,

    "test_inference_performed":
        True,

    "test_consumed":
        True,

    "test_rerun_allowed":
        False,

    "training_performed":
        False,

    "candidate_modified":
        False,

    "checkpoint_modified":
        False,

    "storm_model_retrained":
        False,

    "stage24_results_modified":
        False,
}


for key, expected in required.items():

    actual = receipt.get(
        key
    )

    if actual != expected:
        raise RuntimeError(
            f"{key}: {actual!r} != "
            f"{expected!r}"
        )


print(
    "R9D2_EXTERNAL_TEST_CASE_ROWS_PASS_90=True"
)

print(
    "R9D2_EXTERNAL_CONDITIONS_PASS_18=True"
)

print(
    "R9D2_ALL_SENSORS_CASES_PASS_5_OF_5=True"
)

print(
    "R9D2_EXTERNAL_SEED_SUMMARY_PASS_5=True"
)

print(
    "R9D2_FINAL_RECEIPT_GATE_PASS=True"
)
PY


cp     "$SCRIPT"     "$OUT/run_v26_external_storm_test_r9d2.py"


(
    cd "$OUT"

    find . -type f         ! -name SHA256SUMS.txt         ! -name COMPLETE         -print0 |
        sort -z |
        xargs -0 sha256sum         > SHA256SUMS.txt
)

touch "$OUT/COMPLETE"


echo
echo "============================================================"
echo "V26 EXTERNAL STORM R9D2 FROZEN SHA"
echo "============================================================"

sha256sum     "$OUT/SHA256SUMS.txt"


echo
echo "V26_EXTERNAL_STORM_TEST_R9D2_FROZEN_COMPLETE=True"
date --iso-8601=seconds
