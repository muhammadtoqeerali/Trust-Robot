# R128 — Hilti-Oxford 2022 Exp14 real-sensor source checkpoint

This is **source characterization only**, not scientific admission of a real sensor
factor, model training, physical timing calibration, or localization scoring.

- Original Hilti-Oxford 2022 revision: `e62017f907007fdc5ab8c721842e4ae7359d7f49`.
- Verified UNIVER recording: `exp14_basement_2.bag`, 6,260,771,085 bytes,
  SHA256 `18eea013076b8263ababf4f36eb68d331564a0a493262b006dc0dddc2aa85b82`.
- KIOS received a SHA-verified *sanitized* 10,009-byte eight-member handoff
  (`d8c68507ca63f093ec792eb77328b9382b7927117cf80085994dfe68fd207c25`).
- Handoff manifest SHA256 `3e2a701bbb685848b8237ab09001e07c82186d1d894abe70d12de5dd243c0ce7`.
- Independent KIOS intake receipt SHA256 `84dd82c77810eb244fc26aa9ce6a8e02c826a4531eaed1e4cb64df63cd6f1235`.

## Contents and reproduction

`handoff/` contains exactly eight small files: the scientific summary, lineage,
R128-B11A-R1 repair history, scope note, B9/B10 audit source, manifest and
standalone verifier. Run `python3 -I -B handoff/verify_handoff.py` from any
working directory. The B9/B10 scripts require the separately retained 6.26-GB
ROSbag and isolated Python `rosbags==0.11.9` reader on UNIVER; they are **not**
standalone runnable on KIOS. `kios_intake_receipt_v1.json` records receipt, not
new independent physical qualification.

First 128 messages per each of five cameras, one IMU, and one LiDAR were sampled
(896 total). The seven streams' header timestamps equaled bag timestamps for
these samples. Camera median intervals were ~24.9973 ms, IMU 2.505 ms, LiDAR
99.997 ms. 122 distinct LiDAR point-count widths were observed; these are
sensor-record metadata, not corruption evidence. These findings are bounded
descriptive observations and **do not verify physical synchronization**.

No raw image/point/IMU messages, per-message timestamps, absolute local dataset
paths, reference ground truth, or binary archive are included here. No dataset
partition is frozen for Hilti. Its dense LiDAR–inertial reference is not an
independent full-6DoF reference for LiDAR+IMU evaluation. Scored ATE/RPE,
health-model training and real localization factors remain unauthorized.

Original M2DGR split 22/7/7 remains unchanged; its confirmation_test is sealed
and **all 11 scientific gates are CLOSED**.

Audit: `docs/audits/trust_robot/TRUST_ROBOT_R128_HILTI_OXFORD_SOURCE_CHARACTERIZATION_V1.md`.
