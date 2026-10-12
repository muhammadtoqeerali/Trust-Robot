# TRUST-ROBOT KIOS V15 exploratory LiDAR odometry integration

Status: **offline implementation and validation passed**.

## Engineering accomplishment

Connected the frozen Phase-2 scan-registration frontend to the
existing TRUST-ROBOT FixedCleanBackbone using its native
RelativePoseIncrement and PoseSE3 mathematical interfaces.

The frozen Phase-4 registration-diagnostic extractor is also
reused. Previously recorded V15 frames are read-only.

Clean pose chain: **6 poses**, five registration increments.

Frame-3-sparsified pose chain: **6 poses**, five increments.

Numeric environment:
`{'numpy': '1.26.4', 'python': '3.10.12', 'scipy': '1.13.1'}`.

Cross-environment diagnostic pairs differing numerically:
**0**.
This count is diagnostic and is not a performance score.

Two complete derivations were byte-compared to check
reproducibility under the selected environment.

## Frame and timing semantics

The chain begins at an **arbitrary identity odometry origin**.

Its body frame denotes the unverified synthetic LiDAR frame,
not a calibrated robot-base frame.

The increment timestamp integer is derived from Isaac Sim
simulation read-step time; it is not a physical firing,
exposure or sensor measurement timestamp.

The USD transform sequence is not used as independent
ground-truth input, and no reference association is performed.

## What is not implemented or claimed

The existing FixedCleanBackbone is a deterministic SE(3)
pose-composition kernel, **not a complete fixed-lag nonlinear
optimization backend**.

This milestone does not perform cross-modal factor fusion,
IMU preintegration, calibrated health weighting, probability
calibration, hard suppression or safety supervision.

LiDAR scan fitting diagnostics are not ATE/RPE.

The generic 16-emitter pilot scans are not qualified as
physically accurate moving scans or a specific commercial
LiDAR model.

No physical robot was contacted.

The frozen Phase-7 auxiliary consistency and Phase-8
factor-conditioning runtime authorization gates remain blocked.

## Provenance

Parent commit:
`988f5a64433bc2108f02d6df7dcb1655a0fb4739`

Implementation SHA-256:
`5ab5fa253ec387d4869e2e604368d48813f285c9a0cf3dd654972eb16f7188ee`

Test SHA-256:
`fc1b19550f20a863eb19f9d738dc3174049b7a9af0b8d3ee638a4daae7e60daa`

Derived manifest SHA-256:
`b1f04d865c65d59c8962f10b5f47501c9c17cfff3f34c360e19e765208d4e20f`

Large numerical outputs remain local and are excluded from Git.

## Reproduction

Use a compatible project-local NumPy and SciPy installation.

    PYTHONPATH=src python -B src/trust_robot/isaacsim_v15_odometry_chain.py RECORDING_DIR REGISTRATION_DIR experiments/isaacsim_v15/compact_evidence_v15.json NEW_OUTPUT_DIR

    PYTHONPATH=src python -B tests/trust_robot/test_isaacsim_v15_odometry_chain.py -v

## Next prerequisite

An observable synthetic motion dataset with documented frame
conventions, validated capture-time semantics and a separately
qualified reference source is needed before defensible
reference-based localization evaluation.

Empirical TRUST-ROBOT health-model training remains blocked
until admissible supervision exists.
