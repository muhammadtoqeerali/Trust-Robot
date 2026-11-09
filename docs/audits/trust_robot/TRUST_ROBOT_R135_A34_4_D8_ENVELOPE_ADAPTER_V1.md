# R135-A34-4-D8 — Read-only ROS bag recorder-envelope adapter

## Engineering purpose

Add a bounded, read-only ROS 2 SQLite metadata inventory module and focused tests.
It enumerates ROS topic names, message types, recorder-envelope counts, and recorder
SQLite timestamp ranges. It does not deserialize messages or access ROS headers.

## Evidentiary boundary

This module is for engineering inspection of recorder metadata, **not** for qualifying
physical sensor identity, event-time accuracy, metric calibration, independent
six-degree-of-freedom ground truth, or trustworthy sensor factors.
Recorder envelope times must not be presented as camera exposure, IMU sample,
or LiDAR firing times. There is no real-factor admission path.

The A23 physical evidence requirements remain separate and unfulfilled; the original
11 M2DGR scientific gates remain closed. The frozen 22/7/7 dataset split and the
non-pristine historical confirmation-inspection caveat are unchanged.

## Review scope

- `src/trust_robot/real_rosbag2_metadata_adapter_v1.py` is unchanged from the
  privately tested candidate source.
- `tests/trust_robot/test_real_rosbag2_metadata_adapter_v1.py` changes only the
  import path required for the repository package layout.
- The adapter uses SQLite URI `mode=ro&immutable=1`, checks read-only schema and
  timestamp invariants, and refuses symlinked bag directories or shards.
- An independent metadata-query implementation cross-checked the candidate on a
  frozen Nova stationary recording. This is not independent physical measurement.
- Public files exclude raw recordings, host identifiers, private evidence receipts,
  credentials, physical host paths, and unpublished device identity details.

Publication is handled separately after the local source and regression audit.
