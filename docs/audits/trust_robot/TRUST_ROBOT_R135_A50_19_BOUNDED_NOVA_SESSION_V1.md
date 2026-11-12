# TRUST-ROBOT R135-A50-19 — Bounded Nova diagnostic session checkpoint

## Status and provenance

A50-16RR published baseline commit `4ae9018fdad0bf9c3ef8817c67eeb329f3709d32` on branch `kios-isaacsim-v15-integration`.
That checkpoint contains two Nova ROS-shaped metadata adapters, 40 manufactured adapter tests and a comprehensive earlier project handoff document.

A50-17, strictly KIOS offline: private bounded metadata session, 18 manufactured tests passed. Candidate SHA-256 `322473a80cb7198be3735c4e04214cff9ff039d61e737a4b633e22c4a59b6baf`; private receipt SHA-256 `5c9c3feaaed42080d6ffd7593c19b7bbf5698c9048addf0dceb2b52cf8a17e30`.

A50-18, strictly KIOS offline: hardened projector exception boundary; 12 new adversarial tests plus A50-17's 18 and earlier 89 regression tests = 119 selected tests passed. Hardened candidate SHA-256 `9a0a103dfb90ba5fac28793e36a3b815f7285f51ccd72379bffe658935879ffe`; private receipt SHA-256 `bd00c327a3f56c3889ea27876cba0244ed4e2bcb95c29344d58dc9976082dd00`.

## Software contract

Six allowlisted Nova streams: left/right Image, left/right CameraInfo, Hesai PointCloud2 and BMI088 Imu. A bounded session accepts at most three metadata records per stream and only up to an injected monotonic deadline of 20 seconds. Invalid topic, header sequence, timestamp or message metadata fails closed and clears held descriptors; normal completion also clears held descriptors. Unexpected ordinary Python exceptions in the projector are caught and cause session closure and metadata clearing. These are test-object contracts; no physical event-time calibration is claimed.

The `now_ns` value is **injected by the caller**. This module is NOT a real-time watchdog and CANNOT guarantee cleanup of a blocked ROS callback or crashed subscriber process. `except Exception` also does not catch every `BaseException`, nor does it provide process supervision. No ROS subscription or driver startup has been implemented in this checkpoint.

No raw image pixels or LiDAR points are accessed, saved or published by this code. Tests are manufactured and self-contained, without private Nova metadata in the Git tree. ROS message class names and frame IDs do not independently attest physical hardware identity.

## Scientific and physical restrictions

Real sensor factor admission DENIED; health weighting DENIED; pose/localization accuracy NOT ESTABLISHED; robot actuation DENIED. Physical clocks, camera/LiDAR/IMU extrinsics, faults/attack labels, independent ground truth and statistical uncertainty remain unqualified. Original M2DGR eleven gates CLOSED and A23 qualified witness requests 0/13. The frozen research dataset split remains 22 train / 7 calibration-validation / 7 confirmation-test; never retune on confirmation data. KIOS handles offline implementation and Git publication. Nova Jetson holds drivers; any future *stationary* sensor-only testing requires explicit onsite supervision and operator approval. Verona/UNIVER keeps the real M2DGR corpus separate from KIOS and Nova. No charging, motor or navigation commands are authorized.

## Next phase

Only after reviewing and separately approving this code for publication: add and test an independently supervised, non-actuating, read-only diagnostic ROS subscriber on KIOS first with mock ROS inputs. Require an external monotonic wall-time supervisor and killable process group, explicit consent, bounded subscriptions, safe cleanup, no payload persistence and no automatic ROS driver startup unless separately authorized. Then review the exact Jetson execution plan. Physical scientific evidence gates remain closed.
