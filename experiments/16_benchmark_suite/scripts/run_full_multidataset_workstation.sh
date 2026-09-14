
#!/bin/bash

PROJECT_ROOT=$(pwd)

LOG_DIR="results/logs"

mkdir -p "$LOG_DIR"


TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

LOG_FILE="$LOG_DIR/full_multidataset_${TIMESTAMP}.log"


echo "================================"
echo "STARTING FULL MULTIDATASET BENCHMARK"
echo "LOG:"
echo "$LOG_FILE"
echo "================================"


nohup bash -c "

cd $PROJECT_ROOT

PYTHONPYCACHEPREFIX=/tmp/my_pycache \
/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/protechto311/bin/python \
experiments/16_benchmark_suite/run_suite.py \
--dataset UCI_HAR

PYTHONPYCACHEPREFIX=/tmp/my_pycache \
/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/protechto311/bin/python \
experiments/16_benchmark_suite/run_suite.py \
--dataset PAMAP2

" > "$LOG_FILE" 2>&1 &


PID=$!


echo "$PID" > "$LOG_DIR/full_multidataset.pid"


echo ""
echo "BENCHMARK_STARTED=True"
echo "PID=$PID"

