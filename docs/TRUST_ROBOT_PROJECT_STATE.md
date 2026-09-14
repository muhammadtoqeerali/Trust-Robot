# TRUST-ROBOT Project State

Last Updated:
2026-09-14

Repository:
muhammadtoqeerali/Trust-Robot

Purpose:
Scientific implementation tracking document.
This file is the first document an AI agent should read before modifying the project.

============================================================

# CURRENT PHASE

Phase:
Calibration Artifact Provenance Extension

Status:
NEXT IMPLEMENTATION TARGET

Current scientific objective:

Introduce machine-readable calibration provenance without
freezing unsupported calibration assumptions.

============================================================

# COMPLETED IMPLEMENTATIONS

## Phase 1 — Data Contract Foundation

Status:
COMPLETE

Implemented:

- Stream contracts
- Frame contracts
- Reference validity rules
- Dataset readiness validation
- Synchronization contract
- Trajectory record validation

Validation:

- Unit tests passing
- Leakage prevention rules active
- Reference independence enforced


------------------------------------------------------------

## Phase 2 — Synchronization Contract Extension

Status:
COMPLETE

Implemented:

- Measurement time basis
- Header timestamp handling policy
- No default fixed offset
- No frozen numerical association tolerance
- Confirmation split cannot select tolerance

Scientific decisions:

DEFAULT_FIXED_OFFSET = NONE

NUMERICAL_ASSOCIATION_TOLERANCE = NOT_FROZEN

SYNCHRONIZATION_VERIFIED = FALSE


------------------------------------------------------------

## Phase 3 — Trajectory Manifest Schema V1

Status:
COMPLETE

Implemented:

- trajectory manifest schema
- deterministic manifest generation
- SHA256 identity tracking
- immutable manifest write policy
- lineage validation reuse
- synchronization coverage validation

Validation:

52 tests PASS

Synthetic manifest validation PASS

Real M2DGR assignment:
NOT STARTED


============================================================

# DATASET STATUS

Dataset:

M2DGR

Acquisition:

IN PROGRESS

Current status:

- ROS bags downloaded incrementally
- Resume download verified
- No truncation observed
- Acquisition process remains independent from development


Validation completed:

- ROS bag magic validation
- Header timestamp extraction
- Sensor timing characterization
- Cross-stream timing characterization

Important policy:

Timing characterization does NOT imply synchronization verification.


============================================================

# SCIENTIFIC POLICIES (DO NOT VIOLATE)

Frozen:

- No evaluation leakage
- No reference derived from estimator inputs
- No unsupported synchronization claim
- No arbitrary fixed timestamp offset
- No calibration values without provenance


============================================================

# NEXT IMPLEMENTATION ORDER

## Next Phase

Calibration Artifact Provenance Extension

Planned:

- CalibrationArtifactSpec
- Calibration manifest section
- Calibration checksum binding
- Source provenance metadata
- Applicability metadata
- Frame graph validation integration


After calibration:

1. Real M2DGR trajectory assignment
2. Real trajectory manifest generation
3. Dataset split validation
4. Evaluation pipeline preparation


============================================================

# DEVELOPMENT RULES FOR FUTURE AI AGENTS

Before changing code:

1. Read this file.
2. Inspect existing tests.
3. Preserve completed scientific contracts.
4. Add tests before extending functionality.
5. Do not freeze numerical assumptions without evidence.
6. Update this file after every completed phase.


============================================================

Current status:

PHASE_1_PROTOCOL_FROZEN = FALSE

PROJECT_STATE_DOCUMENT = ACTIVE
