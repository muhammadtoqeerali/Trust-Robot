# M2DGR Non-Executable Evaluation Plan V1

## Purpose

This checkpoint adds deterministic provenance-record and evaluation-plan
objects on top of the promoted fail-closed evaluator gate.

The plan is descriptive only.

It does not execute trajectory evaluation.

## Bound provenance

The plan binds:

- frozen Evaluation Protocol V2;
- permanent reference-family protocol-boundary evidence;
- frozen split manifest;
- split-freeze evidence;
- promoted fail-closed evaluator-gate implementation.

Bindings record repository-relative path and SHA256.

Logical content hashes are also retained where the frozen JSON artifacts expose
them.

## Required per-evaluation provenance

Protocol V2 already defines the provenance that a future executable evaluation
would have to supply, including trajectory identities, frame IDs, measurement
time basis, association method/tolerance, fixed offset, interpolation method,
evaluation interval source, alignment mode/source, metric dimension, validity
artifact, protocol digest, and split role.

This checkpoint records those requirements.

It does not fabricate their future per-trajectory values.

Accordingly:

- per-trajectory provenance values populated: FALSE;
- estimator trajectory bound: FALSE;
- reference trajectory bound: FALSE;
- raw confirmation-test data accessed: FALSE.

## Non-executable plan

The plan records the currently frozen choices exactly:

- association method: `unselected`;
- association tolerance: `null`;
- fixed reference-to-estimator offset: `null`;
- interpolation method: `unselected`;
- evaluation interval: `unselected`;
- alignment mode: `unselected`.

It contains twelve family/metric entries:

- three reference families;
- four Protocol V2 metric definitions per family.

Metric definitions remain visible as schema metadata.

Every metric remains disabled.

Every execution authorization remains FALSE.

Every scoring authorization remains FALSE.

## Confirmation-test protection

The confirmation-test partition remains closed to selection.

The plan does not inspect confirmation-test raw trajectories.

The plan does not use confirmation-test outcomes.

## Deliberately absent data and computation

The plan contains no estimator trajectory array.

The plan contains no reference trajectory array.

It does not perform:

- exact timestamp association;
- nearest-neighbor association;
- interpolation;
- lag search;
- fixed-offset estimation;
- interval construction;
- SE(3) alignment;
- Sim(3) alignment;
- ATE computation;
- RPE computation;
- aggregation;
- trajectory scoring;
- estimator scoring.

## Tamper resistance

Plan validation rejects attempts to change an execution flag, select an
association method, or mark confirmation-test raw data as accessed, even if the
plan content digest is recomputed.

## Scientific status

This checkpoint improves reproducibility plumbing only.

Physical evaluation remains blocked.

Protocol V2 remains byte-identical.

The permanent reference-family boundary remains byte-identical.

No estimator-performance claim is produced.

## Immutable plan artifact handling

The non-executable plan now provides deterministic immutable JSON artifact
writing and validated loading.

An identical plan may be written repeatedly.

An existing artifact may not be overwritten with different logical content.

Loading always revalidates the plan digest and all fail-closed semantics.

This persistence layer stores plan metadata only. It does not store estimator or
reference trajectory samples.

## Provenance completeness diagnostics

`src/trust_robot/m2dgr_evaluation_readiness.py` adds field-name completeness
diagnostics for the 17 provenance fields required by Protocol V2.

The diagnostic accepts field names only, not provenance values.

Therefore it cannot select or invent:

- an association method;
- a tolerance;
- a time offset;
- an interpolation policy;
- an evaluation interval;
- an alignment mode;
- a frame transform.

A complete set of provenance field names means only that the required schema
names are present.

It does not establish that the corresponding values are physically or
scientifically valid.

## Execution-readiness diagnostics

The readiness diagnostic exposes the currently frozen authorization state and
remaining blockers.

Even when all 17 required provenance field names are present:

- provenance semantic verification remains FALSE;
- executable metric count remains 0;
- scoreable metric count remains 0;
- evaluation readiness remains FALSE.

`require_execution_ready()` therefore fails closed under the current frozen
Protocol V2.

## Metadata-only evaluation inspection

The local evaluator-plumbing phase now includes a metadata-only
family/metric inspection interface:

`src/trust_robot/m2dgr_evaluation_request.py`

and a local inspection CLI:

`scripts/trust_robot/inspect_m2dgr_evaluation_readiness.py`

An inspection request carries only:

- reference-family name;
- metric-family name;
- optional names of provenance fields said to be present.

The request does not accept:

- estimator trajectory identity or path;
- reference trajectory identity or path;
- trajectory samples;
- timestamps;
- an association tolerance;
- a fixed time offset;
- an interpolation policy;
- an evaluation interval;
- a frame transform;
- an alignment value;
- metric values.

The request therefore cannot be used to select or execute the unresolved
physical evaluation choices.

## Human-readable blocked-state report

The inspection report exposes:

- structural metric support;
- metric enabled state;
- execution/scoring authorization;
- provenance field-name completeness;
- provenance semantic-verification state;
- the still-unselected execution contract;
- confirmation-test closure;
- global and metric-specific blockers.

A report always ends in `RESULT: BLOCKED` under current Protocol V2.

Even a request declaring all 17 required provenance field names present remains:

- provenance semantics verified: FALSE;
- metric execution authorized: FALSE;
- metric scoring authorized: FALSE;
- evaluation ready: FALSE.

The CLI is diagnostic only. It loads no trajectory samples and computes no
trajectory metric.

## Cross-layer integration and phase consolidation

The local evaluator-plumbing phase now includes an end-to-end integration
suite spanning:

- frozen Protocol V2;
- permanent reference-family protocol boundary;
- fail-closed evaluator gate;
- non-executable plan construction;
- immutable plan persistence;
- provenance field-name diagnostics;
- execution-readiness diagnostics;
- metadata-only family/metric inspection.

The integration suite verifies all twelve family/metric pairs twice:

1. with no provenance field names supplied;
2. with all seventeen required provenance field names supplied.

In both cases every metric remains execution-blocked and scoring-blocked.

The integration suite also verifies that Leica rotation remains structurally
unsupported and that the confirmation-test partition remains closed.

A tamper matrix attempts to change association, tolerance, alignment,
metric execution, metric scoring, global metric authorization,
confirmation-test access, estimator/reference trajectory binding, and metric
value production.

All such modified plans must be rejected even when their logical content
digest is recomputed.

## Staged phase artifacts

The final local consolidation generates deterministic staging artifacts under
the dataset audit area rather than the Git repository.

These staging artifacts contain:

- the immutable non-executable evaluation plan;
- a deterministic inspection matrix for all family/metric pairs;
- a local phase manifest binding the frozen inputs and current implementation
  component hashes.

They contain no trajectory samples and authorize no evaluation.
