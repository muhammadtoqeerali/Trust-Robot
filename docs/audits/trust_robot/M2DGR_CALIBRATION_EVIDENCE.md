# M2DGR Calibration Evidence

## Status

Calibration verification remains incomplete.

This checkpoint records calibration provenance, frozen sensor-content evidence,
the remaining calibration requirements, and a contract-level distinction
between artifact integrity and sensor-calibration verification.

It does **not** declare M2DGR calibration verified.

## Bound source artifacts

- Phase-3D trajectory manifest:
  `67fe08bff676689dd212da03dce8e16ecee277c96f38f752d0d38a5e4e54cf6f`
- Phase-3E reference temporal evidence:
  `4f6580c6a0b06b4089990adcc700b5d823a748bacacfc0f00c3dd3b4169d9117`
- calibration source provenance:
  `ccc265172ceee536079d55649bbe40901ccaba50c82f5b0362bf2e3b9ac449ab`
- frozen rotation hypothesis challenge:
  `ab0e4f32ed91ca6045336eec85320108342e7ebc356673a9306ddff6c052b4e2`
- calibration requirements inventory:
  `86aba0afbbf2c7c0279365632379bf5d96b8fc9739a0a025b9a2fde1b1c5cc3a`

## Author calibration provenance

The current upstream calibration source is tracked at revision
`5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5`.

The released `calibration_results.txt` SHA256 is
`e515207fcf53668953a21a2e4d990643007a3a12ad54b91c456a8ee8a8100a90`.

The source history contains explicit calibration rectification. The current
source also retains known quality flags, including a `to be changed` marker and
malformed/non-ASCII numeric formatting in some camera calibration blocks.

No `/tf`, `/tf_static`, `CameraInfo`, or calibration-like ROS topic was found
in the 36 released bags under the frozen connection inventory.

## D435i IMU relative rotation

The Phase-3B diagnostic was reused without reopening bags or refitting a
rotation.

Across the frozen 28-trajectory structurally selected cohort:

- published rotation > identity: 28/28
- published rotation > published-transpose alternative: 28/28
- published rotation > both fixed alternatives: 28/28
- minimum published-minus-best-alternative score:
  `0.9030439055777579`
- median published-minus-best-alternative score:
  `0.9901506700620717`

No rotation, lag, motion threshold, score threshold, or exclusion rule was fit
for this calibration checkpoint.

This is independent released sensor-content support for the published relative
IMU rotation convention. It is **not** full extrinsic-calibration verification.

## Calibration requirements

The frozen requirements inventory records:

- independently verified full extrinsics: 0
- independently verified camera intrinsic sets: 0
- independently verified reference sensor-origin-to-LiDAR lever arms: 0
- relative rotations with strong fixed-hypothesis sensor-content support: 1
- published mocap-to-LiDAR transform found: false

Camera intrinsics, camera/LiDAR extrinsics, HandsFree/LiDAR translation/full
extrinsic calibration, reference lever arms, and mocap-to-LiDAR calibration
remain unresolved.

## Contract hardening

Historical trajectory manifests stored raw-bag SHA artifacts under
`calibration_artifacts`. Those artifacts verify file integrity, not sensor
calibration.

The hardened contract therefore distinguishes:

- `artifact_integrity`
- `calibration_provenance`
- `sensor_calibration_verification`

Legacy manifest artifacts decode as `artifact_integrity`. They do not establish
sensor calibration.

A `sensor_calibration_verification` artifact must have
`verification_status=verified` and must explicitly identify affected streams
or frames.

Historical manifests remain byte-identical.

## Manifest decision

No calibration successor trajectory manifest is created.

The Phase-3D trajectory manifest remains authoritative and byte-identical with
file SHA256:

`67fe08bff676689dd212da03dce8e16ecee277c96f38f752d0d38a5e4e54cf6f`

Calibration status is not upgraded because full estimator/reference calibration
requirements are not independently verified.

## Frozen conclusion

- author calibration provenance established: TRUE
- author cross-file consistency established: TRUE
- D435i IMU relative rotation has independent sensor-content support: TRUE
- full extrinsic calibration verified: FALSE
- translation verified: FALSE
- camera intrinsics verified: FALSE
- camera/LiDAR extrinsic verified: FALSE
- HandsFree/LiDAR full extrinsic verified: FALSE
- reference lever arms verified: FALSE
- dataset calibration verified: FALSE
- synchronization verified: FALSE
- evaluation ready: FALSE

Permanent evidence content SHA256:

`81b430950c274840c5611f76e9cd0d5be18382f884d1b7870e7d827bd5bdc3b6`
