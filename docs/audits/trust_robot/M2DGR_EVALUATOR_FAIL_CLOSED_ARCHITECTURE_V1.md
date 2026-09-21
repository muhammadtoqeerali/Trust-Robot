# M2DGR Evaluator Fail-Closed Architecture V1

## Purpose

This checkpoint begins evaluator implementation only after the permanent
reference-family protocol-boundary analysis established that metric-schema and
dimension-gating definition work is admissible while physical trajectory
evaluation remains blocked.

The implementation is deliberately fail-closed.

## Frozen inputs

The architecture consumes two frozen artifacts:

- `configs/trust_robot/m2dgr_trajectory_association_evaluation_protocol_candidate_v2.json`
- `manifests/m2dgr_reference_family_protocol_boundary_evidence_v1.json`

Neither artifact is modified by this implementation checkpoint.

Protocol V2 remains:

- temporal association method: `unselected`;
- association tolerance: `null`;
- fixed reference offset: `null`;
- interpolation method: `unselected`;
- evaluation interval: `unselected`;
- frame alignment mode: `unselected`;
- metric computation authorized: FALSE;
- trajectory scoring authorized: FALSE;
- estimator scoring authorized: FALSE;
- dataset calibration verified: FALSE;
- synchronization verified: FALSE;
- evaluation ready: FALSE.

## Implementation

`src/trust_robot/m2dgr_evaluator_gate.py` introduces:

- a validator for the permanent reference-family protocol-boundary artifact;
- immutable metric-family definition objects;
- immutable family/dimension gate objects;
- immutable metric gate objects;
- `M2DGRFailClosedEvaluationGate`;
- explicit blocking exceptions for metric execution and estimator scoring.

The implementation exposes the four metric-family definitions already present
in frozen Protocol V2:

- ATE translation;
- ATE rotation;
- RPE translation;
- RPE rotation.

Exposing a metric definition does not enable or compute that metric.

## Dimension gating

The gate preserves the frozen family structure:

- RTK/INS translation: structurally present;
- RTK/INS rotation: structurally present;
- Leica translation: structurally present;
- Leica rotation: structurally unsupported;
- mocap translation: structurally present;
- mocap rotation: structurally present but containing 1274 audited invalid
  quaternion samples.

For every family and metric, execution remains unauthorized under frozen
Protocol V2.

## Deliberately absent execution code

This checkpoint contains no implementation for:

- exact timestamp trajectory association;
- nearest-neighbor trajectory association;
- reference interpolation;
- time-offset estimation;
- lag search;
- evaluation-interval creation;
- SE(3) alignment;
- Sim(3) alignment;
- no-alignment trajectory comparison;
- ATE computation;
- RPE computation;
- metric aggregation;
- trajectory scoring;
- estimator ranking/scoring.

The gate accepts no estimator trajectory arrays and performs no trajectory
mathematics.

## Fail-closed behavior

Requests to execute a metric raise `M2DGRMetricExecutionBlocked`.

Requests to authorize estimator scoring raise
`M2DGREstimatorScoringBlocked`.

Changing a copy of the frozen boundary artifact to mark any current
family/dimension scoring-admissible causes validation failure even if its
content digest is recomputed.

Changing a copy of Protocol V2 to enable a metric also causes validation
failure.

## Confirmation-test protection

This implementation does not read raw confirmation-test trajectories.

It does not choose any association, alignment, threshold, offset, interval,
filter, or metric operating rule from confirmation-test data.

## Scientific status

This is evaluator plumbing, not evaluation.

No ATE value is produced.

No RPE value is produced.

No estimator-performance claim is produced.

Physical evaluation remains blocked pending genuinely new evidence or a
separately preregistered scientific objective/protocol.
