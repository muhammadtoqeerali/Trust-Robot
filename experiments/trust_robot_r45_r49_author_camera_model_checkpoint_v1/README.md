# TRUST-ROBOT R45–R49: Author calibration and synthetic camera-model checkpoint

This archive preserves 39 source/test/evidence artifacts across R45–R49, including three offline source-transfer payloads. It also retains the original R46 failing verifier, its targeted parser repair, and all three author-published source files byte-authenticated to immutable upstream Git blob IDs.

- R45: four immutable M2DGR author-source candidates; 11 physical-evidence gates remained unfilled.
- R46: three offline-reconstructed Git-authenticated author files, numeric camera/extrinsic/IMU configuration comparison; original independent-parser failure and byte-pinned targeted repair.
- R47: 16 recorded 640×480 color frame dimensions; compressed image topic needs adapter for raw subscriber; HandsFree IMU distinguished from camera IMU native frame.
- R48: 64 synthetic camera rays with independent OpenCV project/unproject consistency and parameter sensitivity. No authentic image content reused.
- R49: 64 synthetic rays, 256 half-pixel perturbations, numerical model interpretation, distortion omission and radial monotonicity checks.

The original room_02.bag is not in the archive or GitHub. Its checksum and frozen TRAIN split are receipts, not embedded sensor data. The three small author calibration text files are external Git-authenticated reference texts and should not be confused with raw recording payloads or physical calibration certification.

**Scientific boundary:** No qualified physical camera intrinsics, complete camera/LiDAR/IMU extrinsics, physical capture-time alignment, independent mocap reference, trained health model, real 6DoF factors, ATE/RPE scoring, confirmation-test access or autonomous safety evidence is authorized. All R43 source receipts remain empty.

Run `python3 -B verify_checkpoint.py` to recheck all archived SHA256 pins and scientific restrictions from any working directory, without opening the raw bag.

Next: R51 source applicability/clock and actual physically traceable evidence intake; numerical model checks are not calibration approval.
