# M2DGR Phase 3C Camera/IMU Synchronization Evidence

Date: 2026-09-17

Status: completed camera-image-to-D435i-IMU characterization checkpoint;
physical capture synchronization remains unverified.

## Purpose

Phase 3C asks whether the released M2DGR D435i color images and D435i IMU
provide independent evidence sufficient to justify a physical capture-time
relationship.

The objective is not to force a camera-to-IMU time offset.

The objective is to distinguish:

- released ROS header coordinates;
- united-IMU construction evidence;
- visual/inertial physical-content consistency;
- fixed-lag diagnostics;
- physical image-exposure timing;
- synchronization verification.

## Released camera-topic evidence

All 36 bags were inspected at the connection-metadata level.

For the released camera data:

- `/camera/imu` is present on 34/36 trajectories;
- `/camera/color/image_raw/compressed` is present on 34/36 trajectories;
- `street_09` and `street_010` contain neither audited camera stream;
- RealSense metadata topics are absent;
- raw camera gyroscope topics are absent;
- raw camera accelerometer topics are absent;
- camera-info topics are absent.

Therefore the released bag topics do not independently identify the exact
RealSense driver revision, runtime configuration, raw motion streams, or the
physical camera event represented by the final ROS image header.

## United D435i IMU characterization

A predeclared pilot used:

- `gate_01`
- `hall_01`
- `room_01`

The `/camera/imu` stream has approximately 200 Hz header cadence.

Consecutive acceleration vectors did not repeat in any of the three pilot
trajectories.

Observed acceleration-repeat fraction:

- `gate_01`: 0
- `hall_01`: 0
- `room_01`: 0

This strongly argues against a simple held-last-acceleration / copy-style
fingerprint in the released united IMU stream.

It does not uniquely identify the exact RealSense united-IMU implementation.

A subsequent acceleration-affine pilot was retained as diagnostic evidence but
is not used to reject linear interpolation because native accelerometer and
gyro rates can make consecutive 200 Hz united samples cross different native
acceleration intervals.

Exact driver configuration remains unresolved.

## Frozen visual/gyro zero-lag pilot

A visual relative-rotation method was frozen before any lag search.

The method used:

- released D435i color images;
- the author-published D435i camera model;
- pyramidal Lucas-Kanade tracking;
- essential-matrix relative rotation;
- D435i gyroscope integration using sensor header timestamps;
- no bag-record timestamps;
- no fixed camera/IMU offset.

The author calibration is provenance-assisted geometry, not independently
verified calibration.

Pilot results:

### `gate_01`

- usable visual/IMU pairs: 892
- zero-lag vector correlation: 0.726064772
- rotation-angle correlation: 0.912663712
- median rotation disagreement: 0.253438459 degrees

### `hall_01`

- usable visual/IMU pairs: 327
- zero-lag vector correlation: 0.801178627
- rotation-angle correlation: 0.789392968
- median rotation disagreement: 0.261404947 degrees

### `room_01`

- usable visual/IMU pairs: 300
- zero-lag vector correlation: 0.799642368
- rotation-angle correlation: 0.443691319
- median rotation disagreement: 0.397622125 degrees

The opposite visual-rotation convention produced the opposite vector-correlation
sign in the pilot, supporting the selected rotation convention.

Zero-lag agreement is physical-content evidence only.

It is not synchronization proof.

## Frozen lag pilot

The frozen visual method was then used for a predeclared diagnostic lag scan.

No lag-specific sample admission was permitted.

The lag grid used a 1 ms characterization step and did not define a
synchronization tolerance.

Primary vector-correlation optima:

- `gate_01`: +23 ms
- `hall_01`: -67 ms
- `room_01`: -3 ms

Best-minus-zero vector-correlation improvements:

- `gate_01`: 0.000588045
- `hall_01`: 0.005890235
- `room_01`: 0.000058340

`hall_01` hit the predeclared negative scan boundary.

Independent median-rotation-error optima were:

- `gate_01`: +8 ms
- `hall_01`: +48 ms
- `room_01`: -16 ms

Thus the diagnostic objectives disagree within trajectories and the primary
lag observations do not identify one common nonzero camera-to-IMU fixed offset.

The scan was not expanded after observing the boundary result.

No offset was frozen.

## 28-trajectory zero-lag generalization cohort

The exact frozen zero-lag method was applied to the same 28-trajectory
structurally clean cohort selected before alignment analysis in Phase 3B.

