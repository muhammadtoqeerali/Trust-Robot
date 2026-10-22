# R111 — In-memory shadow-state transaction boundary

## Goal

Prevent an injected numerical failure in R107/R108
from mutating the committed state exposed through
a new R111 session interface.

## Implementation

For each synthetic packet admission:

1. Validate the packet against the existing graph.
2. Construct a new R108 candidate buffer.
3. Replay previously acknowledged packets.
4. Apply the candidate packet.
5. Verify completion of the candidate operation.
6. Publish the candidate as committed state.
7. Return a successful local acknowledgement.

If an exception occurs before publication,
discard the candidate. The prior committed
buffer and acknowledgement version remain
unchanged.

The same principle applies to finalization.

## Tests

Exercise:
- Three manufactured graph scenarios.
- Ordinary and recentered estimator modes.
- Ordered and bounded-reordered arrivals.
- Six injected internal failure stages.
- Failure before publishing a completed candidate.
- Retry after restoring ordinary execution.
- Invalid packet admission and duplicate rejection.
- Factor ownership and numerical S6 equivalence.

## Limitations

This is single-threaded in-process shadow-state
isolation, not durable transactional storage.

The implementation replays prior packets and
does not establish bounded runtime latency.

There is no crash/power-loss recovery, persistent
journal, concurrency isolation, distributed
exactly-once guarantee, authenticated network
transport, or protection against direct mutation
of internal Python objects.

Earlier R108 buffers are not retroactively made
transactional. R110 demonstrated that they may
mutate before numerical failures.

The SHA-256 acknowledgement is a local state
correlation digest, not source authentication.

All sources are manufactured analytic measurements.

R95 Gaussian priors remain separate from S6.
No recorded sensor factors are authorized.

No health training, physical sensor calibration,
ground-truth ATE/RPE or confirmation-test access.

All 11 scientific gates remain CLOSED.
