# TRUST-ROBOT R135-A50-16 | Nova physical integration checkpoint and new-agent handoff

**Checkpoint scope:** physical Nova Carter robot metadata-only ROS ingress; the prior A48 and A29 safety and scientific boundaries are unchanged. This is a portable repository checkpoint, not physical qualification or authorization to operate a robot. **Read before continuing this work in a new chat.**

## Overall project goal

Reliability-aware multimodal edge AI for camera, LiDAR and IMU sensor diagnosis, detection of faults/attacks, trustworthy 6-DoF localization, and eventually physically safe supervised navigation. The physical target is the **existing Nova Carter mobile robot** equipped with Jetson, Hawk stereo cameras, Hesai 3D LiDAR and BMI088 IMU. We are NOT building a new robot and are NOT yet enabling motion or closed-loop sensor-health feedback. Scientific claims require independently qualified physical timing, calibration, device identity, reference trajectories, and actual fault labels.

## Machines, source boundaries and operational ownership

- **KIOS**: Ubuntu x86_64 desktop; user `kios`; TRUST-ROBOT integration and Git publication. The local Git checkout and private evidence root are identified in the separately held private context-transfer file, not in this public checkpoint. Past Nova launch copy is under a private `physical_evidence_inbox/r135_a25e3_5uiqvv0g/` directory. Private data and receipts are NOT to be committed.
- **Nova physical Jetson**: Ubuntu ARM64, user `nvidia`, ROS 2 Humble at `/opt/ros/humble/setup.bash`; ROS CLI is not on the initial user PATH until this environment is sourced. Historical physical sensor-only launch is in the Jetson user home under `trust_robot_evidence/r135_a25e3_5uiqvv0g/three_sensors.launch.py`. Jetson is for carefully approved, stationary tests only. No Docker containers were running when A50-3R inspected it.
- **Verona/UNIVER**: separate real M2DGR research/data workstation; its dataset, frozen data partitions, source receipts and research-specific implementation are NOT on KIOS and must not be accidentally recreated or retuned. See `TRUST_ROBOT_DUAL_WORKSTATION_SOURCE_BOUNDARY_V1.md`. Frozen M2DGR split is 22 train / 7 validation-calibration / 7 confirmation test. The confirmation test cannot be used for retuning.
- **Windows access path**: user opens SSH to KIOS or Nova from PowerShell; SSH endpoint addresses, credentials, per-host secrets, raw logs, and private source data stay outside Git. The physical target is Nova; the existing KIOS Isaac Sim reference files are synthetic, not physical drivers.

## GitHub provenance and publication discipline

Origin `https://github.com/muhammadtoqeerali/Trust-Robot.git`; branch `kios-isaacsim-v15-integration`; **pre-A50-16 published HEAD `0c5d2893edba0c0e25b8457dc04f003ccda26a72`** (A48-3). A50-1 through A50-15R were private, with no Git commits or pushes. A50-16 publishes the five reviewed source/test/doc files plus this continuity document only after the KIOS tests, exact-path review, operator approval, normal non-forced push, and independently verified remote HEAD. Later agent must inspect the A50-16 publication receipt and current Git HEAD; do not assume the pre-A50-16 SHA is still the tip. Never push raw physical evidence, machine-specific network endpoints, datasets, device logs or credentials. Never rewrite Git history or force-push.

## Previously published scientific research

- Published A48-3: synthetic camera information/uncertainty-readiness result, 389 tests previously passed. The information ratios 4x and 0.25x under chosen manufactured residual scales are NOT calibrated physical covariances. Original A23 13 evidence requests remain unfulfilled; 11 M2DGR scientific gates remain CLOSED.
- Published A25/A26/A29 offline metadata and ROS analysis: prior physical Nova observations, integrity diagnostics and ROS bag envelopes, **not independently qualified physical sensor time or extrinsics**. Existing `src/trust_robot/physical_ros_fusion_boundary_v1.py` refuses real factor creation and physical localization scoring. Earlier ROS metadata audit recorded 848 IMU, 16 left/right RGB images each, 139 point clouds and clock-correlation messages; descriptive intervals are not validated physical timing.
- KIOS Isaac Sim V15 reference/staged synthetic work is distinct from the physical Nova sensor drivers. Prior navigation/goal sender samples are NOT permitted to run on physical Nova.

## A50 progress: static to physical to software, with precise boundaries

