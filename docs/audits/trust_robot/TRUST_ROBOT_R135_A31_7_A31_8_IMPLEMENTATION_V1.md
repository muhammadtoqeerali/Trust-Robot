# TRUST-ROBOT R135-A31-7 / A31-8 Implementation

## Engineering scope

Implement deterministic multi-step synthetic 15D state
prediction and controlled measurement dropout/recovery.

Add descriptive synthetic truth-error diagnostics.

These experiments do not qualify physical measurements.

## A31-7 synthetic trajectory prediction

The toy state is fifteen-dimensional.

The first three coordinates represent abstract position.
Coordinates 3-5 represent abstract velocity.

The remaining coordinates stay constant during prediction.

A declared constant-velocity transition matrix propagates
the state and covariance.

A synthetic acceleration process-noise model is added.

Covariance propagation uses F P F^T + Q.

A Joseph-form synthetic Kalman update may follow prediction.

Four separate toy policies are evaluated:
counterfactual all-candidate updating, NIS-only
counterfactual updating, scheduled delivery-only updating,
and combined synthetic screening.

Counterfactual updates on undelivered candidates are
deliberate simulation controls, not realizable
physical sensor operations.

## A31-8 synthetic consistency

The diagnostic uses a declared synthetic 15D truth state.

NEES is computed with the full toy covariance.

Toy position RMSE is calculated over the declared
synthetic truth sequence.

A single toy trajectory cannot demonstrate statistical
calibration or physical localization accuracy.

Five pinned A29-4 simulated software scenarios are reviewed.

A separate six-step synthetic measurement schedule
contains two planned dropouts followed by recovery.

This schedule is not inferred from actual ROS event times.

## Scientific restrictions

- M2DGR admission gates: 11 CLOSED.
- Real physical factor admission: DENIED.
- Independent qualifying receipts: 0 of 13.
- Physical BMI088 frame relationship: UNVERIFIED.
- Physical clock accuracy: UNVERIFIED.
- Metric physical calibration: UNVERIFIED.
- Independent six-DoF reference: UNVERIFIED.
- Real localization accuracy: NOT ESTABLISHED.
- Physical health probabilities: NOT GENERATED.
- Real factor weights: NOT GENERATED.

The frozen M2DGR split remains 22 training,
7 validation-calibration and 7 confirmation-test.

No real sensor observation model is executed.
No physical robot state is updated.
No robot motion, sensor recording or Git publication occurs.
