# TRUST-ROBOT R135-A31-5 / A31-6 Implementation

## Scope

Implement a deterministic synthetic 15D linear Kalman
update and a four-way simulation-only trust ablation.

These components are not physical localization factors
or a robot estimator execution.

## A31-5 synthetic state update

The module uses the existing A31-3 toy measurement
descriptor and its three-by-fifteen Jacobian.

The update includes prior state covariance.

The innovation covariance is:

S = H P H^T + R

The Kalman gain is computed using Cholesky solves.

The posterior covariance uses the Joseph form.

Toy normalized innovation squared uses S rather
than measurement covariance R alone.

All input measurements and noise models are synthetic.

Numerical covariance validity is not independent
physical uncertainty calibration.

## A31-6 trust ablation

Four fixed toy screening policies are compared:

1. Unscreened synthetic state updates.
2. Synthetic full-NIS threshold screening.
3. Simulated software-delivery screening.
4. Combined synthetic NIS and delivery screening.

The policies are evaluated on two artificial candidate
measurements across the existing five deterministic
recorder-envelope replay scenarios.

The software delivery scenarios are descriptive
simulations, not measured sensor-health conditions.

The ablation does not calculate physical health
probabilities, real factor weights or pose accuracy.

An accepted synthetic update does not authorize
a physical estimator update.

## Scientific restrictions

- Independently qualified A23 receipts: 0 of 13.
- Physical BMI088 frame mapping: UNVERIFIED.
- Metric calibration: UNVERIFIED.
- Physical clock accuracy: UNVERIFIED.
- Independent six-DoF reference: UNVERIFIED.
- Real physical factors: ZERO.
- Physical estimator invoked: NO.
- Real factor admission: DENIED.
- Historical M2DGR gates: 11 CLOSED.

The M2DGR frozen split remains 22 train,
7 validation-calibration and 7 confirmation-test.

No real robot state update, motor command, new recording,
physical pose scoring, or Git publication is performed.
