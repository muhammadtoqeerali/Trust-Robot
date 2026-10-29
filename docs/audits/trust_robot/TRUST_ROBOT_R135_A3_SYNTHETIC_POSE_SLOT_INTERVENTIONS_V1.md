# R135-A3: Synthetic pose-slot intervention diagnostics

Status: **development-only synthetic graph diagnostic**.

## Objective

Verify the existing multimodal factor adapter under
deterministic synthetic measurement-availability changes.

This work does not implement a new estimator or health model.

## Four analytic scenarios

1. Baseline: three synthetic LiDAR pose slots.
2. LiDAR edge removed: one slot is missing.
3. Camera substitution: a manufactured camera relative-pose
   packet replaces one synthetic LiDAR factor.
4. Camera on removed-LiDAR edge: the manufactured camera
   packet occupies a previously missing graph slot.

The fourth scenario demonstrates graph assembly only.
It does not demonstrate successful localization recovery.

The numeric poses are internal manufactured fixtures,
not observations, fitted calibration or measurements
from a real or simulated physics sensor.

## Existing architecture reused

- `clean_backbone.PoseSE3`
- `multimodal_factor_interface.SyntheticPoseFactor`
- `multimodal_factor_interface.assemble_synthetic_pose_slot`

The existing backend has a single relative-pose factor
dictionary historically named `lidar`.

Same-edge camera substitution does not produce two
independent factors. It provides no distinct camera
noise model or independent modality weighting.

## Provenance and denial rules

The intervention runner accepts only one of four fixed
scenario identifiers. It cannot accept external packets,
sensor records, health labels, probabilities or weights.

The existing packet constructor rejects a non-analytic
origin and invalid source identity. The assembly adapter
rejects duplicate camera measurements.

The output contains descriptive graph-ledger metadata only.

No factor conditioning, health inference, classifier
training, metric pose scoring, posterior covariance or
real recorded factor execution is authorized.

This test is not an RQ1 or RQ2 experimental result.
No physical fault, calibrated degradation severity or
causal robustness claim is established.

## Scientific boundaries

- All 11 M2DGR scientific gates remain CLOSED.
- The frozen 22/7/7 M2DGR partition is unchanged.
- No held-out or confirmation data is accessed.
- No Hilti, M2DGR or other recorded sensor data is read.
- No physical camera/IMU calibration assumption is added.
- No health probability or health label is produced.
- No numerical factor weight is selected.
- No 15D estimator pose solve is performed.

## Next step

Review the new analytic graph tests and existing contract
regressions. Commit only after checking their exact source
hashes and the three-file Git change scope.

A later development phase may test synthetic-only estimator
behavior, while preserving all recorded-data and health
authorization boundaries.
