# R110 — Synthetic failure atomicity and fail-stop

## Scope

A guarded session wraps the R108 bounded-delivery
buffer and its R107 nonlinear fixed-lag estimator.

The underlying numerical code is unchanged.

## Failure stages

Deterministic injected exceptions are introduced at:

1. Synthetic IMU prediction.
2. Nonlinear least-squares optimization.
3. Schur marginalization.
4. Same-graph prior recentering.
5. After internal processing but before acknowledgement.
6. Finalization.

These injections are software instrumentation only.

## Fail-stop rule

Before admission, invalid packets are rejected without
changing queue or estimator state. The session stays active.

An exception during internal processing marks the session
FAULTED and records pre/post state observations.

All subsequent submit and finish operations through
the guarded session are rejected.

No acknowledgement of the failed operation is issued.

Recovery is demonstrated only by creating an entirely
fresh estimator and delivery buffer and replaying the
manufactured experiment.

## Important limitations

R107/R108 are not transactionally atomic after an
internal solver exception.

The guarded wrapper does not implement numerical
rollback or restore the prior estimator state.

A synthetic post-processing acknowledgement failure
illustrates ambiguity between internal completion
and client-visible success.

In-process Python objects are not protected against
direct access or external mutation.

The test is not crash recovery, process isolation,
persistent journal recovery or distributed
exactly-once delivery.

The graph is synthetic, not hardware streaming.

No real sensor factors, physical capture clocks,
extrinsics, calibrated health training, independent
ground truth scoring, ATE/RPE or confirmation-test use.

R95 Gaussian priors are not imported into S6.

All 11 scientific gates remain CLOSED.
