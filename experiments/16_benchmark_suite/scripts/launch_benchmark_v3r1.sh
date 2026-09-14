#!/usr/bin/env bash

set -euo pipefail

cd ~/toqeer/IMU_Reliability

PY="/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/protechto311/bin/python"

RUNNER="experiments/16_benchmark_suite/run_benchmark_v3r1.py"

LOGROOT="results/logs"

mkdir -p "$LOGROOT"

if [ ! -f "results/benchmark_v3r1/PREFLIGHT_PASS" ]; then
    echo "V3R1_PREFLIGHT_MISSING=True"
    exit 20
fi

CURRENT="$(
    pgrep -f "$RUNNER" || true
)"

if [ -n "$CURRENT" ]; then
    echo "V3R1_ALREADY_RUNNING=True"
    echo "$CURRENT"
    exit 21
fi

OLD="$(
    pgrep -f \
    'experiments/16_benchmark_suite/run_benchmark_v3.py' \
    || true
)"

if [ -n "$OLD" ]; then
    echo "OLD_V3_PROCESS_STILL_RUNNING=True"
    echo "$OLD"
    echo "Not launching V3R1 concurrently."
    exit 22
fi

GPU_COUNT="$(
"$PY" - <<'PY'
import torch
print(
    torch.cuda.device_count()
    if torch.cuda.is_available()
    else 0
)
PY
)"

echo "CUDA_GPU_COUNT=$GPU_COUNT"

if [ "$GPU_COUNT" -lt 1 ]; then
    echo "NO_CUDA_GPU=True"
    exit 23
fi

if command -v nvidia-smi >/dev/null 2>&1; then
    echo "CURRENT_GPU_STATUS"
    nvidia-smi \
    --query-gpu=index,name,memory.used,memory.total,utilization.gpu \
    --format=csv,noheader \
    || true
fi

STAMP="$(
    date +%Y%m%d_%H%M%S
)"

PIDS_FILE="$LOGROOT/benchmark_v3r1_latest_pids.txt"
LOGS_FILE="$LOGROOT/benchmark_v3r1_latest_logs.txt"

: > "$PIDS_FILE"
: > "$LOGS_FILE"

CACHE_ROOT="$LOGROOT/benchmark_v3r1_pycache"

mkdir -p \
"$CACHE_ROOT/gpu0" \
"$CACHE_ROOT/gpu1"

if [ "$GPU_COUNT" -ge 2 ]; then

    LOG0="$LOGROOT/benchmark_v3r1_${STAMP}_gpu0_PAMAP2_DSADS.log"

    LOG1="$LOGROOT/benchmark_v3r1_${STAMP}_gpu1_UCI_MotionSense.log"

    nohup env \
    CUDA_VISIBLE_DEVICES=0 \
    PYTHONUNBUFFERED=1 \
    PYTHONPYCACHEPREFIX="$CACHE_ROOT/gpu0" \
    "$PY" -u "$RUNNER" \
    --phase all \
    --datasets PAMAP2 DSADS \
    </dev/null \
    >"$LOG0" \
    2>&1 &

    PID0=$!

    nohup env \
    CUDA_VISIBLE_DEVICES=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPYCACHEPREFIX="$CACHE_ROOT/gpu1" \
    "$PY" -u "$RUNNER" \
    --phase all \
    --datasets UCI_HAR MotionSense \
    </dev/null \
    >"$LOG1" \
    2>&1 &

    PID1=$!

    printf '%s\n' \
    "$PID0" \
    "$PID1" \
    > "$PIDS_FILE"

    printf '%s\n' \
    "$LOG0" \
    "$LOG1" \
    > "$LOGS_FILE"

    echo "BENCHMARK_V3R1_MODE=DUAL_GPU"
    echo "GPU0_PID=$PID0"
    echo "GPU0_LOG=$LOG0"
    echo "GPU1_PID=$PID1"
    echo "GPU1_LOG=$LOG1"

else

    LOG0="$LOGROOT/benchmark_v3r1_${STAMP}_gpu0_ALL.log"

    nohup env \
    CUDA_VISIBLE_DEVICES=0 \
    PYTHONUNBUFFERED=1 \
    PYTHONPYCACHEPREFIX="$CACHE_ROOT/gpu0" \
    "$PY" -u "$RUNNER" \
    --phase all \
    --datasets \
    UCI_HAR \
    PAMAP2 \
    DSADS \
    MotionSense \
    </dev/null \
    >"$LOG0" \
    2>&1 &

    PID0=$!

    printf '%s\n' \
    "$PID0" \
    > "$PIDS_FILE"

    printf '%s\n' \
    "$LOG0" \
    > "$LOGS_FILE"

    echo "BENCHMARK_V3R1_MODE=SINGLE_GPU"
    echo "GPU0_PID=$PID0"
    echo "GPU0_LOG=$LOG0"
fi

echo "PIDS_FILE=$PIDS_FILE"
echo "LOGS_FILE=$LOGS_FILE"
echo "BENCHMARK_V3R1_LAUNCHED=True"