All 28 trajectories processed successfully.

Aggregate visual-success fraction:

- minimum: 0.059018812
- median: 0.499076635
- maximum: 0.996827914

Zero-lag visual/gyro vector correlation:

- minimum: 0.069851642
- median: 0.728267345
- maximum: 0.943895974

Zero-lag rotation-angle correlation:

- minimum: 0.061021378
- median: 0.710193493
- maximum: 0.974233453

Per-trajectory median rotation disagreement:

- minimum: 0.128085942 degrees
- median: 0.257421703 degrees
- maximum: 1.639230858 degrees

The result is heterogeneous.

Physical-content agreement is present on many trajectories, but it is not
uniform across the cohort.

## Dark-room counterexample

`room_dark_04`, `room_dark_05`, and `room_dark_06` are important negative
evidence.

Their visual front end reports successful relative-motion estimates on roughly
98--99.7% of consecutive pairs, yet their zero-lag visual/gyro correlation is
poor and their median rotation disagreement is substantially larger.

Approximate vector correlations:

- `room_dark_04`: 0.128502429
- `room_dark_05`: 0.160084077
- `room_dark_06`: 0.069851642

Median rotation disagreement:

- `room_dark_04`: 1.029612599 degrees
- `room_dark_05`: 1.293797904 degrees
- `room_dark_06`: 1.639230858 degrees

Therefore visual-front-end success cannot be converted into a timing-validity
mask or an automatic evaluation inclusion rule.

These trajectories were not removed or retuned after observing the result.

## Scientific interpretation

The released D435i image and IMU streams show physical-content consistency near
the recorded header coordinates on many trajectories.

The evidence does not independently establish:

- the physical exposure event represented by the RGB header timestamp;
- exact RealSense acquisition/driver configuration;
- a unique fixed camera-to-IMU offset;
- a synchronization tolerance;
- uniform visual/inertial agreement across trajectories;
- independently verified camera calibration;
- physical RGB capture synchronization.

The three-run lag diagnostic does not support a reproducible common nonzero
offset.

A 28-trajectory lag optimizer is therefore not run by default.

Phase 3C stops camera/IMU lag tuning rather than forcing a numerical answer
from non-identifiable evidence.

## Permanent evidence artifact

Repository path:

`manifests/m2dgr_camera_imu_synchronization_evidence_v1.json`

Content SHA256:

`d765f8ac13ff21dca23e289efef65fed31372189363e7fa61982e122514e190b`

File SHA256:

`95ff9fdcaf2b74a9f7b118334f0fe3626bee3afe0916c3e09df4a7451d8425c7`

The artifact is bound to Phase-3B manifest content SHA256:

`5cf660327636174912d5d304972758c1b230fa4446ab584ca4549c76fdd6f4db`

## Phase-3C successor manifest

Repository path:

`manifests/m2dgr_trajectory_manifest_v1_phase3c_camera_imu_sync_evidence.json`

Content SHA256:

`f599be5bb1b4d009fe77ff8eb33148880122f92f4bfe00f885ec18015d715387`

File SHA256:

`4453544d437b31cb0ab16b090dfa2e710fab19cb1b90cb65b53d7651166eb156`

The successor contains:

- 36 trajectory records
- 140 stream entries
- 140 synchronization entries
- 68 D435i synchronization-method updates

Only the synchronization `method` fields for:

- `/camera/color/image_raw/compressed`
- `/camera/imu`

change relative to the Phase-3B manifest.

No stream metadata, clock domains, verification status, measurement-time basis,
offset, tolerance, or non-camera synchronization entry changes.

## Explicitly not claimed

Phase 3C does not claim:

- verified RGB physical capture synchronization;
- verified common physical clock;
- a camera-to-IMU fixed offset;
- a synchronization tolerance;
- a camera timing validity mask;
- independently verified camera calibration;
- verified LiDAR capture synchronization;
- verified reference-to-estimator temporal association;
- evaluation readiness.

Synchronization remains `UNVERIFIED`.

Evaluation readiness remains `FALSE`.

## Remaining Phase-3 blockers

- LiDAR-to-IMU physical capture timing
- reference-to-estimator temporal association
- common physical clock verification
- independent calibration verification
- validation/calibration split before any data-selected synchronization
  tolerance is frozen

Camera-image-to-IMU timing has been characterized to the limit justified by the
released evidence, but physical capture synchronization remains unresolved.
