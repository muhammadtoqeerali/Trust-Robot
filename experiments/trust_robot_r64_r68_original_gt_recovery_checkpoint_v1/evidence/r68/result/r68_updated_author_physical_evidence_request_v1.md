# M2DGR room_02 — Ground truth recovered; physical frame and timing questions remain

Status: DRAFT ONLY — NOT SENT.

The original room_02 ground-truth file has been recovered from our
previously downloaded M2DGR dataset. There is no longer a need to request
another GT download simply because our secondary workstation lacked it.

Observed local evidence:

- GT file: room_02.txt; 504,403 bytes.
- Historical SHA256 reproduced exactly:
  79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d
- Original Phase-2 structural quality report reproduced byte-for-byte.
- 3,831 eight-column records.
- 90 structurally invalid quaternion samples under the original 0.001
  quaternion-norm tolerance, occurring in 61 sample-index runs.
- No invalid translation values found under the original structural rule.

Questions requiring authoritative evidence:

1. Which rigid body, marker constellation and physical origin does the
   released room_02 mocap position represent?
2. Is an independently measured mocap-body-to-LiDAR SE(3) transform
   available, including direction, units and coordinate conventions?
3. Which physical measurement event is represented by the released GT
   timestamp, and what clock epoch/timebase/export conversion was used?
4. How were mocap GT timestamps related to ROS camera, IMU and LiDAR
   timestamps? Please specify mapping, sign convention, scope,
   offset/drift information and measurement uncertainty if available.
5. What prospective approach to invalid mocap quaternion records is
   supported? Is there an original validity indicator or tracking-quality
   flag? We have not repaired or interpolated these samples.
6. Are per-sequence calibration files or recording metadata available
   for the original room_02 acquisition?

These questions are for source qualification, not a request to select an
evaluation alignment on a test sequence. Please provide published source
files, authoritative documentation, or original acquisition receipts where
available.

No request was posted or sent by this project phase.
