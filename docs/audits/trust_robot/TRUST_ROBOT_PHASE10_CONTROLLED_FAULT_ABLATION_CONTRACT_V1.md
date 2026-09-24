# TRUST-ROBOT Phase-10 Controlled-Fault / Causal-Ablation Contract V1

Status: software experiment architecture implemented locally; controlled-fault
and causal-ablation execution remains disabled.

## Scope

Phase 10 is:

**Causal ablations and controlled faults — Same-backbone RQ1/RQ2 evidence.**

The numbered master section "10. Safety supervision" is a conceptual project
section and is not the Phase-10 phase-plan definition.

## RQ1

RQ1 asks whether explicitly supervised and calibrated
healthy/degraded/unusable modality probabilities outperform fair
validation-calibrated proxy reliability scores.

The proxy reliability definition and concrete comparison variants remain
unselected.

The empirical Phase-5 health model and Phase-6 probability calibration are not
yet available, so RQ1 execution remains blocked.

## RQ2

RQ2 asks whether health-aware factor weighting improves
localization/state-estimation robustness and graceful degradation under
increasing fault severity.

Numeric Phase-8 factor conditioning is not available.

Fault severity values and severity grids remain unselected.

RQ2 execution therefore remains blocked.

## Native controlled-corruption binding

The currently frozen native Phase-3 mechanisms are exactly:

- EVENT_GAP
- EVENT_REPEAT
- TIMESTAMP_STEP_SHIFT

Their selection policy is bound into the Phase-10 architecture.

They are not executed by this checkpoint.

Synthetic corruption truth is not treated as:

- a health label;
- proof of a physical fault; or
- runtime causal evidence.

## Controlled availability

The Phase-5 controlled-availability interface is named as a reuse candidate.

It remains an unaccepted health-supervision source with zero real health
labels.

No controlled-availability intervention is executed.

## Fault parameter policy

No numeric severity is selected.

No severity grid is selected.

No attack budget is selected.

No fault schedule, duration, probability, or cross-partition seed schedule is
selected.

Silent defaults and performance-driven corruption-condition selection remain
forbidden.

## Scientific rules

Faults must be injected at the scientifically appropriate layer.

Raw-sensor corruption and factor-level corruption are not interchangeable.

Clean and corrupted derivatives of a base trajectory remain in the same
partition.

Corruption random seeds may not be reused across partitions.

Held-out test data may not select severity levels or attack budgets.

## Evaluation boundary

Controlled-fault robustness, graceful degradation, estimator availability,
health discrimination, calibration quality, and localization/state estimation
remain separate evidence categories.

No undocumented aggregate score is introduced.

No ATE/RPE or final scoring is authorized.

## Artifact hashes

- config: `7739dfd406635ec55cce54a0c58af02f1da427d768d41361232aa3ac2546eb99`
- module: `4322842cce824ad933c4ac0388142408a986877ac743a367a31251b7e7bd83b4`
- tests: `fbaebd2618b368d09d17eeb8ad11cad930135cacaa048291af36bbd1b3222586`
- Phase-9 freeze: `9c84e85ed6789e01e6eb8d6d25cf40bcdec8b436af879cf54aa3e1b1df80122d`
- Phase-3 freeze: `330c5041cb27b9460cb2502aa3ea32b5b4e565facfa2fe5b1bc30554257189f0`
- Phase-3 taxonomy: `f8a572fc3c25b0effc9f5d0f5fd084a69fc712953f5ae51c0ad3a06a773c02a7`
- Phase-3 selection policy: `df130b8b06831c443b7027dbf70e521a7969c558e628adaf95f87184fbe5a9f6`
- scope-resolution report: `960f298aa8159ad4c4a0a57c9b7fa2a77e7b5e99c43d4be9c2f21ead7a955eb3`
- scope-resolution JSON: `ab5655fd1f2844dcad76c100d36d48085c65ad019aa9a024a77ebe61d2855ae7`
- RQ1/RQ2 basis report: `d3939b9f3af7f90cfc16f715b09562cac99215e94e4cc2162c24368b88ea5ef8`
- RQ1/RQ2 basis JSON: `64e13c8e7b015aadbe43cecbfeaa5a9b7fde3193810a7fc728875cfed2f1923a`
