# TRUST-ROBOT KIOS R70–R74 source admissibility checkpoint

Date: 2026-10-21.
Parent Git SHA: `6873da42fda57f23a46c0ecb2c788489802faa8c`.

R70 Verona discovery identified 91 candidate metadata files (not 91 qualified
calibration receipts). R71A SHA-checked original author calibration, hardware
description and commit provenance. R72 verified 15 LiDAR-extrinsic headings
and zero explicit mocap-calibration terms; the author description gives Vicon
Vero 2.2 nominal 50 Hz, while historical GT median interval gives roughly
50.057 Hz. This is not clock synchronization evidence. R73 securely transferred
three private Verona source reports to KIOS and verified their hashes. R74
independently compared report lineage with the earlier exact Phase-2 quality
artifact, passed eight in-memory negative controls, and prepared sanitized
publication outputs.

This checkpoint includes six SHA-pinned R74 sources/results, its manifest,
README and standalone verifier. The private R70/R71A/R72 reports, R73 receipt,
original 504403-byte GT and all ROS bags are NOT committed. Their SHA-256
identifiers are recorded in the checkpoint manifest. No private source paths,
source excerpts or raw GT data are published. Historical evidence files remain
unchanged.

Remaining blockers: tracked mocap body/marker-set origin; independently
validated mocap-body-to-LiDAR SE(3); reference capture timestamp event, epoch
and export semantics; clock-domain conversion and uncertainty; prospectively
specified quaternion anomaly handling. All 11 scientific gates CLOSED,
confirmation_test sealed, and no real pose factors, health training or ATE/RPE.

Verification:
`python3 experiments/trust_robot_r70_r74_scientific_admissibility_checkpoint_v1/verify_checkpoint.py verify experiments/trust_robot_r70_r74_scientific_admissibility_checkpoint_v1`.
