# TRUST-ROBOT Phase-11 Cross-Dataset Compatibility Contract V1

Status: cross-dataset software compatibility architecture implemented locally;
secondary-dataset data access and evaluation remain disabled.

## Scope

Phase 11 is:

**Cross-dataset evaluation — generalization/stress evidence.**

## Dataset-role separation

Proposal-level dataset role is not local readiness.

Proposal-level dataset role is not evaluation authorization.

M2DGR remains the primary development benchmark.

Project-declared non-primary datasets are bound as role identities only.

### EuRoC

Declared roles:

- camera-IMU controlled testing;
- different-platform comparison.

Local readiness remains unverified.

No local EuRoC path is present.

EuRoC is not selected for Phase-11 evaluation.

### TUM-VI

Declared role:

- supplementary cross-dataset stress testing.

Local readiness remains unverified.

No local TUM-VI path is present.

TUM-VI is not selected for Phase-11 evaluation.

## Modality boundary

Camera and IMU are proposal-level common modalities across the declared
non-primary datasets.

This overlap is not treated as verified cross-dataset compatibility.

LiDAR coverage is not declared for EuRoC/TUM-VI in the current project role
definitions.

## Reference boundary

Reference-family compatibility remains unverified.

EuRoC Leica-only reference is not rotational ground truth.

TUM-VI partially referenced longer trajectories are not silently treated as
fully referenced trajectories.

Only independently supported intervals and metric dimensions may eventually be
scored.

## Adapter / timing / frames

No Phase-11 cross-dataset adapter is implemented.

Any future adapter must preserve raw timestamps before resampling/alignment.

No unknown offset, clock conversion, interpolation, association, or frame
mapping is assumed.

## Zero-shot and recalibrated transfer

Zero-shot and recalibrated transfer must be reported separately.

Cross-dataset recalibration is currently unauthorized.

If later allowed, recalibration must use a calibration-only subset disjoint
from final cross-dataset testing.

No model, threshold, or probability-calibration refit is authorized now.

## Evaluation

No secondary dataset has been opened.

No secondary split is selected.

No cross-dataset evaluation is authorized.

Validation remains unopened.

Confirmation remains closed.

No ATE/RPE or final scoring is authorized.

## Artifact hashes

- config: `45e4ed026fb0555e2be8ff7498ec3289ca99e51fd38bf066a26f530d4359e7bf`
- module: `93e2e8d8879e346b41bc9bd19daf34c04f88f7ad1e55dace9f3e189be5be63cc`
- tests: `909e1f0e6e973c35bc0ddce1edf860283ec5073699c12e5ddd35f9090dc51f65`
- Phase-10 freeze: `23a69b642fc0e4bd878c7323aeb2975f4eba4e65e6b017ff78f219019ce2a470`
- frontier report: `1fd1a54297c0915aac9b57d91b464b9748a52f93b6cd32aee17aec73009d8b75`
- frontier JSON: `5b8e55c7deff85fea4c9e0394c8504709802f9ac9a4cc5764481ca160b1e5eeb`
- role-resolution report: `c87c02ebe731be0598e2b38200eaa47af7a72b5f01a0fbe2409ce77cbfd81df1`
- role-resolution JSON: `72b194c713893dac372f83d8c44c3ab153a64ba000f655baebf964b356f6194b`
- dataset registry: `dec39d6ad8a084df99bcaa1ff1705dd1bf4a823709baa09e99ea86080738d4b2`
- data protocol: `ffee2e1daea71318f649564c0c48da71a5e26d6ad89a82544e5f216e0ffc2485`
