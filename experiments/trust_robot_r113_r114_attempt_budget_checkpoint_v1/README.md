# TRUST-ROBOT R113-R114 replay resource checkpoint

Date: 2026-10-22.

Parent Git commit:
eed9d62ba424b0e136d8307b738059bab7c5e44a

## R113 — Bounded synthetic replay and cancellation

47 regression tests passed.

R113 added deterministic candidate-replay dispatch
accounting to the previously validated R111
in-memory shadow transaction interface.

Across 12 healthy manufactured sessions:

- 60 committed operations.
- 168 replay work units.
- 14 work units per completed session.
- Maximum four work units per operation.
- Exact replay dispatch-count witness.

Validated:
- Local owner-object identity.
- Explicit expected-version checking.
- Budget rejection before candidate work.
- Cancellation of active sessions.
- Cancellation at the pre-publication boundary.
- Preservation of previously committed state.
- Recovery after injected solver failure.

The work count represents candidate packet dispatches.
It is not measured CPU time, memory, energy or FLOPs.

## R114 — Failure-charged replay attempt budget

54 regression tests passed.

R114 extends R113 with an attempt budget that charges
reserved candidate work even when the candidate fails.

It verified:

- 12 healthy manufactured sessions.
- 168 attempted units and 168 committed units
  across healthy sessions.
- Six injected failure stages.
- Six charged failed candidates.
- Six successful retries after fault removal.
- Repeated-failure budget exhaustion.
- Rejection of further execution after exhaustion.
- Cancellation without refunding reserved work.
- No replay charge for invalid pre-admission packets.

A work reservation is a conservative bound on the
expected candidate packet dispatch count for the
tested manufactured graph.

## Scientific boundaries

These results do not establish:

- Real-time execution deadlines.
- Physical RAM or energy limits.
- Floating-point computational complexity bounds.
- Concurrent or multiprocess atomicity.
- Durable transaction journals or crash recovery.
- Cryptographically authenticated owner identity.
- Distributed exactly-once sensor delivery.
- Actual hardware fault recovery.

R95 Gaussian priors were not merged into S6.

The original S6, R107, R108, R110, R111 and
R113 implementation sources remain unchanged.

All measurements are manufactured synthetic inputs.
No recorded camera, LiDAR or IMU factors are admitted.

No physical clock or extrinsic calibration,
independent ground-truth ATE/RPE, health training,
original ROSbags, or sealed confirmation-test
access is authorized.

All 11 scientific gates remain CLOSED.

## Standalone verification

python3 -B experiments/trust_robot_r113_r114_attempt_budget_checkpoint_v1/verify_checkpoint.py verify experiments/trust_robot_r113_r114_attempt_budget_checkpoint_v1
