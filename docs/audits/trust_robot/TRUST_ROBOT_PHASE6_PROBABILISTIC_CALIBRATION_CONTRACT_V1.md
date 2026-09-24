# TRUST-ROBOT Phase-6 Probabilistic Calibration Contract V1

Status: software contract implemented locally; empirical calibration remains
blocked because Phase-5 empirical health-model outputs do not yet exist.

## Calibration meaning

Phase 6 is probabilistic calibration of modality-health model outputs.

It is not geometric sensor calibration, intrinsic calibration, extrinsic
calibration, synchronization, or reference-frame alignment.

Those physical quantities remain governed by their separate evidence
boundaries.

## Proposal mechanism

The project master context states:

- calibration should use validation/calibration data only;
- temperature scaling is the current proposal mechanism;
- Phase 6 performs validation-only probabilistic calibration.

Accordingly, this contract records temperature scaling as the proposal-defined
mechanism.

It does not fit or select a temperature.

It does not select an optimization objective, calibration-quality metric,
input representation, or global/per-modality/per-class temperature scope.

Historical IMU-reliability and OOD calibrators are not adopted.

## Selection partition

The frozen `validation_calibration` partition contains seven M2DGR
trajectories.

It is the only permitted future data-selection partition for Phase-6
probabilistic calibration.

The current evidence gate does not yet authorize opening those bags for
calibration because there is no trained Phase-5 health model, no admissible
health-label set, and no uncalibrated health-model output to calibrate.

## Confirmation boundary

The seven-trajectory `confirmation_test` partition remains closed.

It may not select:

- calibration mechanism;
- calibration objective;
- temperature scope;
- temperature value;
- health threshold.

## Operating-point separation

Temperature calibration is distinct from health-state operating thresholds,
suppression/recovery thresholds and fallback/safety thresholds.

No such threshold is selected here.

## Current empirical gate

- Phase-5 empirical health model complete: false;
- trained health model available: false;
- uncalibrated health outputs available: false;
- admissible health labels available: false;
- validation calibration inputs available: false;
- calibration objective selected: false;
- temperature scope selected: false;
- temperature selected: false;
- calibration execution authorized: false;
- calibrated probability output authorized: false.

## Artifact hashes

- config: `7761cf8c39620d7166c88092470aeb09e2f5b1120cd0d4be3e1c11118822f367`
- module: `81c22be62a4dec6e37cb0a7c5dda90b1b300f6b3a5234c7a605d176c652f23ab`
- tests: `ba998071f7dc8cd549b1de139fe51e32ed979a3ab710adb8a93449985d8b1b65`
- Phase-5 freeze: `457a42c3778731307b1371208407fca6d7cf8e604718f81138034479deb0d09a`
- Phase-5 health-model config: `aa48c67cdcd19aa5af2a297f42b20d1bb4369b5dcd38bdc2c2ca9ae68ceb4ea3`
- evaluation protocol V2: `4aaec974d9d7b7f0f057a8991dc0486654d58de5f8c2e6ebf239d5d3d313d6d3`
- prospective split freeze: `017a388ef1ce4ad30812669632a022ca37c084871bc949693fd9c0541014238f`
- Phase-6 frontier report: `903652150452ec9c006dbbd14981056afd3525f06844358ee2b9437c210db522`
- Phase-6 frontier JSON: `4c0eae88b55b9dc14b2e376fa4f6fda329da7edde86236fb05825246afe66310`
- master context: `84a4dfebc38cb38d9d3d91bb20ce4134b53d03843108433adee468a995ca4e48`
- phase plan: `de26e1f0dd5029b014b9ac2412f21543ce782a4f22141d0f63f534d2763633b3`
