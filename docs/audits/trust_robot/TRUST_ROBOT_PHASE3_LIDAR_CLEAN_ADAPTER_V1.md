# TRUST-ROBOT Phase-3 LiDAR Clean Adapter V1

## Purpose

This layer binds the new Phase-3 generic `EventStream` representation to the
already-frozen Phase-2 M2DGR Velodyne decoder.

It deliberately does not implement a second PointCloud2 decoder.

The adapter imports and reuses:

- `decode_m2dgr_velodyne_xyz`;
- `pointcloud_header_stamp_ns`;
- `pointcloud_field_descriptors`;

from:

`src/trust_robot/lidar_frontend.py`

This preserves the exact Phase-2 XYZ decoding semantics.

## Raw PointCloud2 byte handling

Raw PointCloud2 provenance hashing uses the Python buffer protocol through
`memoryview(...).cast("B")`.

This is compatible with both:

- Python byte buffers used by synthetic tests;
- contiguous ROS/rosbags message data buffers.

This byte handling is provenance-only. It does not decode XYZ independently
and therefore does not create a second sensor-decoding definition.

## Event representation

Each `/velodyne_points` PointCloud2 message becomes one LiDAR `EventStream`
event.

The event payload is exactly the frozen Phase-2 decoded XYZ array:

- shape: `(N, 3)`;
- dtype: `float64`;
- contiguous;
- finite;
- copied into the immutable `EventStream`.

Different scans may retain different point counts.

The EventStream source identity is:

`/velodyne_points`

and modality is:

`lidar`

## Timestamp boundary

The PointCloud2 header stamp is carried into the EventStream only as the same
ordering/state label already used by the frozen Phase-2 estimator.

The adapter does not claim that this timestamp represents scan start, scan
center, scan end, or another verified physical temporal reference.

Per-point `time` is not used.

No deskew is performed.

## Provenance receipt

Each adapted event records:

- event index;
- header timestamp;
- frame ID;
- height and width;
- PointCloud2 point/row step;
- endianness and dense flag;
- full PointField descriptors;
- raw PointCloud2 data SHA256;
- raw data size;
- decoded XYZ shape;
- decoded XYZ dtype;
- decoded XYZ data SHA256.

The receipt additionally binds the resulting clean EventStream fingerprint.

Receipt content is itself SHA256-bound.

## Real TRAIN smoke

The first three `/velodyne_points` messages from frozen TRAIN `Circle_01` are
used only for a mechanical clean-adapter proof.

The same three already-deserialized messages are adapted twice.

Required proof:

- source PointCloud2 bytes unchanged;
- EventStream fingerprint exactly reproduced;
- adapter receipt exactly reproduced;
- each EventStream payload exactly equals direct output from the frozen
  Phase-2 decoder.

No corruption is applied.

## Scientific boundary

This layer does not:

- access reference trajectories;
- access confirmation-test trajectories;
- run the estimator;
- compute ATE/RPE;
- score localization;
- select severity;
- select an attack budget;
- select any corruption parameter;
- establish physical timestamp semantics;
- perform deskew.

Phase-3 exit evidence therefore remains unsatisfied after this layer.

The next corruption experiment must remain prospectively specified and cannot
derive corruption magnitude from reference error or confirmation outcomes.
