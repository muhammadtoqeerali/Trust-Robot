# M2DGR Phase-2 Reference Quality Audit

Date: 2026-09-15

Project: TRUST-ROBOT

Dataset: M2DGR

## Purpose

This audit establishes structural reference-quality evidence before
trajectory scoring or estimator comparison.

It does not claim that synchronization, continuous-time reference
coverage, physical tracking quality, or evaluation readiness has been
verified.

## Dataset population

Total trajectories: 36

Reference families:

- RTK/INS: 16
- Leica: 11
- Motion capture: 9

## Raw integrity provenance

The dataset contains one precomputed SHA256 checksum sidecar for each of
the 36 ROS bag files.

Phase-2 finalization validated all 36 bag SHA256 values against the
previous immutable trajectory manifest.

The ROS bag contents were not re-hashed during Phase-2 finalization.

Ground-truth SHA256 sidecars were also used to bind each generated
reference-quality artifact to its immutable raw reference source.

## Legacy trajectory manifest

Dataset-relative path:

`manifests/m2dgr_trajectory_manifest_v1.json`

Status:

Legacy pre-reference-coverage schema.

The artifact predates the addition of
`reference_coverage_artifacts` to the current trajectory record schema.

The legacy artifact was not modified.

File SHA256:

`efcee88f57355d7458659084cb224dbfbde8efde28e7cd3d4be9cd16e4b5376e`

Stored and independently recomputed manifest content SHA256:

`6503d8c94147465903b3341e02b317c0de7ab3a5beed1e52336b5f65252bf671`

Legacy content-hash validation: PASS.

## Phase-2 audited successor manifest

Dataset-relative and repository-relative path:

`manifests/m2dgr_trajectory_manifest_v1_phase2_audited.json`

Manifest content SHA256:

`7183501dba3ee05fd0951424e144b94b7b55ded068434a08e1df174492f06745`

File SHA256:

`b4bac02cc64592e86fbe105fedd901b20a426463586088015a26b9c295c7fa4f`

Current strict manifest-schema validation: PASS.

The successor preserves the legacy stream, lineage, synchronization,
calibration, and bag-integrity metadata while replacing unsupported
reference claims with audit-backed reference metadata.

The synthetic `[0,1] ns` reference-coverage placeholder is absent.

## Reference-quality index

Dataset-relative and repository-relative path:

`manifests/m2dgr_reference_quality_index_v1.json`

Index content SHA256:

`c768e25ca4957280ba042a8dc694990723188ce4032ff09d95a3e1409cae50e0`

File SHA256:

`5605c9da59f0081c5f0b4c564451a5d93bb3de2ec35cd9702073422913696f77`

The index binds all 36 reference-quality artifacts to:

- raw ground-truth SHA256,
- quality artifact SHA256,
- previously verified bag SHA256,
- reference family,
- dimension-specific structural validity information.

## Structural translation results

No structurally invalid translation samples were found in any of the
36 released ground-truth files.

This is a structural result only. It is not an independent proof of
physical tracking accuracy.

## Leica results

All 11 Leica trajectories are treated as translation-only references.

Rotation is explicitly unsupported.

No continuous-time interpolation authorization is inferred from sample
timestamps.

Large observation gaps observed in the released Leica files are retained
as diagnostics rather than converted into an arbitrary validity
threshold.

## Motion-capture results

All 9 motion-capture trajectories contain structurally invalid rotation
samples.

Invalid rotation sample counts:

| Trajectory | Invalid rotation samples |
|---|---:|
| room_01 | 165 |
| room_02 | 90 |
| room_03 | 216 |
| room_dark_01 | 122 |
| room_dark_02 | 191 |
| room_dark_03 | 145 |
| room_dark_04 | 107 |
| room_dark_05 | 78 |
| room_dark_06 | 160 |

These failures are not small quaternion normalization deviations.
Observed invalid quaternion norms are substantially different from unity.

Translation validity is preserved independently from rotation validity.

No mocap sample is silently normalized, repaired, interpolated, or
imputed by the structural auditor.

## RTK/INS results

All 16 RTK/INS trajectories are structurally clean under the current
finite-value and quaternion-norm structural checks.

This structural result does not independently verify physical reference
accuracy or synchronization.

## Sample-run semantics

The Phase-2 quality artifact records valid and invalid sample-index runs.

Sample runs do not constitute continuous-time validity intervals.

They do not authorize interpolation between observations.

This distinction is especially important for Leica trajectories with
large observation gaps.

## Evaluation-readiness state

At the completion of Phase 2:

- structural reference quality audited: TRUE
- raw reference modified: FALSE
- continuous-time reference coverage verified: FALSE
- reference-to-estimator synchronization verified: FALSE
- numerical association tolerance frozen: FALSE
- physical reference quality independently verified: FALSE
- evaluation ready: FALSE

These unresolved items intentionally block trajectory scoring.

## Validation

TRUST-ROBOT unit suite after Phase-2 hardening:

66 tests PASS.

Authoritative reference-quality artifacts generated:

36.

Audited successor manifest current-schema validation:

PASS.

Legacy manifest unchanged:

PASS.

Synthetic `[0,1] ns` reference coverage retired:

PASS.

## Next phase

Phase 3 is synchronization verification.

The next work must establish measurement-time evidence and cross-stream
association correctness without introducing arbitrary fixed offsets or
selecting association tolerances on confirmation/test data.
