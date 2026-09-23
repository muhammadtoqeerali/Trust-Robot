# TRUST-ROBOT Phase-5 Health Supervision Protocol V1

## Purpose

The Phase-5 semantic layer defines `healthy`, `degraded`, and `unusable`.

The subsequent provenance audit found no accepted supervision source capable
of assigning those states to real records.

This layer prospectively defines what a candidate supervision source must
provide before any source can be considered for acceptance.

It accepts no source and assigns no label.

## Required source declaration

A future candidate source must explicitly declare:

- source identity;
- modality;
- measurement role;
- source kind;
- evidence description;
- protocol version;
- supported health states;
- a documented criterion for every supported state.

The declaration must be prospective.

## Scientific admissibility

Candidate evidence must be grounded in the modality's declared measurement
role.

It must be independent of:

- final estimator scoring;
- confirmation-test outcomes.

The following are insufficient as sole health supervision:

- clean-branch identity;
- corruption identity;
- diagnostic values;
- diagnostic thresholds.

The following are prohibited health-label bases in this protocol:

- reference-trajectory metrics;
- ATE/RPE;
- inherited `imu_reliability` policy;
- a classifier's own output.

## Candidate versus accepted source

Passing the source-shape validator does **not** accept the source.

It only demonstrates that the declaration satisfies the prospective protocol
shape and exclusion rules.

This layer intentionally implements no source-acceptance API.

Current accepted supervision-source count:

**0**

Current real health-label count:

**0**

## Phase separation

This protocol does not:

- select classifier structure;
- select diagnostic features;
- select thresholds;
- train a model;
- calibrate a model;
- assign a real health state;
- authorize factor weighting;
- authorize modality suppression.

The frozen Phase-4 diagnostic feature contract remains unchanged.

## Current frontier

A subsequent evidence-specific step must identify a concrete candidate
supervision source and justify it against this protocol.

Only after a source is explicitly reviewed and accepted can a separate layer
define label receipts or classifier-training data.

Phase-5 exit evidence remains **NOT YET SATISFIED**.
