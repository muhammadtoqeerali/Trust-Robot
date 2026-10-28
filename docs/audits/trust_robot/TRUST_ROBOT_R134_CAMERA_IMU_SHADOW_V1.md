# R134 camera–IMU shadow rotation diagnostic V1

Status: **tracked diagnostics-only implementation candidate**.

## Provenance

The module is a byte-identical copy of the off-Git R134-A37 V2
synthetic kernel, independently inspected in R134-A38.

Source SHA256:
`048abce9b63a13176dab1ccb36208195c40baaee4ba61f91eb793bccd9a04462`

The API consumes already-constructed camera-bearing pairs, bounded
IMU angular-rate samples, a provisionally supplied 3x3 camera-from-IMU
rotation and an optional timestamp shift. It returns three descriptive
angular residual hypotheses: zero, negative gyro and positive gyro.

## Empirical diagnostic motivation

Hilti-Oxford 2022 recording `exp14_basement_2.bag` was previously
examined on UNIVER without ground-truth access.

R134-A32: negative gyro improved median camera-bearing residuals
relative to zero rotation in 7 of 8 camera pairs.

R134-A33: negative gyro improved residuals in 4 of 8 new pairs,
specifically all 4 actively moving pairs. The 4 near-stationary pairs
did not improve against zero rotation.

These results show limited cross-modal consistency, not independently
verified physical calibration, camera pose, synchronization or accuracy.

## Software boundary

- Synthetic geometry and negative-input controls exercised.
- Distinct angular bearings are required, but independent physical
  observations are **not** established.
- Reports are frozen but trivially constructible by callers.
- Reports are never authorization tokens.
- No factor generation, pose estimate, covariance, classifier,
  health label, confidence calibration or safety action is provided.
- No runtime sensor adapter or estimator integration is included.
- No Git-tracked raw dataset, real sensor samples or calibration
  coefficients are introduced.
- No production-facing threshold has been selected.
- The source's numerical bounds are computational limits only.
- Static admission-gate inspections do not establish dynamic isolation.

## Scientific disposition

All 11 M2DGR scientific gates remain CLOSED.
M2DGR 22 TRAIN / 7 CAL-VAL / 7 confirmation-test split is unchanged.
Real recorded estimator-factor admission is DENIED.
Health-label authority is DENIED.
Physical calibration, timestamp interpretation and independent pose
reference remain unverified.

Before any later runtime integration, add separate tests that prove
the shadow result is not interpreted as a pose factor or authorization.
