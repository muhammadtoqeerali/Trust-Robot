# TRUST-ROBOT M2DGR sensor admission development V1

**Status:** offline recorded-source admissibility interface implemented.
This is not real-sensor localization or reference scoring.

## Implemented

- Frozen M2DGR source and scientific-evidence hash bindings.
- Frozen trajectory-disjoint train/validation/test split validation.
- Camera, LiDAR and IMU inventory admission.
- Exact existing SE3 camera/IMU feature-record contract reuse.
- Stream index, header-stamp and reader-provenance validation.
- Explicit missing-header and strict-header-reversal reporting.
- Independent within-stream feature-record hashing.
- Reference and cross-split feature-record rejection.
- Bounded, project-local, read-only feature JSONL inspection CLI.
- Fail-closed real-sensor factor-execution authorization.

This module does not generate camera relative-motion factors,
LiDAR odometry factors or synchronized inertial factors.

## Frozen M2DGR inventory

- Trajectories: 36
- Camera-containing trajectories:
  34
- IMU-containing trajectories:
  36
- LiDAR-containing trajectories:
  36
- Missing camera trajectories:
  street_010, street_09

These are source-manifest counts, not evidence of accessible
raw recordings or physical calibration.

## Scientific blockers preserved

- Camera physical capture timing remains unverified.
- LiDAR physical capture/firing-time semantics remain unresolved.
- Cross-sensor extrinsics are not independently qualified.
- Reference-to-estimator temporal association is unverified.
- No fixed offset or association tolerance is authorized.
- No interpolation or nearest-neighbor pose scoring is authorized.
- Current cross-modal fusion and estimator scoring are blocked.
- Frozen train/validation/test assignments remain unchanged.
- Existing Phase-7 and Phase-8 runtime authorization gates
  are not opened.
- No health labels or calibrated modality-health probabilities
  were manufactured.

The offline feature-admission API does not infer metric
6-DoF motion from camera low-level intensity summaries.

## Reproduction

    PYTHONPATH=src python -B tests/trust_robot/test_m2dgr_sensor_admission.py -v

For frozen source inventory:

    PYTHONPATH=src python -B scripts/trust_robot/run_m2dgr_sensor_admission_v1.py --repo .

If previously generated frozen SE3 feature JSONL files are
available within the dedicated project workspace, the CLI can
inspect a single train-only stream with --feature-jsonl,
--trajectory and --stream.

No full raw dataset download, ROS connection or physical robot
contact is required.

## Remaining integration work

- Bind qualified raw/front-end LiDAR motion and actual visual
  motion constraints to the estimator's factor interface.
- Establish physical time and coordinate-frame evidence.
- Replace analytic initial anchors and synthetic timestamps
  where independently justified measurements exist.
- Add real-data estimator availability and calibrated health
  supervision only after valid reference and label contracts.
- Evaluate controlled faults separately from attack models.

Do not report this source-admission milestone as a completed
three-modality localization benchmark.
