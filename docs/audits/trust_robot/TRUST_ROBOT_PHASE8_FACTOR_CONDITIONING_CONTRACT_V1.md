# TRUST-ROBOT Phase-8 Factor-Conditioning Contract V1

Status: software architecture implemented locally; numerical factor
conditioning remains disabled.

## Authoritative equations

The project defines the persistent-health modality weight conceptually as:

`w_m(t) = p_H_m(t) + alpha_m * p_D_m(t)`

The project defines the final factor scale conceptually as:

`lambda_m = clip(w_m * q_m, epsilon_m, 1)`

These equations are frozen as interface semantics only.

No numerical evaluation is performed by this checkpoint.

## Persistent health pathway

The persistent health pathway requires modality health probabilities.

The proposal explicitly states that `alpha_m` is selected on validation data.

At this checkpoint:

- empirical Phase-5 health inference is unavailable;
- calibrated Phase-6 health probabilities are unavailable;
- `alpha_m` is unselected;
- no default `alpha_m` is created.

## Current-innovation pathway

Current standardized innovation remains scientifically separate from persistent
modality health.

It is reserved for bounded short-horizon conditioning through `q_m`.

At this checkpoint:

- the numerical standardized-innovation definition is unselected;
- the `q_m` definition is unselected;
- no `q_m` value is generated;
- no default `q_m` is created.

## Final factor scale

The authoritative expression includes `epsilon_m` and an upper clip value of
1.

The upper value 1 is preserved because it is explicitly present in the
authoritative equation.

No `epsilon_m` value or selection policy is invented.

No `lambda_m` value is produced.

## Estimator modification

The project states that factor scaling conceptually rescales factor information
or equivalently inflates covariance.

Neither operation is authorized or implemented here.

No estimator factor is modified.

## Phase boundaries

Phase-9 suppression, recovery, fallback, hysteresis and estimator-status logic
remain outside this checkpoint.

No health threshold is selected.

No synchronization, transform or interpolation choice is introduced.

## Data and evaluation boundary

Validation data remain unopened.

Confirmation remains closed and cannot select `alpha_m`, `epsilon_m` or the
`q_m` definition.

No ATE/RPE or final scoring is authorized.

## Artifact hashes

- config: `cbd137977060f961fb14feaeed6194de40b4e4338e5f6c303edc1993110ea5c2`
- module: `96d3c179d1690aa75edd0c6a6d8ce8a14d079da02ab225d1da9ffe2bc4a97b6a`
- tests: `b457e2d26cc3a4a9a381016094a7eeee1acfb77cd8867d147c07d879adfae3cd`
- Phase-7 freeze: `5f416186ee8d8b226f0f88c70a0553cf80fe5213592b8df9b07fc1b5503b7280`
- Phase-6 freeze: `a022c1923d340bb2fc40a2c7515199ab92d7745f95546ca055ee63fb11f1f2e6`
- Phase-5 freeze: `457a42c3778731307b1371208407fca6d7cf8e604718f81138034479deb0d09a`
- Phase-8 frontier report: `fdd91cac466e01306369e8e312d6ac576cd89f0e8edb2e57bd0113116c0f4819`
- Phase-8 frontier JSON: `e171714edcc448c206cadcfb517ca6e9980f09aa352991c622afa7db257eb833`
