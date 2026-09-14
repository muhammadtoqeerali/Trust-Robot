#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
PY="/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/protechto311/bin/python"

OUT="$ROOT/results/v26_development_screening_r3"
SCRIPT="$ROOT/experiments/26_v26_robust_model_development/run_v26_development_screening_r3.py"

rm -f "$OUT/COMPLETE"

echo "============================================================"
echo "V26 DEVELOPMENT SCREENING R3 WORKER START"
date --iso-8601=seconds
echo "============================================================"

CUDA_VISIBLE_DEVICES=0 \
"$PY" -u "$SCRIPT"

echo
echo "============================================================"
echo "V26 R3 FINAL RECEIPT VALIDATION"
echo "============================================================"

"$PY" - \
"$OUT/v26_development_screening_receipt_r3.json" \
"$OUT/promotion_decision_r3.json" \
<<'PY'
import json
import sys
from pathlib import Path

receipt = json.loads(
    Path(
        sys.argv[1]
    ).read_text()
)

promotion = json.loads(
    Path(
        sys.argv[2]
    ).read_text()
)


required = {
    "status":
        "PASS",

    "frozen_v25_validation_baseline":
        "PASS_6_OF_6",

    "candidate_training_runs":
        "PASS_24_OF_24",

    "candidate_summary_rows":
        4,

    "promotion_rule_applied":
        True,

    "validation_only_model_selection":
        True,

    "test_inference_performed":
        False,

    "heldout_seed_inference_performed":
        False,

    "pamap_motionsense_inference_performed":
        False,

    "storm_used_for_selection":
        False,

    "storm_inference_performed":
        False,

    "candidate_training_performed":
        True,

    "candidate_checkpoints_saved":
        24,
}


for key, expected in required.items():

    actual = receipt.get(
        key
    )

    if actual != expected:

        raise RuntimeError(
            f"R3 receipt mismatch: "
            f"{key}={actual!r}, "
            f"expected={expected!r}"
        )


if promotion.get(
    "promotion_decision"
) not in {
    "PROMOTE_ONE",
    "PROMOTE_NONE",
}:

    raise RuntimeError(
        "Invalid frozen promotion decision"
    )


if promotion.get(
    "test_inference_performed"
) is not False:

    raise RuntimeError(
        "Unexpected test inference"
    )


if promotion.get(
    "storm_used_for_selection"
) is not False:

    raise RuntimeError(
        "Unexpected STORM selection use"
    )


print(
    "V26_R3_FINAL_RECEIPT_GATE_PASS=True"
)

print(
    "V26_PROMOTION_DECISION=",
    promotion[
        "promotion_decision"
    ],
)

print(
    "V26_PROMOTED_CANDIDATE=",
    promotion.get(
        "promoted_candidate"
    ),
)
PY


echo
echo "============================================================"
echo "FREEZE COMPLETE V26 R3"
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
echo "V26_DEVELOPMENT_SCREENING_R3_FROZEN_COMPLETE=True"
date --iso-8601=seconds
