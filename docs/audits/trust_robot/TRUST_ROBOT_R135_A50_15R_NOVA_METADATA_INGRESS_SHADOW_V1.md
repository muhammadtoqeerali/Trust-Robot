# R135-A50-15R Nova physical ROS metadata ingress shadow

## Purpose and scope

Two offline, payload-free diagnostic modules validate the
observed Nova ROS message layout.

No ROS runtime, sensor launch, robot I/O, recording,
estimator, localization, sensor-health model or
power/charging commands.

## Basis and provenance

A50-9 and A50-10 observed ROS sensor messages and structure.
A50-12 produced 18 private physical-unqualified descriptors.
A50-13 transferred and schema-reviewed them on KIOS.
A50-14 tested an offline ROS-shaped-object ingress projection.

Only manufactured fixtures are included in proposed tests.
Private physical metadata, logs, network endpoints and
receipts are excluded.

## Observed interface contract

- Left/right images: 1920x1200, rgb8.
- CameraInfo: rational_polynomial, 8 distortion coefficients.
- LiDAR: 128000x1, point_step 26.
- Fields: x, y, z, intensity, ring, timestamp.
- BMI088: no orientation estimate declared.
- Zero IMU covariance fields are not calibrated uncertainty.

Checking frame ID and Python class name does not independently
establish physical sensor identity.

Monotonically increasing header timestamps do not prove
clock accuracy or physical synchronization.

## Scientific boundary and safety

The existing A29 fusion boundary refuses real factor admission.

Physical calibration, metric extrinsics, event-time semantics
and independent reference are not qualified.

A23 evidence requests remain unfulfilled.
Eleven original M2DGR scientific gates stay closed.

No physical localization accuracy, qualified sensor-health
labels, closed-loop controller or safe-stop policy is authorized.

Real factor admission: DENIED.
Robot actuation: DENIED.
Power and charging management: OUT OF SCOPE.

Git publication requires separate review and authorization.
