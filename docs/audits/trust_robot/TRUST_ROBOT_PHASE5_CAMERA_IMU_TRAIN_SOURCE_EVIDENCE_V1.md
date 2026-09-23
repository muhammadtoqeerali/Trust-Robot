# TRUST-ROBOT Phase-5 Camera / IMU TRAIN Source Evidence V1

Status: permanent compact evidence binding implemented locally; not promoted.

The verified real-M2DGR TRAIN ingestion and representative feasibility
characterization are now bound into a repository-resident evidence manifest.

## TRAIN population

Exactly 22 frozen TRAIN trajectories are represented.

Validation and confirmation-test data were not used.

## Camera

The M2DGR color stream is:

`/camera/color/image_raw/compressed`

Verified TRAIN coverage:

- present trajectories: 20 / 22;
- absent trajectories: `street_010`, `street_09`;
- messages: 107,675;
- serialized bytes: 3,429,452,123;
- header stamps structurally present: 107,675.

Twenty representative TRAIN camera messages were inspected.

All twenty were reported as:

`rgb8; jpeg compressed bgr8`

Pillow was available and all 20 representative JPEG payloads decoded
successfully. OpenCV was not available.

This representative check is not full-stream camera feature validation.

## IMU

D435i IMU stream:

`/camera/imu`

- present trajectories: 20 / 22;
- absent trajectories: `street_010`, `street_09`;
- messages: 1,404,805.

HandsFree IMU stream:

`/handsfree/imu`

- present trajectories: 22 / 22;
- messages: 1,304,477.

Representative IMU fields were finite in the inspected cohort.

The observed covariance-field patterns are preserved descriptively only.
They are not converted into uncertainty, quality or health claims by this
evidence layer.

## Scientific boundary

No camera feature contract is selected.

No IMU feature contract is selected.

No diagnostic threshold or three-state health label is created.

No model is selected or trained.

No physical measurement-time interpretation, cross-sensor synchronization,
fixed offset or interpolation rule is selected.

No reference, validation, confirmation-test, ATE/RPE or final scoring is used.

## Artifact hashes

- manifest: `d4d2a73ddbcf73102cec0d0d4556fa65786a408217fefe1dece0f4d402cce675`
- validator module: `4fc2321532b7889d1b356919ee60d9036e4171221607c90d0e34f7ef9e213a73`
- tests: `62eaa35c7ef2c2f89f2f23d4eae5e84185bf64c122fa9e191a3ee1200b4ae3b8`
- verified dataset run manifest: `530b00d4134dd4b26043891d51e262a4ab3a2af025e740bb6bf2ab1f9b35edc7`
- verified dataset SUCCESS receipt: `2ca5852695cb80999e337b7b3df16f385a3dfda25160647ea3edcb1b0d5fa653`
- verification report: `be2e9f34cb8f512d0d0ffe292fcc5482d47e6ee44d8b1d3b31c986bd81ae16b5`
- verification JSON: `a2d8404668c45b4485d168aa98589b1bc14de195b1b5f120dca0f26dc025a509`
- feasibility report: `f7bf891555e8c93ba2a4146009c2bf2041cb9c2d29e30a2936ddcedf87ad18f2`
- feasibility JSON: `bc70e2b4291c8ec05c99a6a9c085361820705496283ee1d0183c07cb000a0801`
