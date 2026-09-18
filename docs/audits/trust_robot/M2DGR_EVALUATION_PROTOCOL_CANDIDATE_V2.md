# M2DGR Trajectory Association and Evaluation Protocol Candidate V2

## Status

`blocked_pending_physical_evidence`

V2 is bound to the frozen prospective M2DGR split:

- train: 22
- validation/calibration: 7
- confirmation test: 7

The existence of a validation/calibration partition removes the earlier
"no validation split" blocker. It does **not** establish any missing physical
fact and does not by itself authorize evaluation.

## Key distinction

A validation/calibration partition is now available for future data-selected
protocol parameters.

However, a data split cannot establish:

- what physical measurement event a reference timestamp represents;
- whether reference time and estimator sensor time are physically synchronized;
- the reference sensor/body origin;
- the reference-to-estimator frame transform;
- missing extrinsic calibration;
- continuous reference validity.

Those remain evidence questions rather than tunable parameters.

## Temporal association

Selection partition: `validation_calibration`

Selection partition available: true

Selection authorized now: false

Selected method: `unselected`

Association tolerance: `null`

Fixed offset: `null`

Interpolation: `unselected`

Nearest-neighbor association remains unauthorized.

Reference interpolation remains unauthorized.

Confirmation-test data may not select any association parameter.

## Evaluation interval

No evaluation interval is created.

Numeric timestamp overlap, header-range intersections, and sample-run endpoints
are not promoted to evaluation coverage.

## Alignment

Candidate modes remain:

- none
- SE(3) rigid
- Sim(3) similarity

Selected mode: `unselected`

A future data-selected alignment convention would use only the
validation/calibration partition, but alignment selection is not currently
authorized because reference-frame/origin semantics remain unresolved.

Sim(3) requires an explicit scale-gauge justification.

Confirmation-test error may not select alignment.

## Metrics

ATE translation, ATE rotation, RPE translation, and RPE rotation are named but
remain disabled.

Leica remains translation-only.

Mocap invalid rotation samples may not be silently repaired or scored.

RPE delta and aggregation policies remain unselected.

## Current blockers

The frozen split does not resolve temporal association, reference frame/origin,
calibration, LiDAR effective scan time, mocap rotation quality, Leica rotation,
or alignment policy.

Estimator scoring remains unauthorized.

Evaluation readiness remains false.

Content SHA256:

`8f60fa3a2303d6a2b8ad8d74719439358e2f7b19ca834c77e6cf09aa1889efbc`
