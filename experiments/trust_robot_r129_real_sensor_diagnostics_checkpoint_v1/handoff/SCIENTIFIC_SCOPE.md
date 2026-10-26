# TRUST-ROBOT R129-B3 — real-sensor diagnostic handoff

Source: Hilti-Oxford 2022, Exp14, SHA256-verified ROSbag.

R129-B1 extracted aggregate diagnostic statistics from 448 real
sensor messages, with 64 messages from each of five cameras, one IMU
and one LiDAR. The published report and extractor source are SHA-pinned.

R129-B2 independently replayed the same bounded content and reported:
seven matching message fingerprints, 33 reproduced feature families,
matching numerical aggregate statistics and six rejected tampered
reports. The B2 result is recorded from operator-posted terminal
output. A separately hash-pinned B2 replay program was not independently
archived with this package. Thus the B2 observation record is not a
standalone cryptographic proof of that replay.

The portable verifier checks the handoff files, source lineage,
aggregate report structure, scientific limits and tamper controls.
It cannot independently decode the real recording without the
original ROSbag, which remains on UNIVER.

No raw image, point cloud, individual IMU sample, per-message
timestamps, per-message feature vectors, ground truth or ROSbag data
is exported. The report contains aggregate statistics and
per-stream ordered fingerprints.

All features are descriptive engineering diagnostics, not measured
sensor-health labels or calibrated fault probabilities. Header/bag
timestamp equality does not prove physical synchronization.

No alternate-dataset partition, independent full-6DoF reference,
real localization factor, health-model training, ATE/RPE scoring or
robot safety qualification is authorized.

The original M2DGR 22/7/7 split and sealed confirmation_test are
unchanged. All eleven scientific admissibility gates remain CLOSED.
