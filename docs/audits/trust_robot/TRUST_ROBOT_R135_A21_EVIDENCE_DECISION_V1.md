# R135-A21 — Synthetic evidence consolidation and scientific decision

Status: SYNTHETIC_ONLY_NO_SCIENTIFIC_ADMISSION.

## Scope

R135-A17, A18, A19 and A20 are consolidated under
a single executable, deterministic evidence review.

The study inventory contains:
- A17: 128 five-node LiDAR-dropout configurations;
- A18: 256 five-node joint IMU-bias/dropout configurations;
- A19: 15 twelve-node IMU fault/outage configurations;
- A20: 20 twelve-node single/combined IMU fault configurations.

The total is 419 study configurations. These are not
419 independent trials. Several cases are intentionally
repeated across versions and checked for parity.

## Established engineering evidence

1. The published 15D Schur-marginalized estimator executes
   manufactured IMU and relative-pose factors.

2. Its fixed-window factor accounting and provenance
   controls pass targeted regression testing.

3. A17 showed 128/128 numerically accepted LiDAR-dropout
   patterns. Seventy-eight accepted configurations lacked
   current LiDAR in at least one window.

4. A18 combined a fixed accelerometer fault with all
   128 dropout patterns. Both IMU conditions were
   accepted, with numerical output differences.

5. A19 extended the analysis to twelve nodes and
   longer manufactured LiDAR outages, including
   complete LiDAR absence.

6. A20 combined accelerometer and gyroscope corruption.
   Nonzero manufactured nonlinear interaction was
   observed in the five tested outage schedules.

7. Cross-study parity is required for all 128 shared
   clean five-node configurations and 15 shared
   long-horizon single-fault configurations.

## Critical interpretation

Numerical solver acceptance does not demonstrate
sensor-supported or physically accurate localization.

A solution with zero active LiDAR factors does not
provide independent evidence of environmental
localization recovery.

Changes from a synthetic clean estimator baseline
are not independently scored localization errors.

Manufactured bias magnitudes and residual scales
are not physically calibrated health or failure models.

The interaction norm between simultaneous IMU faults
is an estimator-output diagnostic, not a failure
probability, trust estimate, accuracy score or
physical robustness metric.

## Scientific admission decision

The following remain BLOCKED:
- real sensor factor execution;
- physical localization accuracy claims;
- physical failure recovery claims;
- independently weighted same-edge camera/LiDAR fusion;
- health probability inference and labeling;
- learned health-conditioned factor weighting;
- recorded independent GT scoring;
- confirmation-test access.

No new research phase may silently reinterpret the
synthetic findings as authorization for these operations.

## Next evidence requirements

Priority evidence categories:
1. Independent timing and coordinate-frame verification.
2. Camera/LiDAR metric calibration and measurement provenance.
3. Defensible sensor-health definitions and supervision.
4. Factor information and uncertainty-model validation.
5. Stronger cross-scene synthetic robustness testing.
6. Admission-gated study of recorded datasets.

## Protected data and workstations

KIOS remains responsible for implementation, testing,
committing and pushing verified changes.

UNIVER contains the M2DGR dataset and is governed by
the established read-only dataset restrictions.

The frozen M2DGR split remains:
22 TRAIN / 7 VALIDATION_CALIBRATION /
7 CONFIRMATION_TEST.

All 11 M2DGR admission gates remain CLOSED.
No recorded M2DGR/Hilti data or recorded ground truth
is used in this evidence review.

## Publication decision

Publish this evidence synthesis as a software and
scientific-accountability checkpoint only.

No physical localization, real sensor fusion, health
inference, factor weighting, dataset admission or
confirmation-test permission is granted.
