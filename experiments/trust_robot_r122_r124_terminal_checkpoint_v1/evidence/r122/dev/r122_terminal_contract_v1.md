# R122 — Synthetic post-saturation terminal-path audit

## Objective

R120's bounded denial history rejects further
mutations when the receipt capacity is exhausted.

This includes normal cancellation and retirement,
which can leave a session active and unretired.

R122 evaluates a separate terminal-only pathway
without changing R120 or earlier source files.

## Terminal operations

Two explicit operations are permitted:

1. terminal_cancel:
   - Requires a live local session handle and owner.
   - Requires an exact integer committed version.
   - Requires an active session.
   - Cannot add, replay or execute sensor factors.
   - Cancels without changing previously committed
     estimator state or attempted-work reservations.

2. terminal_retire:
   - Requires the same local owner/handle.
   - Requires a cancelled session.
   - Requires a prior terminal-cancel receipt.
   - Enforces creation-order retirement before mutation.
   - Releases only the registry's active reference.

These operations directly invoke the previously
validated R117 registry lifecycle interface,
bypassing only the R120 denial-capacity check.

The ordinary R120 denial history remains unchanged
by terminal operations.

## Bounded terminal ledger

The terminal ledger permits at most two events
per created session: cancellation and retirement.

The maximum number of sessions is separately
bounded by the existing R116/R117 registry.

SHA-256-linked terminal receipts are checked
before further operations.

This is a logical event-count bound, not
preallocated physical RAM or persistent storage.

## Tested situations

- Receipt capacity fully exhausted.
- Ordinary estimator work blocked.
- Normal cancellation and retirement blocked.
- Explicit terminal cancellation succeeds.
- Explicit terminal retirement succeeds.
- Owner, handle, version and retirement-order checks.
- Preservation of a partially committed estimator.
- Charged repeated internal solver failures.
- Cancellation during candidate prepublication.
- Detached terminal audit observations.
- Accidental terminal receipt corruption rejection.
- Maximum 12 created and 12 retired sessions.

## Important limitations

A Python interpreter crash, memory allocation
failure, arbitrary callback exception, scheduler
failure, hostile in-process code, corrupted registry,
concurrent mutation or hardware failure may prevent
the terminal path from completing.

The tested terminal path is not an emergency stop,
independent watchdog, motor power cutoff,
certified safety controller or guaranteed shutdown.

The in-memory receipts are not authenticated,
signed or crash durable.

Original numerical S6 and R104-R120 sources
remain unchanged.

R95 Gaussian priors are not imported into S6.

All factor inputs are manufactured synthetic data.

No recorded camera, LiDAR or IMU factor execution,
physical extrinsic or clock qualification, health
training, independent ATE/RPE, original raw GT,
ROSBags or sealed confirmation_test access.

All 11 scientific gates remain CLOSED.
