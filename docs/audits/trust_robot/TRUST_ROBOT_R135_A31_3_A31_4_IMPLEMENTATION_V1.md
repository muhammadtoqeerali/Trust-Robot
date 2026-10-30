# TRUST-ROBOT R135-A31-3 / A31-4 Implementation

## Purpose

Implement a small, deterministic toy 15D innovation
diagnostic and simulation-only trust-selection interface.

These are engineering components for future estimator
research, not physically qualified observation factors.

## A31-3 toy innovation

The toy state contains fifteen scalar coordinates.

The three supported toy observation types select
XYZ coordinates at offsets 0, 3, and 6.

They are deliberately not physical camera, LiDAR,
or IMU observation models.

The module computes:

- Three-dimensional residual.
- Three-by-fifteen linear Jacobian.
- Strictly positive-definite covariance preflight.
- Normalized innovation squared using Cholesky solves.

The covariance is synthetically assigned. It does not
represent measured physical sensor noise.

The toy innovation is not an estimator state update.

## A31-4 trust selection

The trust gate consumes validated toy innovations
and deterministic software replay diagnostics.

A declared NIS threshold and a simulated stream
delivery label determine toy candidate eligibility.

Software suppression and queue overflow are treated
separately from high normalized innovation.

No factor weight is generated.

No physical sensor-health probability is generated.

Toy candidate eligibility is not permission to
construct or execute a real estimator factor.

## Integration

The five existing A29-4 replay scenarios are checked.

Synthetic low- and high-innovation examples are
screened against the software delivery observations.

The same artificial state and measurement models
are used across scenarios to test deterministic rules.

The physical ROS bag envelopes are not converted
into measurement values, sensor-header timestamps,
or qualified localization factors.

## Scientific restrictions

- Independent A23 receipts: 0 of 13.
- Physical BMI088 frame mapping: UNVERIFIED.
- Metric physical calibration: UNVERIFIED.
- Physical clock accuracy: UNVERIFIED.
- Independent six-DoF reference: UNVERIFIED.
- Physical health probabilities: NOT GENERATED.
- Physical estimator factor weights: NOT GENERATED.
- Physical localization accuracy: NOT ESTABLISHED.
- Real factor admission: DENIED.
- Original M2DGR gates: 11 CLOSED.
- Estimator invoked: NO.
- Real factors created: ZERO.

Frozen M2DGR split remains 22 training,
7 validation-calibration, and 7 confirmation-test
sequences.

No robot motion, new sensor capture, data fitting,
physical pose scoring, or Git publication occurs.
