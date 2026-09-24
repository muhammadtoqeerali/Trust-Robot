# TRUST-ROBOT Phase-6 Probabilistic Calibration Software Freeze V1

Status: Phase-6 software checkpoint prepared for promotion.

The frozen claim is intentionally limited:

**Validation-only probabilistic-calibration architecture is implemented.
Empirical temperature fitting and probabilistic calibration are deferred.**

## Implemented boundary

Phase 6 calibrates modality-health probabilities.

It does not alter physical sensor geometry, intrinsics, extrinsics,
synchronization, or reference-frame alignment.

The proposal-defined mechanism is temperature scaling.

The implementation provides fail-closed execution and output guards.

## Current empirical state

No trained empirical Phase-5 health model is available.

No admissible validation health-label set is available.

No uncalibrated health-model probability output is available.

Therefore:

- calibration objective is unselected;
- calibration quality metrics are unselected;
- temperature scope is unselected;
- temperature parameter is unselected;
- no temperature has been fitted;
- validation bags remain unopened for calibration;
- calibrated probability output remains disabled.

## Data-selection boundary

The frozen validation_calibration partition contains seven trajectories.

It is reserved for future calibration selection once the empirical gate opens.

The seven-trajectory confirmation_test partition remains closed and cannot
select calibration or operating-point parameters.

## Operating-point separation

Health-state thresholds and suppression/recovery/fallback thresholds remain
separate from temperature calibration.

No such threshold is selected by this Phase-6 checkpoint.

## Deferred obligations

The Phase-5 empirical health model must first become admissible.

Then Phase 6 still requires validation-only selection of its calibration
objective, any calibration-quality metric, temperature scope, and fitted
temperature value.

Those selections must be frozen before confirmation_test is opened.

## Frozen evidence

- parent commit: `6c82b68a2086e140379f283bfdd4110437555ec1`
- Phase-5 freeze: `457a42c3778731307b1371208407fca6d7cf8e604718f81138034479deb0d09a`
- Phase-6 contract config: `7761cf8c39620d7166c88092470aeb09e2f5b1120cd0d4be3e1c11118822f367`
- Phase-6 contract module: `81c22be62a4dec6e37cb0a7c5dda90b1b300f6b3a5234c7a605d176c652f23ab`
- closure report: `2342ee541365c179d89d09ecc3de4ee75b17a8075257d4cc6d5f4a418be41f68`
- closure JSON: `eadfefa1a3267a26cfbc06e0d2f877c6872cc67df643ba66c1c380bec29ff204`

## Freeze artifacts

- manifest: `a022c1923d340bb2fc40a2c7515199ab92d7745f95546ca055ee63fb11f1f2e6`
- validation tests: `6632e0c164e7af0ca92b681ed9a6d8299c4ce94ce05d18a05c6c6419e5f1bbce`
