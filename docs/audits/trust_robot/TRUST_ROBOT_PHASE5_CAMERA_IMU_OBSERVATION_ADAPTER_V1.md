# TRUST-ROBOT Phase-5 Camera / IMU Raw Observation Adapter V1

Status: implemented locally; not promoted.

## Purpose

This layer creates deterministic provenance receipts for M2DGR camera and IMU
serialized observations before any diagnostic-feature selection.

Supported M2DGR streams:

- camera: `/camera/color/image_raw/compressed`
- IMU: `/camera/imu`
- IMU: `/handsfree/imu`

No preference between the two IMU streams is selected here.

## Preserved direct observations

Each receipt preserves:

- modality;
- exact source stream;
- trajectory/session identifier;
- declared split role;
- message index;
- ROS message type string supplied by the caller;
- serialized payload size;
- SHA-256 of the serialized payload;
- bag/container record time;
- header timestamp when supplied.

The serialized payload is not decoded by this layer.

## Timing boundary

Bag record time remains transport/container time only.

Header timestamp presence does not establish physical capture-time semantics,
clock identity, cross-sensor synchronization or a fixed offset.

No synchronization offset, interpolation policy, tolerance or physical
measurement-time mapping is selected.

## Diagnostic boundary

No camera feature contract is selected.

No IMU feature contract is selected.

No feature vector, normalization, temporal aggregation or diagnostic threshold
is produced.

The already-frozen Phase-4 LiDAR diagnostic contract is untouched.

## Health boundary

No healthy/degraded/unusable label is assigned.

No health probability, threshold, classifier architecture, training action or
calibration parameter is introduced.

Final localization error is not used as health supervision.

Confirmation-test observations may be represented for provenance, but they do
not authorize model, threshold, feature, calibration or supervision selection.

## Artifact hashes

- config: `1dd104b036e46b94990600e5484a465081a7f7f95adaa2b17b634838f222d8cd`
- module: `1ef9e34e4309fb420d05a8e14671803e5591b1efe7f07257a60ece8d9c611a92`
- test: `97ea89e262ef26ab92fe66a0529f9e6439c023b7d34a8352117bf796df0e6b11`
- upstream multimodal-foundation config:
  `37cba4494f1d84b16d3d84d106303bf649874bb3fb58c6b626ea6b5aeb1ce8a3`
- upstream multimodal-foundation module:
  `429778265826f839bd685a93d77b55d4bb0c18a2aa843c8947af28fef9916b43`
