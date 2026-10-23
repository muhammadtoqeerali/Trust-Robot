# R124 shadow-published terminal transaction: synthetic modeling contract

## Scope and lineage

- Single process, synchronous caller, one manufactured local session, one object-identity lease and owner.
- Inspired by the R117 registry / R120 saturated-denial / R122 terminal and R123 fault-boundary semantics. This is a **separate reduced model**, NOT a clone of their real nested Python objects, nor a drop-in atomic repair for them.
- One immutable `PublishedState` pointer, immutable string-encoded receipts, detached observations. Explicit candidate `dataclasses.replace` preserves local `object()` identity references without `deepcopy`.
- Candidate first undergoes model mutation, model registry + terminal receipt construction, complete structural/hash/semantic validation; only then one local pointer assignment publishes. Prepublication faults leave that pointer and its visible snapshot unchanged.
- Two valid transitions: ACTIVE -> CANCELLED with a terminal-cancel receipt; CANCELLED -> RETIRED with registry-retirement and terminal-retirement linked receipts. The old committed digest and work counters remain unchanged. Model initial version 7 is manufactured, not inferred from R122 recordings.
- At denial-capacity saturation, no factor submit is accepted. Max one session, max one registry retirement, max two terminal receipts. Capacity is a count check, **not reserved RAM**.

## Evidence and fault contract

- For each operation: nine prepublication injection points (`candidate_create_pre`, `candidate_create_post`, `mutation_pre`, `mutation_post`, `receipt_pre`, `receipt_post`, `validation_pre`, `validation_post`, `publication_pre`); two postpublication/no-success-return points (`publication_post`, `ack_pre`).
- Faulting before publication: original published object identity and full detached observation preserved; retriable safely after removal of fault. Faulting after publication: operation visible/complete, caller lacks a success return; replay denied; caller must inspect before deciding any higher-level recovery. No exactly-once guarantee across an external boundary.
- Test suite includes identity binding, owner/version denial, no factor execution, denial-after-terminal, bounded counts, tamper/incomplete-candidate rejection, receipt chain, detached snapshots, work preservation and aggregate negative science gates.
- Independent validator **does not import the R124 engine**; checks the complete 22-case matrix, receipt hashes and cross-chain links, published revisions and all no-claim flags, plus the 51-unit-test log.

## Explicit nonclaims / blocked science

- The experiment is not an integration with R117 `GuardedRegistry`, R122 `TerminalPath`, actual estimator state, S6 or sensor factor front ends. R122/R123 original atomicity gap still exists in their implementation.
- No memory/power/crash persistence, concurrent linearizability, lock-free guarantee, thread safety, durable journal, atomic filesystem write, multi-session semantics, capacity allocation guarantee, secure/authenticated receipt ledger, distributed exactly-once, physical emergency stop, robotic actuation or real-time safety proof.
- No real camera/LiDAR/IMU samples, recorded M2DGR data, original ground truth, confirmation_test access, 6DoF ATE/RPE, learned health-head, physically qualified sensor factors or hardware were used.
- All 11 physical scientific admissibility gates remain CLOSED. `scientific_gates_closed: 11` is a count, not a reconstruction of the exact R43 gate receipt names. No claim of progress on those gates.
- Next scientific decision: assess whether this modeled proof merits a carefully audited full state integration with actual R117/R122 internals; do not misrepresent reduced-model evidence as actual backend atomicity.
