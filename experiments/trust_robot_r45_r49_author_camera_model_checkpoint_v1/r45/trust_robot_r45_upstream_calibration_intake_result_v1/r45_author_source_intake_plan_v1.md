# R45 — Upstream M2DGR calibration source intake readiness

Immutable published upstream candidates; **no file content downloaded or qualified on KIOS**.

Upstream repository: `SJTU-ViSYS/M2DGR`.
Upstream commit: `5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5`.

## Immutable candidates

- **calibration_results.txt** — AUTHOR_PUBLISHED_CALIBRATION_TABLE_CANDIDATE; Git blob `f2b1180f9cdef4e665332a09973f9acba9d9d34e`.
  https://github.com/SJTU-ViSYS/M2DGR/blob/5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5/calibration_results.txt
  Sensor calibration and extrinsic candidates; requires applicability, matrix orientation and independent physical validation.
- **my_params_camera.yaml** — APPLICATION_CAMERA_VIO_CONFIGURATION_CANDIDATE; Git blob `9c429c28dcfc7bea2e59be5529c79ecf46cdf3c6`.
  https://github.com/SJTU-ViSYS/M2DGR/blob/5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5/my_params_camera.yaml
  LVI-SAM camera parameter choices and IMU/camera mapping; not a new calibration experiment.
- **my_params_lidar.yaml** — APPLICATION_LIDAR_IMU_CONFIGURATION_CANDIDATE; Git blob `a768b1a8f8baa5649009c941817a51ff3f3e00e9`.
  https://github.com/SJTU-ViSYS/M2DGR/blob/5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5/my_params_lidar.yaml
  LVI-SAM LiDAR and HandsFree IMU application settings; not independent physical validation.
- **README.md** — UPSTREAM_DATASET_DESCRIPTION_AND_AUTHOR_CONTEXT; Git blob `c394994a8431426c0bd4b3dcf618faf7b97d119f`.
  https://github.com/SJTU-ViSYS/M2DGR/blob/5db59c1fe38d8f1d2fb3a71f1f8c5581b8de00e5/README.md
  Dataset author describes sensor suite, synchronization claims, calibration methods and export tools.

## Critical distinction

The official dataset README and published calibration_results.txt provide prospective sensor parameters, but actual applicability to the frozen room_02 messages, matrix storage layout, sensor frame direction, complete physical clock alignment and independent reference validity have not been demonstrated.
LVI-SAM parameter YAML files may contain application-specific choices and must not override independently verified author calibration receipts.
The R43 evidence-receipt template remains fully empty. There is no incoming calibration file in this phase.

## Next R46

Audit content of specifically approved, pinned upstream sources under a separate read-only source-intake stage. Before use, independently verify SHA256, precise sensor applicability, transform orientation, units and discrepancies between the calibration table and application YAMLs. Do not admit pose factors, health labels or ATE/RPE.

No Git changes, no raw ROS bag access, no confirmation-test data.
