# R53: Author-source timing and reference intake boundary (TRAIN `room_02`)

**No evidence has been received or physically qualified in R53.** All five new receipts and all eleven original R43 gate receipts remain empty.

## Exact recorder streams needing source documentation

- `/camera/color/image_raw/compressed`: recorded `frame_id=camera_color_optical_frame`; explain hardware event represented by its ROS header timestamp, timebase, device/firmware and mapping to other streams
- `/camera/imu`: recorded `frame_id=camera_imu_optical_frame`; explain hardware event represented by its ROS header timestamp, timebase, device/firmware and mapping to other streams
- `/handsfree/imu`: recorded `frame_id=base_link`; explain hardware event represented by its ROS header timestamp, timebase, device/firmware and mapping to other streams
- `/velodyne_points`: recorded `frame_id=velodyne`; explain hardware event represented by its ROS header timestamp, timebase, device/firmware and mapping to other streams

## Questions and evidence to obtain from the M2DGR authors

1. Which exact serial number, firmware, device calibration generation and recording configuration apply to `room_02`? Does the published calibration table cover those devices?
2. For each of the four sensor topics, which physical event is stamped (exposure start/mid/end, IMU sample, LiDAR scan start/end) and which clock/timebase generates the ROS header stamp?
3. Was any clock-to-host or intersensor offset/drift correction performed during recording/export? Request calibration method, values, intervals and uncertainty; identify any per-trajectory exceptions.
4. Which ground-truth/mocap export file corresponds to `room_02`? Request original source checksum, units, coordinate conventions, tracked body and physical tracking-marker origin.
5. How was reference time linked to the sensor clocks? Request export-stage conversion details and independent timing validation, not only a statement that timestamps were calibrated.
6. Supply a traceable rigid transform (direction and units) from mocap tracked body to LiDAR and a documented resolution of the 90 invalid rotation entries.
7. Supply independent verification data and uncertainty bounds before setting any association tolerance, fitting a real pose factor or scoring ATE/RPE.

## Fail-closed admission sequence

Verify author authenticity and SHA256 of each new file, independently validate frame and clock semantics and room_02 applicability, review uncertainty and dataset splits, and then propose gate-by-gate qualification **only in a new review phase**. Never edit the frozen R43 receipts or the 22/7/7 split manifest.

Current camera color, camera IMU and HandsFree observations comprise only 48 sparse previously decoded records; the 224 nearest-header distances and 144 residuals are explicitly counterfactual diagnostics. Nine camera-IMU record-minus-header residuals are negative. They do not establish transport latency, fixed physical clock offset or calibration.

No Git modification, original bag reopening, confirmation-test access, real pose factor, health training or scoring is authorized.

## Next R54

Prepare the source request packet and a bounded intake/response tracker; progress substantive measurement only after independently verifiable external evidence is received.
