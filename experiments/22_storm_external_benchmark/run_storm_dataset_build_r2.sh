#!/usr/bin/env bash
set -euo pipefail

cd "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability"

echo "STORM_EXTERNAL_DATASET_R2_WORKER_START=True"
echo "TIME=$(date --iso-8601=seconds)"
echo "UPSTREAM_COMMIT=507dc30c0cab936f1a04f5cb665e9731c962f6b3"
echo "MIN_PURITY=0.8125"
echo "MAX_OTHER_RATIO=1.0"

"/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/protechto311/bin/python" -u "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability/external_references/storm_2026_upstream/utils/create_dataset.py" --out-root "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability/results/storm_external_r2/data" --datasets "uci,motionsense,pamap2" --fs 50.0 --win-len 1.28 --win-stride 0.64 --train-frac 0.70 --val-frac 0.15 --seed 42 --min-purity 0.8125 --max-per-class 0 --max-other-ratio 1.0

echo
echo "STORM_EXTERNAL_R2_DATASET_BUILD_FINISHED=True"

"/mnt/hdd16T/ToqeerHomeBackup/miniforge3/envs/protechto311/bin/python" -u "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability/experiments/22_storm_external_benchmark/audit_storm_dataset_r2.py"

touch "/mnt/hdd16T/ToqeerHomeBackup/toqeer/IMU_Reliability/results/storm_external_r2/COMPLETE"

echo
echo "STORM_EXTERNAL_DATASET_R2_WORKER_COMPLETE=True"
