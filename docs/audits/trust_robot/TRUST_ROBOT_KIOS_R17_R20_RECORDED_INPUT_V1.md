# KIOS R17–R20: Authenticated recorded-input nonfactor readiness checkpoint

Date: 2026-10-19. Parent Git commit: `0dddf4eda57cd629db4c5ee63cdbf645b17fb31d`.
Archive: `experiments/trust_robot_r17_r20_recorded_input_checkpoint_v1/`.

## Input integrity and split

Original M2DGR `room_02.bag` SHA256: `ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1`; exact match with the immutable TRAIN manifest. The 15 GB-class recording is not included in Git. No validation-calibration or confirmation-test raw data were used for selection.

## R17 — ROS1 index integrity

15 topics and connections, 5182 chunks; 1113 camera compressed-image, 13858 camera IMU, 10426 HandsFree IMU, and 752 Velodyne messages (26149 across those four streams). Positive synthetic fixture and five negative malformed-index controls passed. An independent reader recomputed index counts. Bag timestamp fields were not used to prove physical capture time.

## R18 — bounded recorded decoding and repair

The original decoder failed on a real chunk containing ROS1 connection metadata (`0x07`) alongside message-data records (`0x02`). Original failed source was retained byte-for-byte. A narrowly scoped decoder and independent-verifier patch passed six malformed-connection negative controls and eight real serialized-message SHA256 checks. Two messages were selected from each of four streams, spanning four chunks. This is bounded decoding, not an exhaustive data audit or registration pipeline.

## R19 — existing frontend contracts

Six camera/IMU raw-observation adapter receipts conform to the repository's existing contract; two LiDAR observations match the existing frontend's layout requirements as *nonfactors*. All eight source-message bytes and contract links were independently checked. No camera odometry, LiDAR registration, IMU preintegration, or cross-modal alignment was executed.

## R20 — recorder readiness review

197 targeted existing frontend/sensor-admission regressions passed (two warnings reported). Six camera/IMU and two LiDAR provenance receipts were rechecked with an independent verifier. Decision: `RECORDED_OBSERVATION_PROVENANCE_ONLY`. Independent review passed. Source and report hashes are frozen in the archive's `checkpoint_manifest_v1.json` and can be verified without possessing the original large bag.

## Scientific gate

Real sensor factor execution DENIED; physical synchronization UNVERIFIED; physical capture-event semantics UNVERIFIED; extrinsic transformations UNVERIFIED; independent reference-to-estimator association UNVERIFIED; 6DoF localization scoring BLOCKED; health labels/training NONE; live simulator launch NOT AUTHORIZED. Prior S1–S10 checkpoints and M2DGR split remain immutable. No new estimator accuracy, covariance, independent GT, or sensor health claim is made.

Next: recorded single-modality frontend candidate development with explicit research gates, not scientifically authorized real fusion or evaluation.
