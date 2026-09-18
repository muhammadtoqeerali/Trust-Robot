# M2DGR Trajectory Association and Evaluation Protocol Candidate V1

## Status

`blocked_pending_evidence`

This candidate defines the structure of a future trajectory-evaluation protocol
without authorizing trajectory scoring.

It deliberately does not select:

- reference interpolation;
- nearest-neighbor pose association;
- an association tolerance;
- a fixed reference-to-estimator time offset;
- an evaluation interval;
- SE(3) alignment;
- Sim(3) alignment;
- metric aggregation;
- an RPE delta definition.

## Frozen source checkpoint

`c802b01bc2d1b521cf2098860172eb4da899ec74`

## Current dataset state

- trajectories: 36
- train: 36
- validation_calibration: 0
- confirmation_test: 0
- reference frames recorded as `unknown`: 36
- RTK/INS references: 16
- Leica references: 11
- mocap references: 9
- translation-only references: 11
- translation+rotation references: 25
- mocap trajectories with structurally invalid rotation samples: 9

## Candidate metric families

The candidate names four metric families but keeps all disabled:

- translation ATE
- rotation ATE
- translation RPE
- rotation RPE

Metric naming does not authorize computation.

Translation and rotation remain dimension-gated independently. Leica cannot
support rotation metrics. Structurally invalid mocap rotation samples may not
be silently repaired or scored.

## Temporal association

Selected method: `unselected`

Candidate concepts are exact numeric identity, nearest-neighbor association,
and reference interpolation, but none is authorized by the current evidence.

Association tolerance: `null`

Fixed reference offset: `null`

Interpolation method: `unselected`

The Phase-3E permanent evidence remains authoritative.

## Evaluation interval

Selected policy: `unselected`

No numeric header-range intersection, reference/sensor numeric overlap, or
sample-run endpoint is promoted to an evaluation interval.

## Frame alignment

Selected mode: `unselected`

Candidate modes are:

- none
- SE(3) rigid alignment
- Sim(3) similarity alignment

The candidate does not select among them.

All 36 reference frames remain `unknown`; reference-frame semantics and
reference-to-estimator transforms are not independently verified.

Sim(3) additionally requires an explicit estimator scale-gauge justification
and may not be selected merely because it improves test error.

## Selection policy

Any future data-selected association, alignment, or metric operating choice
must be selected only on a nonempty `validation_calibration` partition.

The current M2DGR manifest has no such trajectories.

Confirmation-test data may never select protocol choices.

The current all-training cohort may not be used to invent the blocked choices.

## Current authorization

Allowed now:

- protocol-schema definition;
- metric-family naming;
- dimension gating;
- provenance requirements;
- validation-only selection rules.

Not authorized now:

- estimator scoring;
- trajectory scoring;
- metric computation;
- association execution;
- alignment execution;
- nearest-neighbor association;
- reference interpolation;
- evaluation-interval creation;
- current-data protocol selection.

Evaluation readiness remains false.

Content SHA256:

`cc4400dbdb4726244be39eda42d9870e4ba5917560be66debc46f10e71e2b72a`
