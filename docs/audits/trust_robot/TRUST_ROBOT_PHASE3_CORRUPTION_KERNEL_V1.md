# TRUST-ROBOT Phase-3 Corruption Kernel V1

## Phase objective

Phase 3:

**Multimodal fault/degradation/attack taxonomy and corruption engine**

Exit evidence:

**Deterministic paired corruption framework**

This kernel is the first local implementation layer. Phase-3 exit evidence is
not yet declared satisfied.

## Adoption decision

The historical `src/imu_reliability/injection` implementation was reviewed
before this kernel was created.

The following concepts are deliberately retained:

- immutable/copy-on-create clean inputs;
- explicit paired clean/corrupted outputs;
- SHA-derived deterministic specification and injection identities;
- origin-index preservation;
- explicit synthetic truth records;
- no-op rejection;
- immutable manifest semantics;
- separation of synthetic truth from runtime causal attribution.

The historical package itself is **not** imported by TRUST-ROBOT.

Historical IMU/HAR severity values, random seed grids, detector thresholds,
runtime evidence mappings, final-test outcomes, and old corruption registries
are not adopted as TRUST-ROBOT policy.

Historical source hashes reviewed by the adoption audit included:

- `src/imu_reliability/injection/types.py`
  `b8c1808de1f4a7e3635d5aac8de8462964d8004036c24da46f7627aa55e5fe61`
- `src/imu_reliability/injection/p0.py`
  `dfacc36671b556f121cf39b0b2c1b720b1b1ad372cc44fb381173f8b7a0bb367`
- `src/imu_reliability/injection/manifest.py`
  `e7647e9a15c8c0f3730b0d704aa5f64fe54ae1edc2b37bc41e684cf9561c2e97`

They remain inherited historical code rather than dependencies of the new
TRUST-ROBOT kernel.

## New native representation

`EventStream` represents an immutable sequence of numerical event payloads.

Payload shape may differ between events, allowing the same core representation
to hold, through future adapters:

- IMU vectors;
- camera image arrays;
- LiDAR point clouds;
- depth data;
- GNSS or odometry payloads;
- other numerical event data.

Each stream records:

- modality;
- source identity;
- event timestamps;
- event payloads;
- clean-origin indices;
- adapter metadata;
- deterministic content fingerprint.

The timestamp field is an adapter-supplied event label. The corruption kernel
does not promote it to a verified physical clock or synchronization fact.

## Implemented structural mechanisms

V1 implements three explicit deterministic mechanisms.

### EVENT_GAP

An explicit contiguous event range is removed.

A pre-gap and post-gap event must remain.

Clean-origin indices remain available on surviving events.

### EVENT_REPEAT

An explicit range of event payloads is replaced by the immediately preceding
clean payload.

Timestamps continue unchanged.

Clean-origin indices continue unchanged.

A no-op repeat is rejected.

### TIMESTAMP_STEP_SHIFT

An explicitly supplied non-zero integer `offset_ns` is applied at one internal
event boundary and to every later event timestamp.

The kernel does not choose this value.

The output is allowed to become non-monotonic because temporal corruption
itself may violate timestamp ordering.

This does not claim anything about the physical meaning of a dataset timestamp.

## Scenario taxonomy

Mechanism truth and scenario context are separated.

Scenario context may be:

- unattributed;
- fault;
- environmental degradation;
- attack.

An attack context requires an explicit threat-model identity.

Calling a synthetic scenario an attack does not establish that any observed
real dataset event was maliciously caused.

Synthetic corruption truth is not runtime causal evidence.

## Parameters deliberately not selected

This kernel selects no:

- severity grid;
- fault magnitude;
- attack budget;
- noise standard deviation;
- dropout probability;
- drift rate;
- jitter distribution;
- corruption threshold.

No default numeric corruption magnitude exists.

No confirmation-test outcome may select these values.

## Current scientific scope

This implementation:

- does not open M2DGR bags;
- does not open confirmation-test data;
- does not access reference trajectories;
- does not run the Phase-2 estimator;
- does not evaluate localization;
- does not compute ATE/RPE;
- does not score an estimator;
- does not change synchronization status;
- does not change M2DGR evaluation readiness.

All current tests use synthetic fixtures only.

## Remaining Phase-3 work

Before Phase 3 can satisfy its exit evidence, subsequent local layers should
add:

1. explicit adapters between real TRUST-ROBOT modality payloads and the generic
   event-stream contract;
2. deterministic modality-specific corruption primitives where scientifically
   justified;
3. a prospective corruption-policy manifest that defines how parameters may be
   selected without confirmation leakage;
4. regeneration/provenance receipts for real TRAIN corruption instances;
5. paired clean/corrupt execution checks against the frozen Phase-2 backbone.

None of those steps authorizes ATE/RPE while the independent evaluation
protocol remains blocked.
