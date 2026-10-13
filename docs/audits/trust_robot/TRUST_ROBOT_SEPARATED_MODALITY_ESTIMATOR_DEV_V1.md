# TRUST-ROBOT separated modality estimator development V1

**Status:** synthetic nonlinear estimator integration validated.
Not physical camera/LiDAR/IMU fusion validation.

## Engineering advance

The new synthetic-only 15D fixed-lag estimator permits
independent camera and LiDAR relative-pose residual blocks
on the same graph edge.

The implementation preserves:

- Separate camera and LiDAR factor dictionaries.
- Separate residual blocks and synthetic numerical scales.
- Distinct source and measurement identities.
- Independent IMU, LiDAR and camera consumption ledgers.
- Source-aware history inside each Schur information prior.
- No double counting during marginalization.
- Jacobian information-support analysis.
- Numerical failure and missing-camera admission checks.
- Original published estimator implementation unchanged.

The previous temporary compatibility adapter remains intact
for comparison, but this new estimator does not remove a
LiDAR observation when an additional camera-style observation
is present on its edge.

## Development experiment

| Condition | Seed | Camera enabled | Camera factors | LiDAR factors | IMU factors | Solved windows |
|---|---:|---|---:|---:|---:|---:|
| clean | 13 | False | 0 | 7 | 4 | 4 |
| clean | 13 | True | 2 | 7 | 4 | 4 |
| clean | 31 | False | 0 | 7 | 4 | 4 |
| clean | 31 | True | 2 | 7 | 4 | 4 |
| clean | 71 | False | 0 | 7 | 4 | 4 |
| clean | 71 | True | 2 | 7 | 4 | 4 |
| lidar_dropout | 13 | False | 0 | 3 | 4 | 4 |
| lidar_dropout | 13 | True | 2 | 3 | 4 | 4 |
| lidar_dropout | 31 | False | 0 | 3 | 4 | 4 |
| lidar_dropout | 31 | True | 2 | 3 | 4 | 4 |
| lidar_dropout | 71 | False | 0 | 3 | 4 | 4 |
| lidar_dropout | 71 | True | 2 | 3 | 4 | 4 |

All 12 manufactured scenarios completed.

The existing 192-test baseline and the new 12-test suite
passed, totaling 204 tests.

## Scientific limitations

Camera relative poses were manufactured from synthetic
trajectory states with seeded perturbations.

No pixel correspondences, visual odometry tracking,
camera calibration, reprojection residual or optical-flow
motion estimate was implemented in this milestone.

LiDAR remains generated from analytic scan registration.
IMU factors use the existing analytic preintegration.
The initial anchor remains a synthetic assumption.

The camera and LiDAR residual scales are separately declared
development constants. They are not empirically calibrated
measurement covariances or runtime trust weights.

The two same-edge observations are tracked separately in
the factor graph. Their statistical independence is not
established merely by their different source labels.

The project does not yet have independent real-sensor
capture timing, verified complete extrinsics, or authorized
reference-to-estimator temporal association.

Real M2DGR factor execution and localization scoring
remain blocked. No source-attribution rule, health
probability, factor-conditioning weight or recovery/safety
decision is inferred.

Frozen Phase-7/8 scientific gates remain unchanged.

## Reproduction

    PYTHONPATH=src python -B tests/trust_robot/test_analytic_separated_modalities.py -v

The dedicated KIOS experiment folder retains the complete
scenario results, test logs and source SHA256 provenance.

## Next work

Implement and validate genuine image-derived camera motion
with explicit original capture-time and frame evidence.

Connect real LiDAR registration and IMU preintegration only
after physical synchronization and extrinsics are qualified.

Preserve source-specific measurement identity when eventually
connecting the validated frontend to this factor graph.

Do not authorize physical fusion or real-data accuracy
scoring from the present manufactured development experiment.
