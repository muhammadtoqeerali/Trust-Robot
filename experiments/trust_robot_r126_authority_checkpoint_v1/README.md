# TRUST-ROBOT R126 authority and reference-boundary checkpoint

Checkpoint candidate: R127.
Date: 2026-10-23.

Parent Git commit:
ae69a775f133127f1c4cf99d034448c7da382918

## Evidence

R126-B1: identity-aware shadow cloning using actual archived
synthetic R122/R117/R116 Python objects.

- 18 tests passed.
- Ten fault cases verified.
- Independent receipt validation passed.
- The initial three-error attempt and targeted repair are recorded.

R126-C: stale-reference and Python mutation challenges.

- 15 tests passed.
- Two retained-facade terminal-operation bypasses confirmed.
- Four linked terminal receipt histories verified.
- Private pointer rebinding and private-object mutation demonstrated.

R126-D1/D2: cooperative single-authority facade.

- 45 combined tests passed (11 D1 and 34 additional D2).
- 22 fault witnesses verified.
- 18 prepublication cases and four postpublication
  acknowledgement ambiguities.
- Independent linked-receipt and three negative controls passed.

Total distinct regression suites: 18 + 15 + 45 = 78 tests.

The D1 tests are already included in the 45-test D2 suite;
do not add their 11 cases again.

## Provenance

The source lineage file pins 28 source evidence artifacts.
27 evidence artifacts are copied byte-for-byte.

One initial failing test log is archived in redacted form,
because traceback text included a local workstation directory.
The untouched original remains off Git, and its original
SHA256 is recorded in source_lineage_v1.json.

R125 and all older Git checkpoints remain unchanged.

## Reproduction status

This is a candidate awaiting R127 independent standalone
verification, fresh archived regression runs, and a final
checkpoint manifest. Do not publish or commit it yet.

## Scientific limitations

These are manufactured synthetic sessions, not real sensor factors.
They do not prove that the unchanged R117/R122 backend is atomic.

The supported authority API restricts ordinary access to its
mutable backend, but introspection bypass and pointer rebinding
are demonstrable in the same Python process.

No security boundary, concurrent linearizability, durable
journaling, process crash recovery, robotic emergency stop,
physical sensor calibration, health training or ATE/RPE scoring
is demonstrated.

The frozen M2DGR 22/7/7 partition is unchanged.
The confirmation_test split remains sealed.

All 11 scientific admissibility gates remain CLOSED.
