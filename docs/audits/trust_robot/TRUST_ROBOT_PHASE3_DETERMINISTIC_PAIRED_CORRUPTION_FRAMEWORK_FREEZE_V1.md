# TRUST-ROBOT Phase-3 Deterministic Paired Corruption Framework Freeze V1

## Decision

Phase 3 is complete.

Objective:

**Multimodal fault/degradation/attack taxonomy and corruption engine**

Required exit evidence:

**Deterministic paired corruption framework**

Exit-evidence status:

**SATISFIED**

Frozen framework identity:

`trust_robot_phase3_deterministic_paired_corruption_framework_v1`

## What is frozen

The framework provides:

- immutable multimodal `EventStream` inputs;
- explicit clean/corrupt `PairedCorruption` outputs;
- SHA-derived corruption specification identities;
- SHA-derived corruption instance identities;
- clean-origin provenance;
- copy-on-corrupt behavior;
- no-op rejection;
- deterministic manifests;
- explicit synthetic-truth records;
- separation of synthetic truth from physical/runtime causal evidence;
- prospective corruption-selection provenance.

Implemented generic structural mechanisms are:

- `EVENT_GAP`;
- `EVENT_REPEAT`;
- `TIMESTAMP_STEP_SHIFT`.

The declared generic representation supports:

- camera;
- depth;
- GNSS;
- IMU;
- LiDAR;
- proprioception;
- wheel odometry;
- other numerical event streams.

## Real-data evidence

The current real-data integration proof is LiDAR.

Frozen TRAIN `Circle_01` was adapted through the exact Phase-2 Velodyne XYZ
decoder.

A prospectively declared `EVENT_GAP` removed clean origin index `1` from the
fixed three-event mechanical slice.

Clean origins:

`[0, 1, 2]`

Corrupted origins:

`[0, 2]`

The source bytes remained unchanged.

The clean EventStream remained unchanged.

Repeated corruption reproduced the same specification identity, injection
identity, corrupted EventStream fingerprint, and corruption manifest.

## Frozen estimator-plumbing evidence

Both sides of the real clean/corrupt pair were passed to the exact frozen
Phase-2 function:

`register_current_scan_to_previous`

Clean topology:

`[[0, 1], [1, 2]]`

Corrupted topology:

`[[0, 2]]`

Repeated paired execution was exact.

The registration pose, fixed-point iteration count, nearest-neighbor RMSE and
other registration diagnostics are execution diagnostics only.

They are not localization accuracy measurements or corruption-selection
criteria.

## Prospective experimental control

Controlled corruption conditions must be selected and provenance-bound before
execution.

The engine cannot silently choose missing:

- event locations;
- durations;
- magnitudes;
- delays;
- noise levels;
- severity;
- attack budgets.

Estimator outputs, registration diagnostics, reference errors, validation
metrics and confirmation-test outcomes cannot select corruption experimental
conditions.

## Scope limitation

Phase-3 closure freezes a deterministic paired corruption **framework**.

It does not claim that every modality-specific physical fault, environmental
degradation or adversarial attack primitive is already implemented.

The current real-data proof is LiDAR.

Camera-, IMU-, GNSS-, depth- and other modality-specific physical corruption
models may be introduced later only through their own prospective
specifications.

The existing component artifacts are intentionally not rewritten to alter
their historical pre-closure status fields. This closure manifest is the
authoritative aggregate phase-level satisfaction record.

## Evaluation boundary

Phase-3 closure does not authorize M2DGR localization evaluation.

Still unchanged:

- reference data used: false;
- confirmation-test data used: false;
- ground-truth association performed: false;
- alignment performed: false;
- ATE computed: false;
- RPE computed: false;
- trajectory scoring performed: false;
- estimator scoring performed: false;
- synchronization verified: false;
- evaluation ready: false.

## Regression evidence

The comprehensive closure review passed.

TRUST-ROBOT regression:

**306 / 306 PASS**

## Freeze manifest

`manifests/trust_robot_phase3_deterministic_paired_corruption_framework_freeze_v1.json`

Manifest file SHA256:

`330c5041cb27b9460cb2502aa3ea32b5b4e565facfa2fe5b1bc30554257189f0`

Manifest content SHA256:

`860f2b5f995a3f65951314b3bfaf6aa5576300b4f7a4c91c52cccbe3a5920270`

## Promotion identity

The Git commit containing this audit and the Phase-3 freeze manifest is the
authoritative Phase-3 repository promotion checkpoint.

The commit hash is intentionally not embedded here because that would make
this document self-referential.
