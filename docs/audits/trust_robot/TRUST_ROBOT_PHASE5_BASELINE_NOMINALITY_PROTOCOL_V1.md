# TRUST-ROBOT Phase-5 Prospective Baseline-Nominality Protocol V1

## Finding that motivates this layer

The existing M2DGR evidence base contains no accepted independent
interval-bound LiDAR nominality source.

In particular:

- clean source identity is insufficient;
- source byte integrity is insufficient;
- frontend admissibility is insufficient;
- registration success is insufficient;
- Phase-4 diagnostics are prohibited as nominality proof;
- no released TRAIN LiDAR status stream exists;
- the manufacturer manual does not observe the actual M2DGR runtime interval.

## Prospective source shape

A future VLP-32C baseline-nominality candidate must bind:

- exact source measurement identity and digest;
- acquisition-session identity;
- measurement-interval identity;
- raw operational-status evidence and digest;
- an explicit interval-binding receipt;
- a no-deliberate-availability-intervention receipt.

## Manufacturer-grounded positive operational evidence

The prospective candidate requires discrete manufacturer-documented states:

- Motor State = `ON`;
- Laser State = `ON`;
- Thermal Status = `Ok`.

These are operational evidence requirements.

They are not numeric diagnostic thresholds.

They do not make the manufacturer manual itself a runtime receipt.

A candidate satisfying these requirements is still not automatically an
accepted health-supervision source.

## Interval binding

The operational-status observation must be bound to the source measurement
interval by explicit provenance.

This protocol does not invent:

- a timestamp tolerance;
- a fixed timestamp offset;
- interpolation;
- nearest-neighbor temporal association.

The concrete interval-binding mechanism remains unselected.

## Anti-leakage and independence

A candidate must be independent of:

- Phase-4 diagnostic values;
- final estimator scoring;
- reference trajectory performance;
- confirmation-test data.

Confirmation-test data are outside the candidate split vocabulary.

## Current status

No prospective acquisition mechanism has been selected.

No interval-binding mechanism has been selected.

No candidate nominality receipt exists.

Accepted baseline-nominality sources: **0**.

Accepted health-supervision sources: **0**.

Real health labels: **0**.

Controlled corruption generation remains unauthorized.

Health-label generation remains unauthorized.

Classifier training remains unauthorized.

Phase-5 exit evidence remains **NOT YET SATISFIED**.
