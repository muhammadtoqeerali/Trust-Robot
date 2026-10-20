# R48 — TRAIN camera intrinsic projection diagnostics

All image pixels in this experiment form a **manufactured 64-point grid** within the 640×480 dimensions authenticated by 16 recorded R33 images. Original image bytes were not opened.

Author camera parameters (fx, fy, cx, cy, k1, k2, p1, p2): [617.971050917033, 616.44513152479, 327.710279392468, 253.976983707814, 0.148000794688248, -0.217835187249065, 0.0, 0.0].

The numerical camera model uses a standard OpenCV pinhole Brown–Conrady radial-tangential convention with k3 fixed to zero. This is a **candidate interpretation of the author configuration**, not independent physical intrinsics validation.

Independent forward reprojection and inverse-model residual: max 1.42108547152e-13 synthetic pixels.

## Sensitivity on the synthetic pixel grid

- focal_length_plus_1_percent: median 0.189834316°, max 0.269431498° angular ray change
- principal_point_plus_1_pixel_xy: median 0.116067488°, max 0.131282222° angular ray change
- radial_coefficients_plus_5_percent: median 0.0167605138°, max 0.0314109539° angular ray change

## Restrictions

This numerical exercise does not estimate metric translation, camera motion, 6DoF pose, pose covariance, physical calibration quality, reference accuracy or cross-sensor time synchronization.
The published application requires an image transport adapter for the recorded compressed topic; it is not executed here.
11 scientific gates inherited from R43 remain unqualified. No ATE/RPE, health model training, real sensor factors, original bag access or confirmation_test usage.

## Next: R49

Extend the independently checked pixel/ray model with targeted model-misinterpretation and robustness controls, rather than treating numerical consistency as sensor calibration.
