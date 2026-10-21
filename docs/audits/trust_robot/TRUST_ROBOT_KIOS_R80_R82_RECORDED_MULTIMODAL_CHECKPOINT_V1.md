# TRUST-ROBOT R80–R82 recorded multimodal engineering checkpoint

Date: 2026-10-21. Parent: `aa4c06bdc2eac5cff7352157beef9ec534f2f455`. Publication workstation: KIOS.

## Implemented engineering

- R80: eight separated recorded `room_02` LiDAR transform diagnostics; rotation/inverse correctness; 13 regression tests.
- R81: 22 SHA-frozen TRAIN LiDAR odometry trajectories, 90,992 SE(3) increments, 91,014 scan identities; typed read-only adapter and 13 synthetic tests. Original frozen source on Verona, excluded from Git.
- R82: 2,816,957 camera/IMU feature records from previously frozen SE3, 62 source feature files, non-overlapping 256-record stream-local descriptive windows; 13 synthetic tests. Window JSONL kept on Verona, not Git.
- R83A/B: checksum-pinned nine-member Verona–Windows–KIOS transfer archive, eight R81/R82 source files plus a handoff manifest. R80 sources independently bound on KIOS.

## Scientific and privacy boundaries

TRAIN-only 22/7/7 split. No shared clock-domain inference, no real sensor factor admission, no health truth/model, no independent physical calibration, no GT scoring, no ATE/RPE. Sealed confirmation_test, original GT, raw ROSbags, individual LiDAR pose/time streams, SE3 feature records, and 62 derived R82 window files remain off Git. Eleven scientific gates remain CLOSED.

Checkpoint package: `experiments/trust_robot_r80_r82_recorded_multimodal_checkpoint_v1/`. Run its standalone verifier and the three archived regression suites for independent reproducibility.
