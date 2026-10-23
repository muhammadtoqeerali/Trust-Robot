# R120 — Synthetic failure receipt and audit-chain hardening

## Objective

R120 extends the unchanged R119 observation facade.

It makes additional consistency and lifecycle
checks around the R117 in-memory retirement ledger.

## Semantic failure receipt verification

All recorded denials must report:
- No successful acknowledgement.
- An allowlisted denial reason.
- Unchanged committed version, state digest and
  committed-work units when a session is known.
- An attempted-work delta matching the receipt.
- Positive attempted work for an aborted candidate.
- Zero attempted work for other denied operations.

Unknown handle receipts have no session snapshot.

The checks operate on in-memory Python data and
are not authenticated evidence.

## Retirement-order admission

The R117 linked retirement ledger expects terminal
retirements in session creation order.

R120 checks that precondition before calling the
underlying R117 retirement operation.

An out-of-order retirement is denied before it
can mutate the underlying registry.

A linked local policy receipt records the denial.

This is a software precondition guard, not a
concurrency-proof ordering protocol.

## Bounded denial history

A configurable maximum of 1 to 16 denial receipts
is enforced.

At the configured limit, additional mutating
operations fail closed before reaching the
underlying estimator.

The overflow rejection count remains observable,
but individual overflow attempts are not archived
as separate receipts.

Importantly, this includes cancellation and
retirement: a saturated session may remain active
and unretired.

R120 therefore does not guarantee liveness or
emergency shutdown after receipt saturation.

## Source integrity and scientific limits

All original R119, R117, R116, R114 and numerical
estimator sources remain unchanged.

The tests use manufactured analytic synthetic
factors, not recorded physical measurements.

The SHA-256 receipt links are not authenticated,
not durable, not externally anchored, and not
secure against privileged in-process modification.

No concurrent thread safety, hardware timing,
physical RAM bounds or real fault recovery is claimed.

R95 Gaussian priors remain separate from S6.

No recorded camera, LiDAR or IMU factor execution,
physical synchronization, extrinsics, health training,
ATE/RPE, raw GT/ROSBags or confirmation_test access.

All 11 scientific gates remain CLOSED.
