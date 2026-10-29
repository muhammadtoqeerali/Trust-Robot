# R135-A22 — Frozen M2DGR evidence-readiness audit

Status: METADATA_ONLY_ALL_ADMISSION_GATES_CLOSED.

## Research purpose

Move beyond repeated manufactured fault experiments
by reviewing the already-published scientific evidence
that blocks real sensor localization and evaluation.

This phase reads only eight frozen repository-tracked
M2DGR metadata JSON artifacts on KIOS.

No dataset files from UNIVER are accessed.

## Evidence examined

1. Calibration evidence.
2. General synchronization evidence.
3. Frozen trajectory split and holdout policy.
4. Reference physical-frame semantics.
5. Reference temporal-association evidence.
6. Evaluation Protocol V2 candidate.
7. Camera/IMU synchronization evidence.
8. LiDAR/IMU synchronization evidence.

The code validates known logical content identities
and scientific blocking states.

The guarded publication script independently checks
all eight published Git blob identities.

## Diagnostic blockers

Eleven explicit metadata blockers are checked,
covering calibration, timing, reference semantics,
scoring permission and evaluation readiness.

These eleven checks are diagnostic criteria.
They are NOT redefinitions or replacements of the
project's original eleven M2DGR admission gates.

The original eleven gates remain CLOSED.

## Important confirmation-test limitation

The frozen split is:
- TRAIN: 22;
- VALIDATION_CALIBRATION: 7;
- CONFIRMATION_TEST: 7.

Confirmation-test membership is prospectively
closed to future model and protocol selection.

However, the published split evidence explicitly
states that this subset is NOT pristine from
all earlier dataset-level inspection.

The audit preserves this limitation. It does
not claim an untouched or fully independent
confirmation-test history.

## Existing unresolved facts

Current frozen evidence does not establish:
- complete metric sensor calibration;
- verified physical camera/IMU synchronization;
- verified physical LiDAR/IMU synchronization;
- justified reference-to-estimator time association;
- exact reference physical measurement origins;
- verified relevant frame transforms;
- an authorized temporal-association tolerance;
- selected evaluation interval or alignment mode;
- executable and scoreable localization metrics.

The 17 required evaluation provenance fields are
stored in frozen Protocol V2 as a dictionary whose
field-name keys each map to required=true. They
remain a schema inventory, not verified physical values.

The metadata reader now checks exact published Git
blob identities of all eight JSON source artifacts,
in addition to the embedded logical content digests.

## Negative tests

In-memory modifications are used to verify that:
- unverified evidence cannot become verified;
- the frozen split cannot silently change;
- prior confirmation-test inspection cannot be erased;
- evaluation execution cannot be silently enabled;
- published logical evidence identities cannot change.

No frozen evidence file is edited.

## Scientific decision

NO_ADMISSION.

No recorded sensor factor execution.
No reference trajectory scoring.
No ATE/RPE claim.
No sensor-health inference.
No factor-weight modification.
No real-world localization recovery claim.

The original 15D estimator remains unchanged.

## Next research action

Prioritize independent timing, coordinate-frame,
physical calibration and acquisition provenance.

Use existing evidence and future explicitly
authorized acquisition to resolve missing facts.

Do not reinterpret metadata presence as
scientific verification or gate admission.
