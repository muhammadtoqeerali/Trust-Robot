# R134-A48 publisher calibration-source consistency

Status: **publisher-to-local transform consistency supported**.

## Source

The Hilti-Research 2022 Phasma URDF model references the dated
`20220322_calibration.yaml` file. Its Alphasense model identifies
camera 0 as the front-right camera and represents its fixed-joint
transform relative to the Alphasense IMU.

Reference repository:
https://github.com/Hilti-Research/phasma_description

Pinned publisher revision:
`79002026e9b229cf9b4e95a403eaec4f00acfd79`

Pinned calibration Git blob:
`669905cffd11b51fda31ec529f777d5eb0b2663a`

Pinned Phasma Xacro Git blob:
`694316c6aaf858584991c459d749133c0bde5489`

## R134-A48 numerical result

The user's UNIVER experiment verified the embedded publisher
calibration Git blob and local Kalibr YAML SHA256 before
comparing their transform representations.

| Transform comparison | Rotation | Translation |
|---|---:|---:|
| Inverse URDF versus Kalibr | 0.00000171 degrees | 0.000000 mm displayed |
| Direct URDF versus Kalibr | 120.95316063 degrees | 109.241498 mm |

The inverse relationship is strongly supported numerically.
The translation value is printed to six decimal places;
zero at this precision must not be interpreted as an
independent physical measurement of exact zero error.

## Interpretation

The publisher's `imu_to_cam0` URDF fixed joint describes the
camera pose relative to its IMU parent. Kalibr's `T_cam_imu`
maps IMU coordinates into the camera coordinate system.
Their inverse relationship explains the numerical agreement.

This comparison strengthens calibration source consistency
and transform-direction provenance. It does NOT constitute
an independent physical calibration validation. The two
representations may share the same original calibration.

The official S3 calibration archive was not accessed
successfully in R134-A47, so archive byte identity remains
unestablished.

## Explicitly unresolved

- The mapping from recorded `cam0_sensor_frame` to the
  Phasma URDF camera frame is not independently certified.
- The mapping from recorded `imu_sensor_frame` to the
  Phasma URDF Alphasense IMU frame is not certified.
- No bag `/tf` or `/tf_static` provided this mapping.
- No source-specific capture clock or timestamp offset
  certification has been completed.
- No metric 6-DoF localization accuracy was established.
- No independent ground truth was accessed.
- No real estimator factor or health label is authorized.

The publisher's 2023 hardware documentation must not be
silently substituted for the 2022 recording's frame semantics.

All 11 M2DGR scientific gates remain CLOSED and the frozen
22 TRAIN / 7 CAL-VAL / 7 confirmation-test split is unchanged.

## Evidence quality

The accompanying JSON transcribes the R134-A48 terminal
output and records public Git object identities. The test
checks transcription and boundary declarations; it does
not independently reproduce the UNIVER calculation or
cryptographically attest the terminal log.
