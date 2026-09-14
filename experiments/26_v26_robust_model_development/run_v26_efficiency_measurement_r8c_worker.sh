#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"
PY="/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/protechto311/bin/python"

R8A="$ROOT/results/v26_efficiency_protocol_r8a"
R8B="$ROOT/results/v26_efficiency_implementation_integrity_r8b"
FREEZE="$ROOT/results/v26_efficiency_profiler_freeze_r8c0"
OUT="$ROOT/results/v26_efficiency_measurement_r8c"

SCRIPT="$ROOT/experiments/26_v26_robust_model_development/run_v26_efficiency_measurement_r8c.py"

EXPECTED_R8A_SHA="7d15e6f55fd5ad2c3306342050d2781e10bfa81405619428c449e9da3e9c8f5e"
EXPECTED_R8B_SHA="fb67856fc4d46cbb462579da96a6ceb25b0b5e809d668d7fdda494ea5999d9a9"
EXPECTED_PROFILER_SHA="5c640f8367c6abb2f2b9a047412bb4f73161ab64992b01c90d32c3de90acd97c"
EXPECTED_PROFILER_FREEZE_SHA="592e9dec07b3e56037d63e06fea4851ea4b75642a1237e10cc100a286eaac68e"


if [ -f "$OUT/COMPLETE" ]; then
    echo "R8C_ALREADY_COMPLETE=True"
    exit 1
fi

if [ -f "$OUT/TIMING_STARTED" ]; then
    echo "R8C_TIMING_ALREADY_STARTED=True"
    echo "REFUSING_SECOND_TIMING_EXECUTION=True"
    exit 1
fi


for SPEC in     "R8A|$R8A|$EXPECTED_R8A_SHA"     "R8B|$R8B|$EXPECTED_R8B_SHA"     "PROFILER_FREEZE|$FREEZE|$EXPECTED_PROFILER_FREEZE_SHA"
do
    IFS='|' read -r NAME DIR EXPECTED <<< "$SPEC"

    ACTUAL="$(
        sha256sum "$DIR/SHA256SUMS.txt" |
        awk '{print $1}'
    )"

    if [ "$ACTUAL" != "$EXPECTED" ]; then
        echo "${NAME}_RUNTIME_SHA_GATE_PASS=False"
        exit 1
    fi

    echo "${NAME}_RUNTIME_SHA_GATE_PASS=True"
done


ACTUAL_PROFILER_SHA="$(
    sha256sum "$SCRIPT" |
    awk '{print $1}'
)"

if [ "$ACTUAL_PROFILER_SHA" != "$EXPECTED_PROFILER_SHA" ]; then
    echo "R8C_PROFILER_RUNTIME_SHA_GATE_PASS=False"
    exit 1
fi

echo "R8C_PROFILER_RUNTIME_SHA_GATE_PASS=True"


echo "============================================================"
echo "V26 R8C FROZEN EFFICIENCY WORKER START"
date --iso-8601=seconds
echo "============================================================"


CUDA_VISIBLE_DEVICES=0 "$PY" -u "$SCRIPT"


echo
echo "============================================================"
echo "R8C FINAL RECEIPT VALIDATION"
echo "============================================================"


"$PY" - "$OUT/v26_efficiency_measurement_receipt_r8c.json" <<'PY'
import json
import sys
from pathlib import Path

x = json.loads(
    Path(sys.argv[1]).read_text()
)

required = {
    "status": "PASS",
    "model_count": 11,
    "measurement_rows": 11,
    "batch1_latency_sample_rows": 22000,

    "cpu_batch1_warmup": 200,
    "cpu_batch1_iterations": 1000,

    "gpu_batch1_warmup": 200,
    "gpu_batch1_iterations": 1000,

    "gpu_batch64_warmup": 100,
    "gpu_batch64_iterations": 500,

    "synthetic_input_only": True,
    "cpu_threads": 1,

    "model_eval": True,
    "inference_mode": True,

    "torch_compile": False,
    "mixed_precision": False,
    "quantization": False,

    "mac_flop": "NOT_COMPARABLE",

    "checkpoint_sha_verified": "PASS_11_OF_11",
    "parameter_count_verified": "PASS_11_OF_11",

    "latency_timing_performed": True,
    "throughput_timing_performed": True,

    "protected_test_access": False,
    "real_dataset_access": False,

    "training_performed": False,
    "optimizer_created": False,

    "candidate_modified": False,
    "checkpoint_modified": False,

    "storm_used": False,
    "deployment_claim_allowed": False,
}

for key, expected in required.items():

    actual = x.get(key)

    if actual != expected:

        raise RuntimeError(
            f"R8C receipt mismatch: "
            f"{key}={actual!r}; expected={expected!r}"
        )

print(
    "V26_R8C_FINAL_RECEIPT_GATE_PASS=True"
)
PY


echo
echo "============================================================"
echo "FREEZE V26 R8C EFFICIENCY EVIDENCE"
echo "============================================================"


cp     "$SCRIPT"     "$OUT/run_v26_efficiency_measurement_r8c.py"


(
    cd "$OUT"

    find . -maxdepth 1 -type f         ! -name SHA256SUMS.txt         ! -name COMPLETE         -print0 |
        sort -z |
        xargs -0 sha256sum         > SHA256SUMS.txt
)


touch "$OUT/COMPLETE"


sha256sum "$OUT/SHA256SUMS.txt"


echo
echo "V26_EFFICIENCY_MEASUREMENT_R8C_FROZEN_COMPLETE=True"
date --iso-8601=seconds
