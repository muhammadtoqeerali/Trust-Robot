# R126-D — Cooperative single-authority terminal API

This phase evaluates a supported software API boundary around the
actual archived synthetic R122 TerminalPath object graph.

`TerminalAuthority.create()` constructs its own saturated synthetic
fixture. The documented API consists of:

- `create()`: returns a wrapper plus an inert local lease and owner;
- `inspect()`: returns JSON-detached observations;
- `terminal_cancel()`: performs terminal cancellation;
- `terminal_retire()`: performs ordered terminal retirement.

The underlying R122 facade, R117 registry, R116 pool and session objects
are not returned through this documented API.

Mutations execute on an identity-aware deep-copied candidate using the
unchanged R126-B1 clone helper. Selected identity, count, phase, receipt,
work-preservation and integrity conditions are checked before replacing
one private reference with the candidate.

A private diagnostic fault seam is included for tests. It is NOT an
authorization interface or a production API.

CRITICAL NONCLAIMS:

- This is a cooperative Python API contract, not a security sandbox.
- Python introspection can access name-mangled private state.
- Arbitrary code may mutate object internals.
- No exhaustive object-graph alias isolation was demonstrated.
- No concurrency lock or linearizable multi-thread contract exists.
- The pointer assignment is neither crash-durable nor process-persistent.
- No authenticated receipts, secure capability handling, external
  reference revocation, distributed exactly-once or physical liveness.
- The original archived R117/R122 implementations remain unchanged.
- No real robot actuator or hardware emergency stop is involved.
- No M2DGR recorded data, original GT, sealed confirmation_test,
  qualified physical factors, learned health head, or ATE/RPE scoring.
- All 11 physical/scientific admissibility gates remain CLOSED.

R126-D1 checks basic API behavior. Full fault-matrix validation is
reserved for R126-D2 and must not be claimed until it has passed.
