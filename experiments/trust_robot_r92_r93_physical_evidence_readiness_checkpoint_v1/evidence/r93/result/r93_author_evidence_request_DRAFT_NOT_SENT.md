# DRAFT — NOT SENT

**Subject:** M2DGR room_02 physical calibration, clock and Vicon evidence request

Hello M2DGR dataset team,

We are conducting reproducible, trustworthy multimodal localization research using the released M2DGR training data.
We have already recovered the original room_02 ground-truth file, so we are not requesting another GT download.
Our goal is to establish independently checkable physical timing and frame definitions rather than infer them from numerical correlations.

Could you please share existing recording-specific documentation, configuration files, calibration exports or measurement logs for:

1. **Capture time and clock definitions:** the physical event associated with ROS headers, timestamp epoch and units, original publisher/device versions, and any hardware synchronization, offset, drift, mapping-sign convention and uncertainty for each sensor stream.
2. **Five relevant streams:** camera_color, camera_imu, handsfree_imu, mocap_reference, velodyne_lidar. Please specify any differences in capture-time semantics, including LiDAR scan/point firing time and RGB exposure time.
3. **Vicon geometry:** tracked rigid-body name and marker set, body origin and world reference, the mocap-body-to-LiDAR SE(3) transform with direction and metric units, and evidence applicable to room_02.
4. **Vicon time export:** what ground-truth timestamps represent, the export timebase, any conversion to the recording clock, and its uncertainty.
5. **Sensor calibration:** recording-applicable camera intrinsics/distortion and full camera–IMU, camera–LiDAR and other relevant sensor transforms, with direction, units, source version and any independent checks.
6. **Reference-quality records:** original tracking-validity indicators and recording-specific information about missing poses or invalid rotation records, so that a treatment can be predeclared without arbitrary filtering.

For each available item, a source file or document, version/date, the recording(s) to which it applies, coordinate conventions and uncertainty or independent verification details would be helpful.
If an item was not recorded or is no longer available, confirmation of that limitation is also valuable; approximate rates or an assumed zero offset are not substitutes for measured physical timing.

We will not assume these materials establish calibration or scoring readiness until we perform an independent verification.

Thank you.

**Status: draft for user review only. Not sent automatically.**
