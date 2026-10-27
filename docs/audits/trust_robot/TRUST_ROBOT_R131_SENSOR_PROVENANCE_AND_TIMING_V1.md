# R131 — Hilti-Oxford 2022 sensor provenance and timing review

Status: documentation-only scientific review. No real estimator admission or localization-scoring authorization.

## Scope and evidence limits

R131 examines original Hilti-Oxford 2022 Exp14 sensor messages, the publisher's calibration resources, and pinned publisher frame-model documentation. Calibration statements are publisher-provided; numerical agreement between publisher files does not independently verify installed hardware or capture-specific applicability. Later publisher descriptions are not assumed equivalent to the original capture.

## Supported findings

- Six original publisher calibration resources were integrity-checked off Git. Five camera-to-IMU calibration declarations were numerically consistent with the publisher's Phasma 20220322 model under the explicitly tested inverse-transform convention. The Alphasense default model is a distinct calibration variant; stereo-chain closure also passed diagnostic checks.
- The publisher's challenge reference describes an installed IMU reference frame, while its Phasma model defines a `base` frame connected to `alphasense_imu` by a fixed non-identity rotation. These frame coordinates must not be silently identified.
- The original recording exposes five camera streams, IMU, and LiDAR. In bounded early, middle, and late samples, camera timestamps agreed exactly across the five streams; sampled camera and IMU periods were stable. Bag-record timestamps matched header timestamps for inspected messages, which does not establish capture-to-recording latency.
- Bounded LiDAR samples contained distinct per-point timestamps. Their numerical ranges could be bracketed by sampled IMU times, but this is not verified physical clock synchronization or authorization for motion compensation.
- Direct ROS1 bag index inspection confirmed the seven sensor connection records lack `callerid` and `latching` metadata. Consequently those records do not establish capture-time publisher process identity.

## Evidence tiers

R131-A9 contains a SHA-sealed off-Git calibration-consistency checkpoint and independent R131-A10-R1 integrity validation. R131-A12-R1 checked pinned publisher frame-model sources. R131-A14 through A18 were run on UNIVER with operator-reported terminal results; R131-A19 is an integrity-checked synthesis of those results, not an independent replay of every measurement. Source data, detailed measurements, calibration arrays and original reports remain off Git.

## Unresolved prerequisites and prohibitions

- Identity of the recorded `imu_sensor_frame` with the calibration/URDF IMU frame, camera optical frame correspondence, and LiDAR frame applicability are not independently established.
- Capture-specific calibration-version assignment, physical extrinsic accuracy, timestamp semantics, PTP settings and cross-modal clock offset remain unverified.
- No ground-truth payload was used in these R131 audits. No real pose factors, health supervision, deskew, ATE/RPE evaluation, robot safety actions or factor admission were authorized.
- Frozen M2DGR TRAIN/validation_calibration/confirmation_test split remains 22/7/7; all eleven scientific gates remain CLOSED.

## Redistribution and references

This original narrative includes no raw ROS bag, publisher YAML content, numerical calibration matrices, detailed sensor measurements, original ground-truth payload or restricted B5 handoff. It does not grant permission to publish any underlying source artifacts.

Hilti-Research, Hilti-Oxford 2022 dataset: https://huggingface.co/datasets/Hilti-Research/hilti-slam-challenge-2022
Dataset license: CC BY-NC-SA 3.0, https://creativecommons.org/licenses/by-nc-sa/3.0/
Research citation: https://doi.org/10.1109/LRA.2022.3226077
Publisher frame model: https://github.com/Hilti-Research/phasma_description

Publication requires a separate reviewed KIOS Git operation with explicit user authorization. No such authorization is granted by this draft.
