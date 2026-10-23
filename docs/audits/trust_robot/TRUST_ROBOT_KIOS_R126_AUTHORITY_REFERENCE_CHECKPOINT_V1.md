# TRUST-ROBOT R126 authority/reference checkpoint

Date: 2026-10-23.
Checkpoint: R127.
Base Git commit: `ae69a775f133127f1c4cf99d034448c7da382918`.

Archive:
`experiments/trust_robot_r126_authority_checkpoint_v1/`

## R126-A — Actual object-identity audit

The original R122 terminal fixture used opaque Python object
identity for its local lease and owner tokens.

Shallow copying retained mutable registry aliases.
Ordinary deep copying created a distinct nested graph but
did not preserve the original lease/owner identity.

These results motivated the narrow R126-B1 identity memo.

## R126-B1 — Identity-aware shadow candidate

18 tests passed. Ten injected fault witnesses passed.

The prototype cloned selected actual archived synthetic
R122/R117/R116 objects while retaining the identity of
inert local lease and owner tokens.

An initial three-error test run was repaired without erasing
the failure history. The original engine and failing log
hashes are preserved in R126 repair/source lineage.

The failing log's copy in this archive has explicit local
workstation-path redaction. Its untouched original remains
off Git.

The copy and selected identity tests do not prove exhaustive
heap isolation or secure capability ownership.

## R126-C — Retained facade and private-object bypasses

15 tests passed and two retained-reference bypasses were
confirmed: cancellation and retirement on a previously
held original facade remained possible after the shadow
adapter had published a separate candidate.

Linked terminal receipts were independently reconstructed.

Ordinary Python code could also rebind the adapter pointer
or directly write private receipt structures.

This defeats a global exactly-once or universal revocation
claim for the shadow adapter.

## R126-D1/D2 — Cooperative single-authority API

The supported wrapper constructs the synthetic terminal
fixture internally and returns opaque local capabilities,
plus JSON-detached observations.

45 combined tests passed, including 11 initial D1 tests
and 34 further D2 tests.

The D2 matrix covered 22 injection cases:

- 18 prepublication failures kept the authority's
  published observation unchanged and supported retry.
- Four postpublication faults preserved published
  completed state but lost the caller acknowledgement.
- Duplicate terminal operations were denied.
- Terminal, denial and retirement linked receipts
  were independently validated.

Python introspection remained able to access the private
backend, mutate it, and rebind the publication pointer.

This is a cooperative API demonstration, not a security
sandbox or a deployed transaction replacement.

## Checkpoint verification

The complete archive contains 37 files, of which 36 are
pinned by the SHA256 checkpoint manifest.

The standalone verifier passed.
28 original R126 evidence artifacts have source lineage.
27 evidence copies are byte-identical, and one failed log
is explicitly redacted with original SHA256 preserved.

Fresh distinct regression count:
18 + 15 + 45 = 78.

Seven report-level negative controls and two complete
checkpoint tamper controls passed.

Manifest SHA256:
`326b93e2a18f153c07c740379edcf106dfa453a3ff86dd7e21e49bcb2d52f047`

Source-lineage SHA256:
`52ed3aa01e10318092692ee6eee526d4a3cfbffa963a0ca74a0c91b5dca8d713`

Prepared documentation SHA256:

- `AGENTS.md`: `c8de1d019d35903c78ac36f0fec1f5b8023ee233c207681ab5907224cf09000b`
- `docs/TRUST_ROBOT_PROJECT_STATE.md`: `7457c89fc4fb86e573976e7bfc1464ef18d194ba6779e07ac4686e1847fe548a`

These document fingerprints describe the exact appended
revisions prepared for this checkpoint. The independently
validated archive remains byte-identical to its off-Git
checkpoint candidate.

## Scientific scope and restrictions

No modifications were made to the inherited R117/R122
implementation by these R126 experiments.

The original terminal mutation/receipt atomicity problem
has not been repaired in the actual R117/R122 source.

No concurrency correctness, secure in-process isolation,
durable transactions, recovery after power loss,
authenticated receipts, hardware emergency stop,
robotic actuation or physical safety guarantee is proven.

These tests use manufactured synthetic sessions, not
qualified camera, LiDAR or IMU data.

The M2DGR 22/7/7 partition remains frozen.
The confirmation_test split remains sealed.
Private recorded data and original GT remain off Git.

No qualified independent physical ATE/RPE reference,
calibrated health model, real-factor admission or
robot safety supervision result is established.

**All 11 scientific admissibility gates remain CLOSED.**

## Next research decision

R126 supplies evidence that a cooperative authority
can preserve tested single-threaded publication boundaries,
while also demonstrating why private object access and
retained references prevent stronger claims.

Further engineering should use an explicitly scoped,
controlled transaction/ownership contract. Do not
promote this experimental wrapper to an actual atomic,
concurrent or physically safe robotic backend.

Prioritize independent physical evidence qualification
before authorizing real sensor factors or scored results.
