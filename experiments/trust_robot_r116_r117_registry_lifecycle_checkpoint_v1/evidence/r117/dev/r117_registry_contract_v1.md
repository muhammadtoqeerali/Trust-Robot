# R117 — Synthetic session registry lifecycle hardening

## Scope

R117 wraps the unchanged R116 bounded session pool.

The numerical estimator and synthetic factor graph are
unchanged from their pinned previous checkpoints.

## Opaque local handles

Each opened session receives a distinct built-in Python
object used as a local handle.

A previous handle cannot address another local registry,
even if the underlying registries happen to issue the
same printable R116 handle such as S0001.

Owner identity and expected version remain required.

This is object identity within one Python interpreter,
not authentication, secrecy, authorization across
processes, or protection from malicious Python code.

## Retirement ledger

Each completed or cancelled session is explicitly
retired.

A small terminal receipt records its phase, version,
attempted work, committed work and committed-state
diagnostic digest.

Retirement receipts are linked using SHA-256.

The registry checks both its linked receipt chain
and the corresponding underlying R116 retirement
receipts before further operations.

Injected accidental modification of each copy is
detected and prevents subsequent admissions.

This hash linkage has no external authenticated root,
persistent storage, signed timestamp, or crash recovery.

Anyone permitted to modify private Python state may
rewrite or destroy the ledger. It is not tamper-proof
against a malicious in-process actor.

## Tests

- Twelve manufactured solver sessions.
- Pairwise single-threaded event interleaving.
- Ordered and bounded-reordered packet delivery.
- Ordinary and recentered local Schur priors.
- Synthetic S6 numerical equivalence.
- Two-slot registry capacity and cumulative limit.
- No retired or cross-registry handle reuse.
- Invalid packet and wrong-owner admission rejection.
- Two accidental retirement-record corruption controls.
- Charged repeated solver failures and peer isolation.
- Cancellation before candidate publication.
- Terminal retirement without successful acknowledgement.

## Scientific boundary

There is no claim of actual concurrent thread safety,
durable journals, secure audit logs, authenticated packet
or user identity, physical memory reclamation, resource
deadline guarantees, or physical streaming recovery.

All factor observations remain manufactured synthetic
data. No direct R95 Gaussian prior import into S6.

No recorded camera, LiDAR or IMU factors, health
training, independent physical ATE/RPE, raw GT,
original ROSbags, or sealed confirmation_test access.

All 11 scientific gates remain CLOSED.
