# TRUST-ROBOT Phase-5 Camera / IMU TRAIN Ingestion V1

Status: runner implemented locally; full real-data TRAIN execution not yet
started by this implementation step.

## Frozen execution population

The runner contains the exact 22 frozen TRAIN trajectories and opens only
their corresponding M2DGR bag files.

Validation and confirmation-test bags are not authorized.

## Selected raw observation streams

Only these streams are read:

- `/camera/color/image_raw/compressed`
- `/camera/imu`
- `/handsfree/imu`

No reference, ground-truth, GNSS, pose, odometry or TF stream is read.

## Evidence representation

Every selected serialized observation passes through the already implemented
Phase-5 raw-observation receipt contract.

Per-message raw payloads and full per-message receipts are not written to the
evidence directory. Instead, each trajectory/stream records deterministic
aggregate receipt digests, message counts, serialized byte counts, and directly
observed first/last transport/header timestamps.

A missing stream remains explicitly absent; it is not fabricated.

## Scientific boundary

No camera or IMU diagnostic feature contract is selected.

No feature extraction, normalization, health labeling, health-probability
prediction, thresholding or classifier training occurs.

Bag record time remains transport/container time only. Header timestamps do not
establish physical capture semantics or synchronization.

No reference association, ATE, RPE or final scoring is authorized.

## Artifact hashes

- config: `4a1794c81528bcd04165e4da52b60e10b5140a0a276452aa2cf269a4d66c3b9b`
- module: `9d5e75a3122be841cc9e4dfd952e4c97d92769fd2a9ab4e81bd93c213f5681bd`
- runner: `10c6ecd8d89eb21ae3aa48a4b500ce241ae2ca5621f8de0f48cb84746f454f9d`
- test: `e49fb96f679cc93eefc40446b71656083aea2c37b484d0eb04077c13d2e2955e`
