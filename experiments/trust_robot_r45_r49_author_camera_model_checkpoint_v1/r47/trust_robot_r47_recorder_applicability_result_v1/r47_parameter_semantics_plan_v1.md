# R47 — Author parameters vs recorded room_02 interfaces

Evidence derives only from pinned R33/R34/R35/R42 and exact Git-blob-matched R46 author files. No additional ROS bag messages were decoded.

## Verified recorded compatibility

- Camera: 16 authentic color frames are 640×480, frame `camera_color_optical_frame`, ROS connection #4.
- Camera YAML selects `/camera/color/image_raw`, but the bag contains only `/camera/color/image_raw/compressed` as `sensor_msgs/CompressedImage`; a transport/decompression adapter is required for a raw-image subscriber.
- Published camera intrinsics dimensions are numerically compatible, but matching dimensions do not independently prove physical calibration or device serial applicability.
- Camera and LiDAR application configurations both select HandsFree IMU topic (`/handsfree/imu` after normalizing the LiDAR relative name). Recorded HandsFree frame is `base_link`.
- A distinct `/camera/imu` also exists with recorded frame `camera_imu_optical_frame`; **do not substitute the streams or frames**.
- LiDAR YAML `velodyne_points` normalizes to recorded `/velodyne_points`, ROS connection #9.
- The camera application IMU noise settings match 10× published Xsens values, not the published HandsFree noise values; do not interpret as independently estimated noise.
- Short header-gap diagnostics: HandsFree median 6.909012 ms; camera IMU median 4.978777 ms. They do not establish physical sample rates, clock offset or synchronization.

## Scientific restrictions

All camera geometry, complete extrinsics, physical timing, noise covariance, mocap reference, metric scale and pose-factor gates remain closed. No independent calibration or ATE/RPE scoring performed.

## R48

Perform bounded numerical projection/undistortion consistency diagnostics using the author's Git-verified camera model and TRAIN-only recorded image dimensions. Maintain explicit no-ground-truth and no-pose-factor gates.
