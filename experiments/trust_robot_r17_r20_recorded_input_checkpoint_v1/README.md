# R17–R20 recorded-data software provenance checkpoint

All files under `r17/` through `r20/` are verbatim small-source/test/report copies from KIOS off-Git experiments. The manifest binds every file to its SHA256 and includes commit-scoped documentation hashes. Run `python3 -B verify_checkpoint.py` from this directory to independently recheck the archive after Git clone; no ROS installation or raw `.bag` is required.

R18 original failed sources (`*.py.saved`) are retained deliberately, together with the embedded connection-record repair code and negative tests. Existing recorded source: authenticated frozen TRAIN `room_02.bag`, SHA256 `ee621ccb1a37cc19edb1424c39de9b9a2223f9dbc9b0b3dcb4e4b849e9f72ac1`. **The bag itself is never included**. The evidence includes serialized-message hashes and bounded ROS metadata, not raw sensor-image/pointcloud payloads.

This archive validates recorded observation identity, integrity, and interface readiness. It does not establish physical synchronization, full extrinsics, independently referenced pose, ATE/RPE accuracy, calibrated covariance, empirical health labels, or scientific real-sensor factor admission.
