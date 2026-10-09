# KIOS Nova Carter reference study — v1

**Status:** static source review only; no sensor, simulation, or physical experiment was run.
**Purpose:** document the existing Isaac Sim/ROS material relevant to the TRUST-ROBOT research integration, while keeping the KIOS shared workstation untouched.
**Source package:** `kios_reference_study_package_v1.zip` (SHA-256 `650f577065eab8d51d951d509eb3847318eeffbead1669793c093594b269f900`).
**Scope:** 41 files, 73,222 uncompressed source bytes, from a locally staged study selection. This is **not** a complete machine/software/data inventory.

## What the references establish

| Topic | Findings supported by source files | Evidence |
| --- | --- | --- |
| Isaac Sim dataset extension | A `nova_dataset` Python extension imports a capture script when started, and unsubscribes at shutdown. | `nova_dataset_extension/extension.toml`; `nova_dataset_extension/python/nova_dataset/__init__.py` |
| Synthetic camera output | A Script Editor/Replicator workflow selects a Nova Carter front-left camera prim. Configured output is RGB, tight 2-D bounding boxes, and semantic segmentation at 1280×720. The newer extension script schedules nominally 2 images/sec using wall-clock time. | `nova_dataset_extension/python/nova_dataset/nova_dataset_script.py` |
| Capture script variants | Two capture scripts differ: the extension version uses explicit asynchronous frame stepping, arming and a delayed, throttled capture; the separate `isaac_scripts` version uses capture-on-play. They should not be assumed interchangeable. | `nova_dataset_extension/python/nova_dataset/nova_dataset_script.py`; `isaac_scripts/nova_dataset.py` |
| Simulated 2-D LiDAR processing | A ROS node reads `sensor_msgs/LaserScan` on `/front_2d_lidar_scan` and publishes closest range and point. It is **not** a raw 3-D LiDAR driver, health detector, or Hesai decoder. | `lidar_front_detector/lidar_front_detector/front_2d_detector.py` |
| Visual SLAM configuration | A local launch file targets `isaac_ros_visual_slam_node`; the parameter file names rectified left/right stereo image and camera-info topics. Its `use_sim_time` is true. | `visual_slam/launch/vslam.launch.py`; `visual_slam/config/vslam_params.yaml` |
| Nav2 / 2-D SLAM | ROS launch and parameter files describe Nav2 map server, AMCL, planning/control and goal navigation, and SLAM Toolbox consuming `/front_2d_lidar_scan`, with simulation-time settings. | `carter_navigation/launch/navigation.launch.py`; `carter_navigation/params/my_nav2_params.yaml`; `isaac_nav_bringup/config/*`; `isaac_nav_bringup/launch/*` |
| Map metadata | A YAML map descriptor specifies a 0.05-m map resolution and refers to a `.pgm` map not included in this package. | `carter_navigation/maps/my_isaac_map.yaml` |
| Goal client | A `NavigateToPose` example publishes an initial pose and sends a navigation goal. **It must not be executed** as part of a read-only audit: it can command robot navigation when a server is available. | `nav2_goal_sender/nav2_goal_sender/send_goal.py` |
| Upstream dependencies | Included README files describe NVIDIA Isaac Sim/Isaac ROS workspaces and visual SLAM; they do not confirm the local robot's sensor calibration or operational status. | `isaac_sim_ros_readme/README.md`; `isaac_ros_common_readme/README.md`; `visual_slam_readme/README.md` |

### Important execution warning

The dataset scripts are **not read-only utilities**. Their code can create run directories, write image/label outputs, and move files within the configured dataset-output area. Starting the extension imports one of these scripts. Do not import or run these files on the shared KIOS workstation for study. Similarly, do not start the supplied ROS navigation/goal-sending code. A static source review does **not** validate runtime behavior.

## What remains unverified

The current package does **not** establish any of the following:

- Actual physical Nova Carter LiDAR make, model, firmware, interface, or driver, including whether it is a Hesai XT32.
- Physical raw 3-D scan payload schema, `.bin` element layout (e.g. XYZI), timing, frame conventions, packet availability, or recorded provenance.
- Physical camera/IMU topics, message schemas, hardware extrinsics, or cross-sensor clock alignment.
- Live ROS 2 topic publication, frame transforms, camera calibration, or sensor/device health.
- Physical failure labels or experimentally measured real-world TRUST-ROBOT diagnostic performance.
- Contents, integrity, licenses, or transfer permissions of the actual datasets visible in the earlier directory inventory.

A lack of references in this **small selected archive** does not prove the larger KIOS system lacks such components.

## Practical implications for TRUST-ROBOT

1. **Keep research claims separate.** Existing frozen synthetic M2DGR/TRAIN detection evidence must not be described as physical Nova Carter health accuracy.
2. **Protect the KIOS workstation.** Treat original Isaac Sim installations, workspaces, scripts, maps, and datasets as read-only. Work only within the dedicated project workspace; no package upgrades, ROS node launches, global configuration changes, or large copies without specific approval.
3. **Do not reuse the VLP-32C-specific capture preparation as a Hesai implementation.** A physical adapter requires an independently verified device model, message/packet format, and calibration inputs.
4. **Use simulation references for understanding, not as physical evidence.** The camera generator and Nav2/SLAM configuration can inform interface mapping and synthetic protocol design without implying hardware validation.
5. **Prefer a metadata-first follow-up.** Locate and inspect dataset *manifests/file formats and small representative samples* read-only, after reviewing each path and permission. Avoid bulk copying or interpreting undocumented `.bin` files as confirmed XYZI.
6. **Publish derived study notes first.** Do not upload original KIOS source, vendor README copies, proprietary maps, raw data, or paths containing credentials until ownership, attribution, licensing, privacy, and redistribution conditions are checked. Permission to study is not necessarily an applicable open-source license.

## Suggested next read-only inventory

On the HP workstation, from within the dedicated project directory, prepare a **small metadata-only report** for candidate real-world sensor datasets: exact parent path, file extensions, sizes, sample counts, and any adjacent README/schema/calibration files. Redact usernames, internal addresses, credentials, and non-public identifiers before sharing externally. Do not activate simulation or contact the robot.

## Review limitations and provenance

- Review method: ZIP integrity verification, static reading of selected source/config files, Python AST parsing (no execution), filename/term searches.
- All 41 source file hashes matched the included candidate manifest.
- Automated checks did not reveal obvious credentials in the selected materials, but this is **not** a security clearance or an attribution/license review.
- Local ROS packages have placeholder `TODO: License declaration` entries in `package.xml`; raw source publication needs an explicit licensing/rights decision. The archive also contains upstream/vendor-derived READMEs, which should generally be linked to their upstream projects rather than copied wholesale.
- This document contains **our derived findings only**, not KIOS source code or dataset content. It does not alter the frozen TRUST-ROBOT implementation or imply physical testing.
