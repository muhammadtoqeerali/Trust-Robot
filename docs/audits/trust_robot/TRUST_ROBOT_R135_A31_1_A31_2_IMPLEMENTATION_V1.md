# TRUST-ROBOT R135-A31-1 / A31-2

## Purpose

Add deterministic synthetic multisensor event association
and software delivery observability for the trust-aware
localization engineering pipeline.

## A31-1 event association

Event timestamps are exact integer nanoseconds or
rational mapped timestamps from synthetic clock models.

Clock domains must agree, or an explicit synthetic
right-to-left clock mapping must be supplied.

A predeclared tolerance is required.

Matching is conservative, one-to-one, order-preserving,
and greedy rather than globally optimal.

No automatic clock fit, learned association threshold,
real exposure time or physical measurement synchronization
is inferred.

## A31-2 software observability

Consumes existing deterministic recorder-envelope replay
scenario reports from A29-4.

Separately reports source records, delivered records,
intentional synthetic suppression, and queue overflow.

The labels describe simulated software delivery behavior.

They are not physical sensor health classifications,
health probabilities, calibration confidence, or
estimator factor weights.

## Integration

Five checksum-pinned A29-4 scenario reports are assessed.

A separate wholly synthetic camera/IMU clock example
demonstrates deterministic two-event association.

The physical rosbag recorder timestamps are not used as
sensor exposure, IMU sample or LiDAR firing events.

## Scientific boundary

- Original M2DGR scientific gates: 11 CLOSED.
- Real factor admission: DENIED.
- Independently qualified A23 receipts: zero of thirteen.
- Physical timing and clock accuracy: UNVERIFIED.
- BMI088 frame relationship: UNVERIFIED.
- Metric physical calibration: UNVERIFIED.
- Independent six-DoF reference: UNVERIFIED.
- Physical health inference: NOT AUTHORIZED.
- Real factor count: ZERO.
- Physical pose evaluation: NOT PERFORMED.

The historical M2DGR split remains 22 train,
7 validation-calibration, 7 confirmation-test.

No physical factor admission, robot motion,
new recording, or Git publication occurs in this phase.
