# TRUST-ROBOT R98-R99 nonlinear prior checkpoint

Date: 2026-10-22.

Parent commit:
`2520ae6611bc48ddf9bbcd8ce775e29bf7ddc7fb`

## R98

R98 independently audited the existing S6 synthetic
nonlinear SE(3) joint camera-LiDAR-IMU estimator.

Verified:
- 22 regression tests.
- Three manufactured scenarios.
- Twelve nonlinear fixed-lag windows.
- Nine estimator-reported marginalizations.
- One independent local Schur normal-equation audit.
- Independent factor ownership and provenance checks.

R98's detailed independent Schur calculation concerns
a local frozen Gaussian approximation, not the full
nonlinear posterior.

## R99

R99 instrumented the existing S6 marginalization
interface without permanently modifying S6.

Verified:
- 33 regression tests.
- Three synthetic nonlinear scenarios.
- Twelve nonlinear windows.
- Nine individually checked Schur marginalizations.
- Exact prior-object inheritance between windows.
- Factor consumption accounting.
- Instrumented and uninstrumented estimator equivalence.
- Negative tests for corrupted local audit records.

R99's event digests are local integrity checks,
not authenticated provenance or hardware attestation.

## Scientific exclusions

These results concern manufactured sensor measurements.

No physically verified camera, LiDAR, or IMU factors,
capture-clock mappings, extrinsics, calibrated health
probabilities, independent ground-truth scoring,
ATE/RPE or held-out confirmation testing are claimed.

The R95 Gaussian backend has not been merged into
the existing S6 nonlinear estimator.

All 11 scientific gates remain CLOSED.

Original GT files, ROSbags, private raw evidence,
and sealed confirmation data remain outside Git.

The separate M2DGR author inquiry does not establish
physical qualification without verified responses.

## Checkpoint verification

From the repository root:

python3 -B experiments/trust_robot_r98_r99_nonlinear_prior_checkpoint_v1/verify_checkpoint.py verify experiments/trust_robot_r98_r99_nonlinear_prior_checkpoint_v1
