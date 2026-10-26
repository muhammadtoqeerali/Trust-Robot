# R129 — Hilti-Oxford Exp14 real-sensor descriptive diagnostics

**Scope:** SHA256-pinned, bounded payload-level feature characterization only. This checkpoint does not certify sensor health, establish fault probabilities, or authorize real estimator factors or ATE/RPE scoring.

## Provenance and contents

- Original source: Hilti-Oxford 2022 Exp14 ROSbag, 6,260,771,085 bytes, SHA256 `18eea013076b8263ababf4f36eb68d331564a0a493262b006dc0dddc2aa85b82` (original remains off Git on UNIVER).
- Prior R128 sanitized handoff manifest SHA256 `3e2a701bbb685848b8237ab09001e07c82186d1d894abe70d12de5dd243c0ce7`.
- B1: first 64 messages from each of five mono8 cameras, one IMU and one LiDAR (448 total), scanning 3,831 messages and decoding 284,093,312 raw bytes. Six synthetic negative controls and three report-tampering controls passed.
- Original B1 aggregate report SHA256 `acdc86114f31e52990a14b74e0787db1fa2d1887dbbd9becd869c02596c838cb` and B1 manifest SHA256 `1aa2789b33b99f94bfd5f7d494c33f27db2ccf00d9578ae39e6e61220d53ac5d`.
- B2: separate independent real-data replay returned seven identical stream message fingerprints, 33 matching feature families and six negative tamper rejections. **Only the operator's posted result was retained in this archive**: the separately executed B2 replay program was not archived or signed. Do not treat the B2 witness as independently reproducible from this package.
- B3: 11,769-byte seven-member sanitized handoff; SHA256 `817c57bf8d1f193153f8bd0167e5ef6df35baa0327db9cc4b789c2a52a0de588`, manifest SHA256 `cceed1e6f68aee374d2bafbdc7e5eb0eccdc7d074adbbe19b32b7efba690a784`.
- KIOS off-Git B4C intake receipt SHA256 `8f6e063e3d53ac8f9f7477b167b91349d825d267ab0c316c79211905dfec62d7`.

The `handoff/` folder reproduces **exactly seven** B3 members: extractor source, B1 aggregate report, B1 manifest, B2 operator outcome record, scientific scope note, handoff manifest and portable verifier. Run `python3 -I -B handoff/verify_handoff.py` to validate self-contained provenance, schema, scope and tamper controls. Recomputing real features requires the separate original ROSbag and pinned `rosbags==0.11.9`, `numpy==2.5.4` environment on UNIVER; neither is in this Git package. The verifier cannot replay the B2 script.

Camera descriptors: 8-pixel-strided sample intensity mean/std, zero/max fraction and spatial gradients. IMU descriptors: motion norm and consecutive-sample deltas. LiDAR descriptors: point count, finite XYZ fraction and finite-point range median/p95. These measurements are unlabelled, uncalibrated descriptive features, not health classifications.

No raw images/points/IMU samples, per-message timestamps, sensor payloads, ground-truth trajectories, or 6.26-GB bag were committed. Timestamp equality is not independently proven physical synchronization. Independent full-6DoF reference, alternative dataset partition, physical calibration, real factors, trained health model and ATE/RPE remain unqualified. M2DGR 22 TRAIN / 7 validation_calibration / 7 sealed confirmation_test stays frozen with all 11 scientific gates CLOSED.

Scientific audit: `docs/audits/trust_robot/TRUST_ROBOT_R129_REAL_SENSOR_DIAGNOSTICS_V1.md`.
