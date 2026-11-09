# R135-A35-6 — Bounded typed ROS replay-index interface

## Purpose and scope

The reusable `ros2_bounded_typed_replay_v1` module inspects *at most seven*
explicitly selected serialized ROS 2 messages in a read-only SQLite rosbag2
shard. Typed deserialization is optional and lazily resolved; a test decoder
can be injected for deterministic synthetic regression. The caller supplies
recording path, topic/type/count plan, and optional independent file/topic
integrity pins. No device-specific path, topic plan, raw recording, or private
acquisition receipt is part of this public module.

It returns recorder-envelope timestamps and ROS `Header.stamp` values as
**separate, unverified timestamp axes**. It reports camera dimensions,
encoding, stride, and data lengths; LiDAR point-cloud dimensions, point stride,
row stride, and field count; and IMU headers only. It never returns or saves
serialized CDR bytes, camera pixels, point coordinates, IMU numeric readings,
calibration matrices, or frame identifiers (only a SHA-256 digest of the latter).

## Boundaries and testing

- SQLite uses `mode=ro&immutable=1` and `PRAGMA query_only=ON`.
- Requests are limited to seven samples, 24 MiB per serialized message, and
  64 MiB total selected serialized bytes read into process memory.
- Input plans reject duplicate topics, unsupported ROS types, and counts that
  exceed the declared budget. Unsafe symlink paths are rejected.
- Image and PointCloud2 structural validations retain byte-length, stride,
  and field-bound checks; the 128,000-point organized-as-one-row shape tested
  privately is supported by the byte budget rather than an arbitrary 100,000
  width ceiling.
- Optional pinned metadata SHA-256, shard size, and complete topic inventory
  allow a caller to enforce recording identity without hardcoding locations.
- The privately tested original seven-message replay is the engineering
  antecedent, but the public interface is *generalized* and is not byte-equal
  to that private candidate. Real-recording verification of the generalized
  interface is a separate subsequent phase.

## Scientific exclusion

All replay output is **unqualified development data**. Recorder timestamps
are not verified camera exposure, IMU acquisition, or LiDAR firing times.
ROS header timestamps are not established independently as physical times.
Neither structural consistency nor successful deserialization proves sensor
calibration, physical clock alignment, independently witnessed six-DoF truth,
or localization accuracy. No real factors are admitted. The 13 separate A23
independent evidence requests remain unfulfilled, and the original 11 M2DGR
scientific gates remain closed. The frozen M2DGR 22/7/7 split and historical
confirmation-inspection caveat are unchanged.

Source and regression tests are prepared for a separate, audited GitHub
publication phase. No robot code, motion, or sensor configuration is changed.
