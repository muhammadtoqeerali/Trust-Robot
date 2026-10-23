# R116 — Synthetic session lifecycle and fault patterns

## Engineering objective

Extend R114's failure-charged synthetic shadow
transaction interface with a bounded session registry.

The original S6, R107, R108, R110, R111,
R113 and R114 sources are unchanged.

## Session lifecycle

Each session has:
- A monotonically issued local handle.
- An owner identity object.
- A bounded attempted-work budget.
- Explicit ACTIVE, COMPLETED or CANCELLED state.
- An explicit terminal retirement operation.

The registry has a maximum active-session count
and a maximum cumulative creation count.

A retired handle is never reused.

Retirement removes the registry's active reference
and preserves a bounded lightweight receipt.

This does not demonstrate physical memory release,
garbage collection, process isolation or secure erasure.

## Fault patterns

Test:
- Two interleaved active synthetic sessions.
- Ordered and bounded-reordered packet releases.
- Ordinary and recentered nonlinear solver modes.
- Three manufactured graph scenarios.
- Two-slot active capacity exhaustion.
- Monotonic handle creation limits.
- Retired-handle rejection.
- Invalid and cross-graph packet delivery.
- Stale versions and wrong owners.
- Repeated solver failures with charged attempts.
- Attempt exhaustion without harming another session.
- Cancellation during candidate prepublication.
- Eventual healthy completion after admission rejection.

The interleaving is single-threaded and deterministic.

No concurrent thread safety, scheduling fairness,
deadlock freedom or distributed isolation is proven.

## Scientific limits

Attempted work measures replay-dispatch reservations,
not wall-clock execution time, physical RAM,
energy, CPU resource bounds or real-time deadlines.

Local owner objects are not authenticated credentials.

No hardware streaming or recorded sensor factor
execution is authorized.

R95 Gaussian priors are not merged with S6.

No physical synchronization or extrinsics,
health training, GT access, ATE/RPE or sealed
confirmation-test access is authorized.

All 11 scientific gates remain CLOSED.
