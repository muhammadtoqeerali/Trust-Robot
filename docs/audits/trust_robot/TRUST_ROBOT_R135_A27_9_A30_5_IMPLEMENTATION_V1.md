# TRUST-ROBOT R135-A27-9 / A30-5 Implementation

## Purpose

Implement SE(3) uncertainty propagation and exact,
anchored synthetic event-clock calculations.

These modules supply estimator-support mathematics
but do not admit real sensor observations.

## A27-9 SE(3) covariance

Transform convention: T_target_source.

Perturbation convention:
left perturbation with twist order rho_xyz, phi_xyz,
expressed in the target coordinate frame.

The composition formula assumes independently
distributed perturbations. The caller must explicitly
declare that mathematical assumption.

The software does not prove physical independence,
sensor calibration, or covariance provenance.

The covariance matrix is checked for symmetric
positive-semidefinite structure. This is only
a numerical property, not evidence of uncertainty
measured on actual hardware.

## A30-5 clock arithmetic

Clock-domain mapping uses explicitly defined
source and target anchor timestamps.

Rational scale and integer nanosecond timestamps
avoid loss of integer precision at large epochs.

Conservative uncertainty bounds cover declared
source uncertainty, mapping uncertainty and
an anchored drift bound.

All example events and clock relationships
are synthetic and unqualified.

No recorded ROS timestamp is automatically
converted into a sensor exposure, IMU sample,
LiDAR firing event, or physical reference time.

## Scientific restrictions

- Real factor admission: DENIED.
- Historical M2DGR gates: 11 CLOSED.
- Qualified independent A23 receipts: 0 of 13.
- Physical sensor-frame mapping: UNVERIFIED.
- Physical extrinsic uncertainty: UNVERIFIED.
- Physical clock accuracy: UNVERIFIED.
- Independent six-DoF reference: UNVERIFIED.
- Physical pose accuracy: NOT ESTABLISHED.
- Estimator invoked: NO.
- Physical factors created: ZERO.

Original M2DGR frozen split remains
22 train / 7 validation-calibration /
7 confirmation-test sequences.

No original dataset content, ROS bag payload,
or physical calibration value is used for tuning.

This phase performs no robot motion, capture,
physical factor construction or Git publication.
