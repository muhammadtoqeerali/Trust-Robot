# R114 — Failure-charged synthetic replay budget

## Engineering objective

Extend the R113 deterministic candidate replay
accounting to include failed transaction attempts.

The original S6/R107/R108/R110/R111/R113
implementations remain unchanged.

## Attempt reservation

A packet submission reserves:

    previously acknowledged packet count + 1

Finalization reserves:

    previously acknowledged packet count

The reservation is charged before constructing
the next candidate.

Reservations are not refunded if a candidate
fails during prediction, nonlinear optimization,
Schur marginalization, prior recentering,
prepublication validation, or finalization.

## Resource exhaustion

Once the attempt budget is exhausted, further
candidate executions are denied before execution.

Invalid packet admissions, wrong local owners,
and stale expected versions are rejected before
reserving work.

Repeated solver failures must therefore consume
the finite attempt budget.

The prior committed estimator remains unchanged
after a failed shadow candidate.

## Cancellation

An owner may cancel an active session.

Cancellation before publication prevents candidate
publication while preserving the attempted-work
reservation.

A cancelled session is terminal.

## Evidence scope

Replay work units measure predicted counts of
candidate-buffer packet submissions.

Actual candidate dispatches are instrumented
for representative successful and failed cases.

They do not constitute wall-clock latency,
floating-point operation, physical RAM, energy,
thermal, CPU scheduling or real-time guarantees.

The work ledger is in-memory, not crash durable.

The local owner is Python object identity,
not cryptographic authentication.

No concurrent execution, process isolation or
distributed exactly-once guarantee is claimed.

All factor observations are manufactured synthetic
inputs from the established R104 graph.

R95 Gaussian prior import remains denied.

No recorded sensor factors, independent GT ATE/RPE,
health training, original ROSbags, or frozen
confirmation_test are authorized.

All 11 scientific gates remain CLOSED.
