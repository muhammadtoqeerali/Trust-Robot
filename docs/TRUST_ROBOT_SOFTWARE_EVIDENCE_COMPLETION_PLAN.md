# TRUST-ROBOT Software Evidence Completion Plan V1

## Purpose

TRUST-ROBOT has frozen software architecture through Phase 14, but many
empirical obligations remain incomplete.

This track converts those architectural contracts into reproducible
software-level evidence using recorded datasets as virtual sensors before
physical hardware integration.

It does not replace the original Phase 5–15 plan. It completes the deferred
empirical obligations required before final confirmation.

## Frozen partition roles

M2DGR remains trajectory-disjoint:

- TRAIN: 22 trajectories;
- VALIDATION/CALIBRATION: 7 trajectories;
- CONFIRMATION/TEST: 7 trajectories.

All clean/corrupted derivatives of one base trajectory remain in one
partition.

Corruption seeds must not be reused across partitions.

Confirmation may not select features, model architecture, learned parameters,
calibration, thresholds, fault severity, attack budgets, association,
alignment, interpolation, evaluation intervals, or metric operating choices.

## SE0 — Scientific readiness and plan freeze

Reconcile the proposal, master context, frozen Phase 5–14 architecture,
dataset split, evaluator boundary, existing real evidence, and empirical debt.

No training, validation selection, confirmation, ATE/RPE, or final scoring.

## SE1 — Deterministic multimodal dataset replay

Build deterministic M2DGR virtual-sensor replay for the core recorded
modalities with exact trajectory identity, split role, timestamp preservation,
lineage, and provenance.

Initial execution is TRAIN-only.

SE1 does not train the health model and does not select scientific thresholds.

## SE2 — Health-supervision protocol

Resolve how healthy/degraded/unusable supervision is defined independently
from final localization error.

Availability is not a health label.

Missing measurements are not zero feature vectors.

A clean dataset branch is not automatically proof of healthy state.

Synthetic corruption identity is not automatically a health label.

## SE3 — Multimodal feature pipeline

Preserve the frozen Phase-4 LiDAR feature contract.

Resolve and freeze reproducible camera and IMU diagnostic feature contracts
prospectively, without using confirmation.

## SE4 — Health-model training

Train the actual modality-health model using admissible TRAIN evidence only.

Trajectory grouping and derivative lineage must prevent leakage.

Any model-family or hyperparameter selection must follow an explicitly frozen
selection procedure and may not use confirmation.

## SE5 — Validation selection and probability calibration

Use VALIDATION/CALIBRATION only for decisions explicitly authorized by the
scientific protocol.

This includes permitted model selection, probability calibration, thresholds,
hysteresis parameters, factor-conditioning parameters, or other operating
points where scientifically justified.

Every selected value must be frozen before downstream final testing.

## SE6 — End-to-end runtime assembly

Connect:

dataset replay
→ localization/frontends
→ modality diagnostics
→ health inference
→ probability calibration
→ auxiliary consistency
→ factor conditioning
→ suppression/recovery/status
→ supervisory shadow decision

No robot command is required for software-level completion.

## SE7 — Controlled faults, attacks, and causal ablations

Execute prospectively frozen controlled-fault experiments for RQ1/RQ2.

Execute attacks only under explicit frozen threat models for RQ3.

Faults, environmental degradation, and attacks remain distinct evidence
categories.

## SE8 — Localization, cross-dataset, and resource evaluation

Resolve remaining physical/evaluator prerequisites before any ATE/RPE claim.

Only then execute scientifically authorized localization metrics.

Prepare compatible cross-dataset experiments where independent dataset
requirements are satisfied.

Measure software-level resources under a prospectively frozen resource
measurement protocol.

## SE9 — Frozen software confirmation

SE9 remains CLOSED.

It can open only after every confirmation-visible choice is frozen, including
feature contracts, health supervision, trained model, calibration,
thresholds, fault/attack operating points, and the evaluation protocol for
every claimed metric.

Confirmation results may not reopen model or protocol selection.

## SE10 — Dashboard and reproducibility package

Expose the frozen, real software outputs through a GitHub-backed Vercel
frontend.

The dashboard may display real values or explicit unavailable/pending states.

It may not alter scientific parameters, calibration, thresholds, or frozen
experiment definitions.

## Hardware boundary

Recorded datasets act as virtual sensor inputs for this track.

Successful software evaluation does not by itself prove physical-hardware
performance.

Later physical sensor and robot integration should reuse the same core
pipeline through live input adapters and platform-specific evidence, rather
than redesigning the scientific core.
