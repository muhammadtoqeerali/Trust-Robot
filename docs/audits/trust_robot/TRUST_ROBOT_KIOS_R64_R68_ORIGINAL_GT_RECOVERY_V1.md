# TRUST-ROBOT R64–R68 original GT recovery checkpoint

Date: 2026-10-21. Parent Git SHA `f3373e2d2c12a290661e03e0f6e59f66cdead4f9`, branch `kios-isaacsim-v15-integration`.

Original M2DGR dataset: Verona
`/mnt/hdd16T/ToqeerHomeBackup/toqeer/datasets/TRUST_ROBOT/M2DGR/`.
Original TRAIN GT recovered and preserved privately on KIOS, 504403 bytes,
SHA256 `79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d` (project historical evidence, not author-signed).
The raw `room_02.txt` and ROS bags are NOT in the Git archive.

R65 audited 3831 eight-column rows; R66 verified 90 structurally invalid
rotations in 61 runs and 3741 structurally valid rotations; R67 reproduced
the historical Phase-2 quality artifact exactly, SHA256 `8b27f25c02d04e838a88eb62980b1f2e94d0e1ed13defd0c6fa0f0b07c6bed49`.
R68 validated the remaining physical evidence gaps.

The checkpoint `experiments/trust_robot_r64_r68_original_gt_recovery_checkpoint_v1/` contains 22 SHA-pinned original off-Git code/report
files, a manifest, README, and standalone verifier. Independent source-byte
receipt SHA256: `73cb87c7cf349f1b11afda29b38fb215ce51431ffae7997a595aef4b936babe1` (off Git). Tamper test receipt SHA256: `2ba19ca0e4396b3665ccb461c4a5341bcd9ca6021b5f2ed558053fd53fd5a38f`
(off Git): positive replay passed, five negative cases rejected.

The 11 R43 physical/scientific gates are CLOSED and the five R53 timing
receipts remain unfilled. GT access is resolved, but physical mocap-body
origin, mocap-to-LiDAR transform, clock/timebase mapping, and cross-sensor
calibration are NOT validated. No real metric pose factors, health training,
ATE/RPE scoring, raw bag opening or confirmation_test access was authorized.
Original R43/R53 and R61 historical records are unchanged. Author request
has been corrected but NOT SENT.
