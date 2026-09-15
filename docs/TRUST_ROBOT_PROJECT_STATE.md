# TRUST-ROBOT Project State

Last Updated: 2026-09-15

Repository: `muhammadtoqeerali/Trust-Robot`

This document is the authoritative implementation-state record for the
TRUST-ROBOT research project.

## Current phase

Phase 2 — M2DGR Reference Quality Audit and Evaluation Readiness

Status: COMPLETE — pending Phase-2 Git checkpoint.

Next phase:

Phase 3 — Synchronization Verification.

## Research objective

TRUST-ROBOT is developing a trustworthy multimodal robot-perception and
evaluation framework with explicit provenance, independent reference
validation, leakage prevention, reproducibility, dataset-aware
evaluation, synchronization correctness, calibration integrity, and fair
comparison protocols.

Core modalities:

- camera
- LiDAR
- IMU

Future platform-specific modalities may be added only after actual
stream/provenance verification.

## Completed foundations

Implemented and validated:

- stream and frame contracts
- reference-independence rules
- split and lineage constraints
- synchronization contracts
- explicit measurement-time basis
- no unsupported fixed timestamp offset
- no confirmation-data tolerance selection
- calibration artifact provenance
- trajectory manifest schema V1
- deterministic canonical hashing
- immutable manifest writing
- M2DGR trajectory discovery
- M2DGR reference-family mapping
- M2DGR reference structural auditing
- dimension-specific translation/rotation sample validity
- reference-quality artifact hashing
- audit-backed M2DGR manifest admission
- retirement of synthetic `[0,1] ns` reference coverage

## Phase-2 validation result

TRUST-ROBOT unit tests:

66 PASS.

Authoritative M2DGR reference-quality artifacts:

36.

Reference families:

- RTK/INS: 16
- Leica: 11
- motion capture: 9

Structural translation invalidity:

0 samples across all 36 released reference files.

Leica:

- translation supported
- rotation unsupported
- continuous-time coverage not inferred from sample timestamps

Motion capture:

All 9 mocap trajectories contain structurally invalid rotation samples:

- room_01: 165
- room_02: 90
- room_03: 216
- room_dark_01: 122
- room_dark_02: 191
- room_dark_03: 145
- room_dark_04: 107
- room_dark_05: 78
- room_dark_06: 160

RTK/INS:

All 16 trajectories are structurally clean under the current finite-value
and quaternion-norm structural checks.

These structural results do not independently verify physical tracking
accuracy.

## Manifest provenance

Legacy dataset-local manifest:

`manifests/m2dgr_trajectory_manifest_v1.json`

Status:

legacy pre-reference-coverage schema.

Legacy file SHA256:

`efcee88f57355d7458659084cb224dbfbde8efde28e7cd3d4be9cd16e4b5376e`

Legacy manifest content SHA256:

`6503d8c94147465903b3341e02b317c0de7ab3a5beed1e52336b5f65252bf671`

The legacy artifact was verified and left unchanged.

Phase-2 audited successor:

`manifests/m2dgr_trajectory_manifest_v1_phase2_audited.json`

Manifest content SHA256:

`7183501dba3ee05fd0951424e144b94b7b55ded068434a08e1df174492f06745`

File SHA256:

`b4bac02cc64592e86fbe105fedd901b20a426463586088015a26b9c295c7fa4f`

Current strict schema validation:

PASS.

Reference-quality index:

`manifests/m2dgr_reference_quality_index_v1.json`

Index content SHA256:

`c768e25ca4957280ba042a8dc694990723188ce4032ff09d95a3e1409cae50e0`

File SHA256:

`5605c9da59f0081c5f0b4c564451a5d93bb3de2ec35cd9702073422913696f77`

## Integrity provenance

All 36 ROS bag SHA256 checksum sidecars were validated against the legacy
manifest.

The bag payloads were not re-hashed during Phase-2 finalization.

All 36 generated reference-quality artifacts are bound to their raw
ground-truth SHA256 values.

Raw reference files were not modified.

## Important semantic distinction

Reference-quality artifacts contain sample-index validity runs.

Those runs are not continuous-time validity intervals.

They do not authorize interpolation between samples.

No numerical gap threshold has been frozen.

No motion-discontinuity rejection threshold has been frozen.

## Evaluation readiness

At this checkpoint:

- structural reference quality audited: TRUE
- raw reference integrity bound: TRUE
- synchronization verified: FALSE
- continuous-time reference coverage verified: FALSE
- physical reference quality independently verified: FALSE
- numerical association tolerance frozen: FALSE
- evaluation ready: FALSE

Therefore estimator scoring remains blocked.

## Scientific policies that remain frozen

Do not violate:

- no ground-truth leakage
- no reference derived from evaluated estimator inputs
- no unsupported synchronization claim
- no arbitrary fixed timestamp offset
- no numerical association tolerance selected on confirmation/test data
- no unsupported calibration value
- no interpolation across unverified reference gaps
- no rotational scoring where independent orientation reference is unavailable
- no scoring of structurally invalid mocap rotation samples
- no final-test parameter selection

## Next phase — Phase 3 Synchronization Verification

Objectives:

1. Establish a ROS-independent or otherwise reproducible bag inspection path.
2. Verify actual sensor measurement-time fields.
3. Characterize camera/LiDAR/IMU timing from measurement timestamps.
4. Separate bag record time from measurement time.
5. Test whether fixed offsets are supported by evidence.
6. Keep fixed offset unset when evidence is insufficient.
7. Establish reference-to-estimator temporal association evidence.
8. Select any numerical association tolerance only through documented
   evidence and permitted validation data.
9. Preserve confirmation/test independence.
10. Keep evaluation readiness false until the synchronization contract is
    actually satisfied.

## Development rule

For long workstation jobs that may take many minutes or hours, use a
detached workstation process with a PID and persistent log so laptop or
SSH disconnection cannot terminate the computation.

Short validation and implementation commands may run normally in the
interactive terminal.
