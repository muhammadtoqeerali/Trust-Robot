# R134-A44 real camera–IMU shadow diagnostic checkpoint

Status: **real recorded-input diagnostic reproduced; scientific
factor admission still blocked**.

## Scope and provenance

The published R134-A40 shadow kernel was executed in memory
on UNIVER against Hilti-Oxford 2022 `exp14_basement_2`.

Published kernel commit:
`eeff75d78f55ee868762a25dde1e7d8fa4ec09d6`

Published source SHA256:
`048abce9b63a13176dab1ccb36208195c40baaee4ba61f91eb793bccd9a04462`

Its compressed transfer and decompressed source hashes passed
at runtime. The camera calibration YAML hash passed.

The experiment decoded 12 camera frames and 11,003 IMU messages.
Eight selected image pairs were evaluated under two timestamp
interpretations, giving 16 descriptive evaluations.

The accompanying aggregate JSON is a transcription of the
user-supplied R134-A44 terminal output. It is **not** a signed,
independently attested experimental log. No real dataset or raw
sensor samples have been transferred into Git.

## Descriptive results

Median of eight pair-level median angular residuals:

| Rotation hypothesis | Header time | Kalibr-shifted time |
|---|---:|---:|
| Zero | 0.49050 degrees | 0.49050 degrees |
| Negative gyro | 0.20914 degrees | 0.21244 degrees |
| Positive gyro | 0.93475 degrees | 0.93195 degrees |

Negative gyro reduced the median residual relative to zero
in 4/8 image pairs for either timestamp interpretation.
All four were in previously identified active-motion windows.
The four near-stationary pairs favored zero rotation by median.

Results matched R134-A33 to the printed precision.
That is **implementation reproducibility on reused observations**,
not independent recording-level confirmation.

The aggregate median is descriptive and must not be used as a
localization metric, effect-size estimate or significance test.
Frame-window correlations, stationary pixel quantization,
visual parallax, gyro bias and feature-matching limitations
remain uncontrolled.

## Scientific boundaries

- Real recorded camera and IMU observations were read on UNIVER.
- Published kernel and calibration file hashes were verified.
- The camera-to-IMU frame bridge remains provisional.
- Kalibr timestamp-shift interpretation is not certified.
- Valid rotation-matrix structure is not physical calibration proof.
- No independently validated 6-DoF reference was accessed.
- No metric pose, covariance or estimator factor was generated.
- No real health supervision or health labels were authorized.
- All 11 M2DGR scientific gates remain CLOSED.
- The 22 TRAIN / 7 CAL-VAL / 7 confirmation-test partition
  is unchanged; confirmation-test data was not accessed.

The accompanying test checks transcription consistency and
scientific-boundary declarations. It does not reconstruct
the real camera or IMU measurements or independently replicate
the original UNIVER computation.

## Next justified research step

Seek independent source/frame/timestamp evidence or test a
separately predeclared recording, strictly diagnostic-only,
without unlocking physical factor admission. Do not iterate
thresholds on these already-examined windows.
