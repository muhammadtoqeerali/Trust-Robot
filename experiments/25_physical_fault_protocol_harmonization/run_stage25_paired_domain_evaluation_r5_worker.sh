#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
PY="/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/protechto311/bin/python"

OUT="$ROOT/results/stage25_physical_fault_protocol/paired_domain_evaluation_r5"
SCRIPT="$ROOT/experiments/25_physical_fault_protocol_harmonization/run_stage25_paired_domain_evaluation_r5.py"

rm -f "$OUT/COMPLETE"

echo "============================================================"
echo "STAGE25 R5 WORKER START"
date --iso-8601=seconds
echo "============================================================"

CUDA_VISIBLE_DEVICES=0 \
"$PY" "$SCRIPT"

echo
echo "============================================================"
echo "R5 FINAL RECEIPT VALIDATION"
echo "============================================================"

"$PY" - \
"$OUT/stage25_paired_domain_evaluation_receipt_r5.json" \
<<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])

obj = json.loads(
    path.read_text()
)

required = {
    "status":
        "PASS",

    "scientific_protocol":
        "FROZEN_R3_UNCHANGED",

    "r4a_tensor_sha":
        "PASS_140_OF_140",

    "canonical_clean_tensor_identity":
        "PASS_4_OF_4",

    "frozen_model_bank":
        "PASS_200_OF_200",

    "clean_baseline_rows":
        200,

    "clean_forward_performed_in_r5":
        False,

    "corrupted_forward_rows":
        6800,

    "total_analysis_rows":
        7000,

    "checkpoint_domain_summaries":
        400,

    "paired_domain_delta_rows":
        200,

    "dataset_model_domain_summary_rows":
        80,

    "equal_dataset_model_domain_summary_rows":
        20,

    "model_construction_count":
        200,

    "checkpoint_deserialization_count":
        200,

    "corrupted_forward_count":
        6800,

    "training_performed":
        False,

    "optimizer_created":
        False,

    "backward_performed":
        False,

    "checkpoint_modified":
        False,

    "dataset_modified":
        False,

    "fault_definition_modified":
        False,

    "fault_severity_modified":
        False,

    "fault_seed_modified":
        False,

    "aggregation_modified":
        False,

    "v25_retrained":
        False,

    "storm_used_for_tuning":
        False,
}


for key, expected in required.items():

    actual = obj.get(key)

    if actual != expected:

        raise RuntimeError(
            f"R5 receipt mismatch: "
            f"{key}={actual!r}, "
            f"expected={expected!r}"
        )


print(
    "R5_FINAL_RECEIPT_GATE_PASS=True"
)
PY


echo
echo "============================================================"
echo "FREEZE R5"
echo "============================================================"

(
    cd "$OUT"

    find . -maxdepth 1 -type f \
        ! -name SHA256SUMS.txt \
        ! -name COMPLETE \
        -print0 |
        sort -z |
        xargs -0 sha256sum \
        > SHA256SUMS.txt
)

sha256sum "$OUT/SHA256SUMS.txt"

touch "$OUT/COMPLETE"

echo
echo "STAGE25_R5_FROZEN_COMPLETE=True"
date --iso-8601=seconds
