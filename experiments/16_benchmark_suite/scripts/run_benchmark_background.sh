#!/bin/bash


PROJECT_ROOT=$(pwd)


LOG_DIR="results/logs"

mkdir -p "$LOG_DIR"



TIMESTAMP=$(date +"%Y%m%d_%H%M%S")


LOG_FILE="$LOG_DIR/benchmark_${TIMESTAMP}.log"



echo "STARTING BENCHMARK"
echo "LOG:"
echo "$LOG_FILE"



nohup python experiments/16_benchmark_suite/run_suite.py \
--dataset UCI_HAR \
> "$LOG_FILE" 2>&1 &



PID=$!


echo "PID=$PID"

echo "$PID" > "$LOG_DIR/latest.pid"


echo "BENCHMARK_STARTED=True"

