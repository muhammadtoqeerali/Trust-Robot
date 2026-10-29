# R135-A16 — Simultaneous two-edge synthetic fault stress

Status: UNTRUSTED_SYNTHETIC_NUMERICAL_STRESS_ONLY.

## Objective

Assess numerical behavior of the frozen five-node,
15D Schur-marginalized estimator under two simultaneous
missing LiDAR relative-pose measurements.

## Experiment

The seven-edge graph has 21 distinct unordered edge pairs.

For each pair:

1. Remove both LiDAR factors.
2. Restore both with ideal synthetic camera factors.
3. Restore both with noisy synthetic camera factors.
4. Restore both with biased synthetic camera factors.

One LiDAR-only baseline is also executed.

Total: 85 distinct manufactured configurations.

## Fault structure

Both missing factors are removed from the same fixed
synthetic graph.

Restoration uses camera factors manufactured from
projected pixels, simulated metric depth and SVD motion
alignment. No LiDAR registration factors are copied.

Both camera factors use the same manufactured scene,
motion source and frozen noise model. They must NOT
be described as physically independent observations.

## Solver outcomes

An accepted configuration reports:

- factor source ledger and pose slot ownership;
- four accepted 15D estimator windows;
- three Schur eliminations;
- synthetic final position and state digest;
- summed numerical optimizer objective;
- final-position difference from the synthetic baseline.

If the existing solver explicitly reports
"Marginalized window solve failed at ...",
the configuration may be recorded as
NUMERICALLY_REJECTED.

An unexpected exception or a failed scientific
contract aborts implementation and publication.

A numerically accepted solve does not prove
physical observability, accuracy, fault tolerance
or real localization recovery.

## Strict scientific limitations

No recorded data or independent reference is used.

No sensor-health label, probability or classifier
inference is generated.

No factor weighting or covariance is modified.

No simultaneous independent camera/LiDAR factors
are introduced on the same edge.

No real sensor factors are admitted.

## M2DGR safeguards

The 22 TRAIN / 7 VALIDATION_CALIBRATION /
7 CONFIRMATION_TEST partition remains unchanged.

All 11 M2DGR scientific admission gates remain CLOSED.

No recorded M2DGR or Hilti ground truth is accessed.

## Next research direction

Use the stress-test evidence to identify whether the
current five-node fixture is too easy. Study stronger
controlled IMU/LiDAR failures and numerical support
without interpreting manufactured optimizer costs as
independent localization accuracy.
