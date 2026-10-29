# R135-A6: Five-node synthetic 15D factor-slot integration

Status: **development-only synthetic solver diagnostic**.

## Objective

Verify actual execution of the existing Schur-marginalized
15D estimator with four deterministic relative-pose
factor-slot configurations.

No estimator, preintegration, marginalization, calibration,
factor-weighting or health-model source code is changed.

## Integration interface

The existing function:

`estimate_marginalized(fixture, factor_factory=...)`

accepts a custom factory supplying synthetic inertial and
pose factors.

The adapter preserves all four nonoverlapping IMU factors.
It uses the existing synthetic LiDAR registration factors.

## Scenarios

1. Baseline: seven analytic LiDAR pose factors.
2. LiDAR removal: six analytic LiDAR pose factors.
3. Camera-labeled substitution: six analytic LiDAR factors
   and one camera-labeled surrogate factor.
4. Camera on removed edge: six analytic LiDAR factors
   and one surrogate occupying the removed edge.

All variants use the same five estimator nodes.

## Critical source-independence limitation

The camera-labeled surrogate copies the analytic LiDAR
relative-pose factor from edge `(1, 2)`.

Consequently, the surrogate is NOT an independently
generated camera measurement.

It is NOT visual odometry, real visual support,
cross-modal redundancy or evidence that a camera
can compensate for physical LiDAR failure.

The substitution/restore cases must produce the same
solver state content as the original baseline because
they contain the same numerical pose factors.

## What is verified

- Existing 15D nonlinear estimator executes.
- Four-window Schur marginalization completes.
- Factor ownership remains consistent.
- IMU sample reuse is prohibited.
- Selected pose-slot counts match each intervention.
- No duplicate same-edge pose factors are created.
- The synthetic output is deterministic.
- Camera and LiDAR sources remain distinguishable
  in the descriptive factor ledger.

## What is NOT established

- Physical localization recovery.
- Independent multimodal sensing.
- Robustness improvement under real faults.
- Calibrated health probabilities or labels.
- Calibrated factor information or covariance.
- Sensor frame or clock certification.
- Physical observability.
- Posterior consistency.
- RQ1/RQ2 experimental conclusions.

Synthetic truth is produced by the existing analytic
fixture constructor but is discarded without scoring
or used-for-selection access.

No recorded reference or confirmation-test data is read.

All 11 M2DGR scientific gates remain CLOSED.

## Follow-on work

After regression tests and guarded Git publication,
investigate genuinely distinct synthetic camera-style
measurement generation and its bias/noise assumptions
before making any claims about cross-modal redundancy.

Keep both the health-model inference gate and the
factor-conditioning gate closed.
