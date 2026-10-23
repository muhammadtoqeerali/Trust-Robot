# R119 — Synthetic audit observation and failure receipts

## Scope

R119 wraps the SHA-pinned R117 synthetic registry.

R116, R117 and all previous numerical estimator and
factor graph sources remain unchanged.

## Read-only observations

The new facade exposes detached diagnostic snapshots
of registry counts, session phase, accepted version,
attempted replay units, committed replay units, and
a diagnostic committed-state digest.

Observations never deliberately serialize local
owner objects, opaque lease objects, raw sensor
packets or manufactured factor measurements.

Mutating an observation returned to the caller
does not mutate the authoritative underlying registry.

## Rejected operation receipts

A rejected or aborted mutation creates a bounded,
structured diagnostic record containing:

- Local ordinal number and operation name.
- Allowlisted denial reason.
- No successful acknowledgement.
- Observed before and after state, when available.
- Reserved attempted-work units charged.
- Prior receipt digest and current linked digest.

Invalid packet admission is rejected before work
reservation and incurs zero attempted-work units.

Numerical candidate failures consume attempted-work
budget but do not publish a committed estimator update.

An exhausted attempt budget denies the next candidate
without charging an additional reservation.

Cancellation during prepublication is recorded as an
aborted candidate with charged attempted work and no
successful acknowledgement.

## Integrity scope

The registry checks the linked in-memory failure
receipts before subsequent operations.

Two return-copy isolation checks and one internal
receipt corruption control are exercised.

The SHA-256 links have no signed external root and
do not establish authenticated provenance, secure
logging, durability, or malicious in-process
tamper resistance.

Private Python object access is not isolated.

No concurrent thread execution is tested.

## Scientific limits

All numerical factors are manufactured analytic
synthetic measurements.

Original S6/R107-R117 implementations are unchanged.

R95 priors remain incompatible with and separate
from the S6 30D same-graph Schur priors.

No recorded sensor factors, physical clock qualification,
extrinsic calibration, raw GT/ROSBags, health training,
ATE/RPE scoring or confirmation_test access.

All 11 scientific gates remain CLOSED.
