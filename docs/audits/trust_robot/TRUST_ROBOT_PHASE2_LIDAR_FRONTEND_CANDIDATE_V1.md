# TRUST-ROBOT Phase-2 LiDAR Frontend Candidate V1

## Selection basis

The candidate frontend is selected from the TRAIN-only structural preflight,
not from estimator performance.

Across all 22 frozen TRAIN trajectories:

- `/velodyne_points` exists on 22/22 trajectories;
- the message type is `sensor_msgs/msg/PointCloud2`;
- `frame_id` is `velodyne` on 22/22 trajectories;
- the field names are `x,y,z,intensity,ring,time`;
- NumPy and SciPy spatial KD-tree support are available.

RGB-D is not selected because depth-image coverage is 0/22 in this preflight.

The LiDAR trajectory remains in the Velodyne frame. No unverified
LiDAR-to-base transform is introduced.

## Registration candidate

The candidate performs deterministic consecutive-scan registration:

- target = previous scan;
- source = current scan;
- initialization = identity;
- all finite points are used;
- no voxel downsampling;
- no correspondence-distance threshold;
- no outlier rejection;
- no keyframe rule;
- no numeric convergence tolerance;
- no maximum-iteration tuning parameter;
- nearest neighbors are computed with one worker;
- rigid fitting uses SVD/Kabsch;
- convergence occurs only when the exact nearest-neighbor assignment is
  unchanged;
- a repeated non-consecutive assignment state raises an error.

The resulting transform is:

`previous_lidar_T_current_lidar`

which directly matches the clean-backbone convention:

`prev_body_T_current_body`

when the backbone body frame is `velodyne`.

## Timing limitation

PointCloud2 header timestamps are used for ordering and state timestamps.

This does **not** claim that the header stamp is the physical scan center,
start, or end time.

The per-point `time` field is not used and no deskew is performed in this
candidate.

The existing LiDAR whole-scan temporal-reference ambiguity therefore remains
explicitly unresolved.

## Scientific scope

No reference trajectory is used.

No confirmation-test bag is opened.

No association to ground truth, alignment, ATE, RPE, or estimator scoring is
performed.

This candidate does not yet satisfy Phase-2 exit evidence.

A real two-scan TRAIN smoke test is only an implementation/mechanical check,
not a performance evaluation.
