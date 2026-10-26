# R129 — Hilti-Oxford Exp14 real-payload descriptive feature checkpoint

**Checkpoint scope:** reproducible source-pinned camera, IMU and LiDAR payload-level *descriptive diagnostic* statistics. This is not health labelling, estimator operation, physical synchronization proof or localization performance scoring.

## B1 reproducible extraction

On UNIVER, R129-A-R1 decoded 56 payloads (8 per stream) to establish feature feasibility. R129-B1 then decoded the first 64 messages per each of seven sensor topics: five 720 × 540 mono8 cameras, an IMU and a Pandar LiDAR. The bounded reader examined 3,831 messages and deserialized 284,093,312 bytes. Per-topic ordered SHA256 fingerprints and aggregate-only feature statistics are retained; individual image, point, IMU and timestamp records remain off Git. The B1 report and executable extractor are independently SHA256-pinned, with six synthetic and three report-negative controls passing.

## B2 independent replay caveat

A separate read-only B2 program replayed the same 448 messages from the source bag on UNIVER. Terminal output reported seven matching fingerprints, 33 matching diagnostic feature families, matching numeric aggregate statistics and six rejected tamper cases. The **B2 independent program and full signed transcript are not included**; the B3 package includes only an operator-result record. The witness is explicitly not a cryptographically sealed proof of an independent rerun. The B3 portable verifier validates only what the archive contains, not a new real sensor replay.

## Transfer, science and remaining qualification

The 11,769-byte seven-file sanitized B3 archive had SHA256 `817c57bf8d1f193153f8bd0167e5ef6df35baa0327db9cc4b789c2a52a0de588`. KIOS B4C rechecked all six immutable payload hashes, the B1 report, receipt lineage and portable verifier; its receipt SHA256 is `8f6e063e3d53ac8f9f7477b167b91349d825d267ab0c316c79211905dfec62d7`. Git receives seven sanitized files, this audit, the README and copied receipt; original archive bytes and source ROSbag remain off Git.

Statistical features have **no healthy/degraded/unusable ground-truth labels**, validated thresholds, calibration or independently evidenced physical time semantics. The dense Hilti LiDAR-inertial reference is not an independent full-6DoF reference for LiDAR+IMU evaluation. No physical sensor health probabilities, trained health head, ATE/RPE, real localization factors or robot safety claims can be inferred or authorized. Original M2DGR 22/7/7 frozen partition and sealed confirmation_test remain untouched. All 11 scientific admissibility gates are CLOSED.

Source code and exact data identifiers: `experiments/trust_robot_r129_real_sensor_diagnostics_checkpoint_v1/`.
