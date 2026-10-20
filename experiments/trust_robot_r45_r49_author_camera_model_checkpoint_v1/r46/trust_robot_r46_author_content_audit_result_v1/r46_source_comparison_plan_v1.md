# R46 — Official author parameter content audit

Exact bytes of three published files were reconstructed offline and matched to their immutable Git blob SHA1 identifiers. Source integrity is not physical calibration certification.

## Source-level numerical comparisons

- RealSense 640×480 intrinsics: fx=617.971050917033, fy=616.44513152479, cx=327.710279392468, cy=253.976983707814; distortion coefficients match the camera YAML.
- Author intrinsics have cx/cy in the last row under row-major reading; automatic standard OpenCV matrix interpretation would be unsafe.
- Author RealSense-to-LiDAR translation: [0.30456, 0.00065, 0.65376] m.
- Author HandsFree-IMU-to-LiDAR translation: [-0.27255, 0.00053, -0.17954] m.
- Camera YAML lidar_to_cam translation numerically matches the inverse HandsFree-to-LiDAR translation, not RealSense-to-LiDAR.
- Camera YAML uses HandsFree IMU topic but its four noise parameters are 10 times the author Xsens values.
- LiDAR YAML noise values match the author HandsFree IMU values.
- Camera-to-IMU translation discrepancy against the arithmetic difference of author sensor offsets is [0.0, -0.00023999999999999998, 2.999999999997449e-05] m, norm 0.00024186773244895332 m. This does not validate a 6DoF transform.
- Camera application td=0 and estimate_td=0 are defaults, not physical synchronization evidence.
- The author calibration document contains formatting irregularities; do not parse the entire document as valid YAML.

## Scientific admission

All 11 physical qualification gates remain NOT QUALIFIED. No real pose factor, health label, ATE/RPE score, physical clock mapping or mocap reference qualification was produced.

## Next R47

Investigate frame direction, exact RealSense model and recorded topic applicability, sensor-to-body mappings and clock/IMU parameter provenance using independent receipts.
