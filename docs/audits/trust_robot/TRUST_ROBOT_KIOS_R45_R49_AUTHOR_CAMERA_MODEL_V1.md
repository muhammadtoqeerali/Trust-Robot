# TRUST-ROBOT R45–R49 upstream calibration and camera-model audit

Checkpoint date: 2026-10-20.
Parent commit: `17536d0e9a03eb4f0b4adfb5056dc7ba63df9921`.
Integration branch: `kios-isaacsim-v15-integration`.
Archive: `experiments/trust_robot_r45_r49_author_camera_model_checkpoint_v1/`.

## Preserved sources and engineering results

R45 discovered four immutable official M2DGR repository source identifiers. R46 independently byte-validated three author files by Git SHA1 and independently verified their corresponding SHA256 hashes. The originally failing independent parser and SHA-pinned targeted repair remain preserved, along with three offline source-transfer receipts. No direct network fetch was made on KIOS.

The published camera intrinsics and distortion matched camera application YAML numerically for 640×480 data. Published intrinsic-matrix storage required transposition to form standard OpenCV K. The LiDAR application noise settings matched published HandsFree IMU parameters; the camera application's HandsFree IMU topic used noise values equal to 10× published Xsens noise. A camera/IMU translational parameter comparison showed 0.000241868 m discrepancy but does not certify coordinate-frame direction or physical calibration.

R47 independently verified image-dimension and topic compatibility with earlier frozen room_02 diagnostic evidence: compressed-image transport requires an adapter for the raw-image topic, and the camera and HandsFree IMU streams have distinct native frames.

R48 generated 64 synthetic camera rays. The independent OpenCV replay verified inverse/forward numerical consistency and limited parameter sensitivity. R49 independently replayed 64 synthetic rays and 256 synthetic half-pixel perturbations. Maximum numerical angular effects were approximately 0.630047 degrees when ignoring distortion, 37.055704 degrees for the wrong author matrix orientation, and 0.065641 degrees for half-pixel offsets. These are simulations, not observed calibration errors.

## Explicit restrictions

No original 15GB TRAIN recording was ingested in R45–R49, no confirmation_test trajectories were accessed, and no physical extrinsic/clock/mocap-reference qualification was achieved. The 22 TRAIN / 7 validation_calibration / 7 confirmation_test split remains frozen, with all eleven physical admission gates closed and zero approved real pose factors or health labels/training or ATE/RPE scoring.

## Next

R51: resolve author parameter applicability and physical measurement provenance, and audit any incoming reference/clock/extrinsic receipts independently before considering real sensor factors.
