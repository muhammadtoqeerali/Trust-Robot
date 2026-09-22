# TRUST-ROBOT Phase-3 Corruption Selection Policy V1

## Purpose

This policy closes the provenance gap between a deterministic corruption
engine and the choice of which corruption instance that engine is allowed to
execute.

The engine is not permitted to choose its own corruption conditions.

## Prospective lock

Before a corruption instance is executed, the following must be explicit and
provenance-bound:

- the corruption mechanism;
- its target/location rule;
- its magnitude or duration;
- any family-specific parameters;
- scenario context;
- any threat-model identity required for an attack scenario;
- the source used to justify those selections.

The selection record is SHA-derived and immutable in interpretation after the
corresponding execution begins.

## Allowed target-selection sources

V1 recognizes:

- explicit pre-execution literal;
- deterministic TRAIN-metadata rule;
- external independent specification.

A TRAIN-metadata rule may identify a source location mechanically, but it may
not use reference errors, estimator outputs, or performance metrics.

## Allowed magnitude-selection sources

V1 recognizes:

- explicit pre-execution literal;
- external independent specification.

There is no default numeric corruption magnitude.

The corruption engine cannot invent one.

## Forbidden selection inputs

Corruption conditions cannot be selected using:

- estimator outputs;
- registration diagnostics;
- reference trajectories;
- reference error;
- ground-truth metrics;
- validation performance metrics;
- confirmation-test outcomes;
- ATE;
- RPE;
- final estimator scores.

This restriction concerns selection of the corruption experimental condition.

It does not redefine the separate estimator-hyperparameter or evaluation
protocol rules.

## Existing real EVENT_GAP smoke

The already-executed real TRAIN smoke is explicitly bound to this policy.

Its target rule was frozen before execution:

the first three Velodyne events formed the fixed mechanical slice, and event
index 1 was the unique internal event.

Its magnitude was also frozen before execution:

`length = 1`

as the minimal non-zero discrete EVENT_GAP mechanical smoke instance.

The subsequently observed registration outputs and diagnostics cannot change
that corruption specification.

## Scientific boundary

This policy:

- selects no new corruption severity;
- selects no attack budget;
- accesses no confirmation-test data;
- authorizes no reference evaluation;
- authorizes no ATE/RPE;
- changes no synchronization state;
- changes no M2DGR evaluation readiness.

It is a prospective experimental-control policy only.

Phase-3 exit evidence remains formally unsatisfied pending the final Phase-3
closure review.
