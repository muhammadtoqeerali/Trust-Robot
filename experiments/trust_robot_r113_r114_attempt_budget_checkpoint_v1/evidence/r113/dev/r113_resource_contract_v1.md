# R113 — Bounded synthetic replay and cancellation

## Scope

R113 wraps the validated R111 in-memory shadow
transaction interface.

The original S6, R107, R108, R110 and R111
source files are unchanged.

## Deterministic replay-work accounting

One work unit represents one candidate-buffer
packet submission.

A packet transaction uses:

    acknowledged_history_length + 1

A finalization uses:

    acknowledged_history_length

For this four-packet manufactured experiment,
the expected operation-work ledger is:

    [1, 2, 3, 4, 4]

Total permitted work per successful session: 14.

Maximum work per operation: 4.

These are replay-dispatch counts, not numerical
floating-point operation counts or measured time.

## Ownership

Each R113 session returns a local Python owner object.

Mutating public operations require identity equality
with this owner object and an exact expected version.

This is a single-process programming boundary.
It is NOT cryptographic authentication or
cross-process access control.

Private Python objects are not isolated.

## Cancellation

Cancellation is terminal.

Previously committed acknowledgements and estimator
state remain unchanged.

Further submit, finish and cancellation calls are denied.

Cancellation injected at the pre-publication hook
must prevent candidate publication and acknowledgement.

No concurrent-thread cancellation correctness is claimed.

## Failure and resource guarantees

Resource limits reject an operation before building
its candidate.

Injected solver failures do not consume committed
replay-work budget. Retries are permitted while
the session remains active.

The tests do not prove rollback after power loss,
persistent recovery, real-time deadlines, physical
memory limits, transport authentication, or
hardware-level fault recovery.

All measurements are manufactured synthetic data.

R95 Gaussian priors remain separate from S6.
No real sensor factors, health training, ATE/RPE,
raw GT/ROSBags or confirmation_test are authorized.

All 11 scientific gates remain CLOSED.
