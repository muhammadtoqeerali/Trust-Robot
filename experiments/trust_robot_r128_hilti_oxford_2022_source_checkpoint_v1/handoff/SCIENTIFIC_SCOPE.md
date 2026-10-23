# TRUST-ROBOT R128-B11A-R1 — sanitized Hilti real-sensor handoff

The source is the SHA256-verified Hilti-Oxford 2022 Exp14 recording.
The first 128 messages from each of five cameras, one IMU and one
LiDAR were characterized in R128-B10 (896 total). All 896 sampled
header timestamps matched bag timestamps. Observed median rates
were approximately 40 Hz (cameras), 399.2 Hz (IMU), and 10 Hz (LiDAR).

Original B11A summary construction failed because its arbitrary limit
of 16 structure variants rejected changing LiDAR scan widths. R1
preserves the original evidence, exports only stable structural
profiles and aggregate LiDAR scan-width statistics, and records the
failure lineage. The 128 individual message records per topic remain
exclusively on the university workstation.

No raw ROSbag, GT trajectory, per-message timestamps, point data,
images or individual IMU measurements are included. Header/bag equality
is NOT proof of physical clock synchronization, capture-event mapping,
LiDAR scan-time semantics, or camera-IMU timeshift applicability.

No localization factors, trained health model, ATE/RPE scoring, or
independent full-6DoF reference have been qualified by this evidence.
The alternate dataset split is not frozen. The M2DGR split remains
22 TRAIN / 7 validation / 7 sealed confirmation_test, with all eleven
scientific gates CLOSED.