- **A50-1** KIOS offline Nova inventory: 9/9 tests. Located the historical `three_sensors.launch.py` copy and ROS/SIM launch references. No Jetson contact.
- **A50-2** static AST launch map: 9/9 tests. Physical historical launch references a `rclcpp_components` multi-threaded `sensors` container and includes four sensor-specific launch files. No physical driver test.
- **A50-3** first Jetson ROS CLI audit failed PATH preflight. **A50-3R** sourced `/opt/ros/humble/setup.bash`: Humble available; zero ROS nodes, two default topics, no running Docker containers, installed Hawk/Hesai/BMI088/correlation packages. No sensor drivers started.
- **A50-4** Jetson static installed package review: six ROS packages, 29 launch/config files; identified `HawkNode`, `hesai_ros_driver_node`, `Bmi088Node` and `CorrelatedTimestampDriverNode`.
- **A50-5** static source SHA and remap review: 9 files; Hesai config suggested `hesai_lidar` frame, `/lidar_points` default and `/lidar_packets`; Hawk and IMU remap `correlated_timestamp` to `/correlated_timestamp`. STATIC defaults are not proof of runtime names.
- **A50-6/6R** KIOS verified historical launch-copy SHA `496dd455a2815782f23687e1e7b75cdb1c8c8f75dc924b829c3b269200c3dfd6`. The physical historical launch includes `hawk.launch.py`, `hesai.launch.py`, `bmi088.launch.py`, `correlated_timestamp_driver.launch.py` and the `sensors` component container.
- **A50-7** Jetson verified all five installed driver/config source pins and found the SAME historical launch SHA on Jetson. No transfer required.
- **A50-8** authorized bounded stationary driver graph smoke: 14 relevant advertised topic entries, clean launch process-group shutdown, zero post-run nodes. `ros2 node list` showed 0 even with topics, so never use node count alone as proof of no publishers. No payload capture or physical evidence qualification.
- **A50-9** authorized bounded message smoke: left/right 1920x1200 RGB8 images (3 each), LiDAR 128000-point PointCloud2 messages (56), IMU (166); per-stream first three positive/monotonic header stamps; process-group shutdown verified and zero post-run nodes. Metadata only, no payload saving.
- **A50-10** authorized bounded schema shadow: three CameraInfo/PointCloud2/Imu messages each, plausible left/right intrinsics but no independent calibration; 6 LiDAR fields/26-byte stride, no IMU orientation estimate declared, zero covariance elements not calibrated uncertainty, clean shutdown.
- **A50-11** KIOS PRIVATE offline schema adapter with manufactured fixtures: 28 new tests + 49 existing physical boundary tests = 77 passed. Candidate private directory `r135_a50_11_nova_schema_Vpk00DiZ`; private receipt SHA `78b2760f4dfe87fed58897f3cc90956fdd64626a869a37596d225c7616f73fff`.
- **A50-12** authorized Jetson six-stream physical metadata acquisition: exactly 3 each of LEFT_IMAGE, RIGHT_IMAGE, LEFT_INFO, RIGHT_INFO, LIDAR and IMU; positive strictly increasing header stamps within each stream. Process-group shutdown verified, zero postrun sensor topics/nodes. Raw images and point clouds NOT saved. Private Jetson directory `a50_12_nova_metadata_6V27saXO`; JSON SHA `365ebaf17305aae57429709637d64a398f16a72f7d3f7d2e478f5a1d4746e547`.
- **A50-13** KIOS approved SHA-pinned SSH copy of those 18 physical-unqualified metadata rows into private `r135_a50_13_nova_metadata_7qJFotrP`; 77 tests passed; adapter accepted metadata ONLY and refused all real factors. Receipt SHA `1c7565b899b9d02282fc5c6ace22957a6494ac34459d267f900b538846c253d7`.
- **A50-14** KIOS private ROS-shaped metadata ingress prototype with no ROS runtime and payload access blocked; 12 new ingress tests + 77 regression tests = 89 passed. Private `r135_a50_14_nova_ingress_QWU3Y8WL`; receipt SHA `dfc6acacfa21e56409fb8ce5a227781206fdf458645907c9a2f34a69c913f7a2`.
- **A50-15** first publication staging failed due a wrong expected multiline source import; a later placeholder test was also invalid. No Git writes. **A50-15R corrected** private publication staging `r135_a50_15r_publication_stage_L04WdWb4`: exact five files, 89 portable self-contained tests passed, private 18-row physical metadata replay passed. Private staging receipt SHA `77f8c5cb844fb68e86cd8310773656d5d7f18641cfd17d0a8a4735993d9e1051`. Git checkout unchanged at its end.

