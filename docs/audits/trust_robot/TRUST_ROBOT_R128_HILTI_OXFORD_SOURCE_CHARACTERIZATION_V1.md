# R128-B11C — Hilti-Oxford 2022 real recorded-source evidence

**Evidence scope:** camera/LiDAR/IMU recording acquisition and bounded source
characterization, with independent SHA256 provenance, not real estimator
admission, calibration, ground-truth qualification or scored localization.

The pinned official Hilti revision `e62017f907007fdc5ab8c721842e4ae7359d7f49`
provided an Exp14 ROSbag of 6,260,771,085 bytes. UNIVER independently
verified its SHA256 `18eea013076b8263ababf4f36eb68d331564a0a493262b006dc0dddc2aa85b82`.
The ROSbag index contained eight connections (five cameras, IMU, LiDAR, and a
string topic), 45,082 messages. R128-B9 sampled 12 per sensor topic (84 total),
then B10 sampled 128 per sensor topic (896 total), with B9's prefix identical.
B10 examined 7,728 bag messages to collect the bounded sample and passed five
negative controls. All 896 sampled sensor header stamps matched bag stamps;
median camera/IMU/LiDAR intervals were 24.9973/2.505/99.997 ms. This is
not hardware synchronization proof or physical sensor-time identification.

The first B11 sanitizer imposed an invalid 16-structure-variant limit; the
LiDAR exhibited 122 unique point-cloud widths. R128-B11A-R1 preserved
all 128 individual LiDAR scan records only on UNIVER while exporting stable
metadata and aggregate width statistics. Failure lineage is included.
The SHA-pinned sanitized B11 handoff was independently validated on KIOS,
including a standalone verifier and scientific-status tamper controls.

**Unresolved:** measured physical camera/IMU/LiDAR time semantics; calibrated
extrinsics and uncertainty independent of author files; LiDAR scan timing;
independent 6DoF reference provenance (dense Hilti reference uses
LiDAR-inertial mapping); predeclared alternative dataset split. No ground truth
file was downloaded in this series. The original 22/7/7 M2DGR partition,
sealed confirmation_test and all 11 CLOSED gates remain untouched.

Package: `experiments/trust_robot_r128_hilti_oxford_2022_source_checkpoint_v1/`.
The actual 6.26-GB bag and per-message audit evidence remain off Git on UNIVER.
No health-model training, real factor admission, robot safety claims, physical
sync inference or ATE/RPE scoring is permitted by this checkpoint.
