# R135-A18 — Joint manufactured IMU corruption / LiDAR dropout

Status: UNTRUSTED_SYNTHETIC_JOINT_SENSOR_STRESS_ONLY.

## Research motivation

R135-A17 showed that all 128 LiDAR-dropout patterns
were numerically accepted, including complete LiDAR
loss. Seventy-eight accepted configurations lacked
current LiDAR support in one or more windows.

We now examine whether the estimator's numerical
behavior changes when its manufactured IMU readings
are also corrupted.

## Controlled conditions

IMU conditions:
- clean;
- accel_bias.

The pre-existing analytic inertial fixture injects
the fixed specific-force offset [0.35, -0.10, 0.20]
m/s^2 into sensor samples 3, 4 and 5.

All other IMU sample indices remain unchanged.
LiDAR scans and the manufactured motion fixture
remain identical across IMU modes.

LiDAR dropout:
- all 128 subsets of seven relative-pose factors.

Total: 2 x 128 = 256 unique configurations.

No camera factor is introduced in this experiment.

## Audited outputs

For every configuration:
- solver accepted/rejected status;
- numeric support availability for each accepted window;
- current LiDAR measurement availability;
- factor counts and consumption consistency;
- synthetic solver state digest;
- summed optimizer objective;
- baseline-relative final position diagnostics.

Two different baseline-relative deltas are reported:
- relative to the full-LiDAR baseline for the same IMU mode;
- relative to the clean-IMU full-LiDAR baseline.

Neither delta measures true localization accuracy.

The manufactured reference trajectory is not used for
estimation, scoring, factor selection or calibration.

## Limitations

The fault mode is a fixed synthetic accelerometer
perturbation, not a measured physical IMU fault.

Numeric rank is not physical observability.
An accepted solver output is not proof of reliable
localization or sensor redundancy.

No trained health model or probability is used.
No factor information weights are changed.
No recorded sensor measurement or ground truth is read.
No confirmation-test sequence is accessed.

The M2DGR split remains frozen at
22 TRAIN / 7 VALIDATION_CALIBRATION /
7 CONFIRMATION_TEST.

All 11 M2DGR scientific admission gates remain CLOSED.

## Next scientific work

Investigate whether the support audit, numerical
residuals and estimator outputs expose meaningful
failure conditions under multiple manufactured fault
types and longer trajectories.

Do not promote numerical optimization success into
claims of physical localization accuracy or recovery.