## Runtime ROS topic and message facts from stationary Nova

| Stream | Topic | Type / frame |
|---|---|---|
| Left image | `/front_stereo_camera/left/image_raw` | `sensor_msgs/msg/Image`; `front_stereo_camera_left_optical` |
| Right image | `/front_stereo_camera/right/image_raw` | `sensor_msgs/msg/Image`; `front_stereo_camera_right_optical` |
| Left info | `/front_stereo_camera/left/camera_info` | `sensor_msgs/msg/CameraInfo`; left optical frame |
| Right info | `/front_stereo_camera/right/camera_info` | `sensor_msgs/msg/CameraInfo`; right optical frame |
| LiDAR | `/front_3d_lidar/lidar_points` | `sensor_msgs/msg/PointCloud2`; `front_3d_lidar` |
| IMU | `/front_stereo_imu/imu` | `sensor_msgs/msg/Imu`; `bmi088_frame` |
| Clock correlation | `/correlated_timestamp` | `isaac_ros_nova_interfaces/msg/CorrelatedTimestamp`; not yet timing-qualified |

Image layout 1920x1200 `rgb8`; CameraInfo `rational_polynomial`/8 distortion terms; LiDAR `width=128000`, `height=1`, `point_step=26`, `row_step=3328000`, fields `x:0:7:1`, `y:4:7:1`, `z:8:7:1`, `intensity:12:7:1`, `ring:16:4:1`, `timestamp:18:8:1`. `is_dense=False`. IMU has no declared orientation estimate; observed zero covariance values are NOT certified uncertainty. Timestamps being positive and increasing only validates field consistency, NOT physical clock/exposure synchronization.

## Publishable A50-16 code contract

`nova_schema_shadow_v1.py` matches six explicit topics, known frames/layouts, returns only metadata descriptors and passes through the existing A29 **fail-closed** physical fusion boundary. `nova_ros_ingress_shadow_v1.py` projects ROS-shaped message headers/schema without reading `.data`; it rejects incompatible topics/classes/frames/dimensions/layouts and carries `PHYSICAL_UNQUALIFIED` provenance. Both have manufactured portable tests. No live ROS subscribers, no fusion factors, no 6DoF estimator, no robot motion, no calibrated health probability. This checkpoint does NOT deploy a ROS process on the Jetson.

## Still missing / not scientifically established

Independent device/source witness, physical timestamp event semantics and clock accuracy, cross-sensor synchronization, camera/LiDAR/IMU extrinsics and uncertainty, ground-truth trajectories, sensor-fault/attack labels and calibrated probabilities, real data training or sensor-factor admission, safe-stop/controller interface and verified autonomy, power/charging idle policy. The independent A23 witness request set remains 0 of 13 qualified; the original 11 M2DGR gates remain CLOSED. No learning from the frozen confirmation partition. Charging/beeping/sleep work is a distinct read-only feasibility track; never switch chargers or motors as part of sensor integration.

## Next task after publishing this checkpoint

1. Confirm the new published GitHub commit and six exact paths; preserve receipt of nonforced push and current branch HEAD.
2. Review the published A50 schema and ingress modules for bound checks and complete runtime input requirements, **without running hardware**.
3. Design an independent, non-actuating, bounded on-Jetson diagnostic ROS subscriber wrapper using those committed modules, with explicit onsite authorization, read-only topic subscriptions, a time limit, and verified cleanup. No raw payload persistence. First test synthetic objects offline, then approved stationary Jetson shadow only.
4. Independently acquire missing sensor identity, timestamps, geometry, and external ground truth before any physical factor admission or validated reliability/pose claim. Maintain `DENIED` until separate evidence review.
5. For future Git changes, develop on KIOS; verify pinned base/branch/remote, tests and private-vs-public paths, inspect exactly what is staged, request approval, commit and normal push from KIOS, verify remote SHA and clean checkout. Never make unapproved Git writes or robot actuation.

**Interpretation of this checkpoint:** successfully transferred and validated physical-unqualified Nova message metadata against a payload-free software contract; not a demonstration of trustworthy real-time localization or autonomous behavior.
