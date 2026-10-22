# TRUST-ROBOT R98-R99 nonlinear estimator checkpoint

Date: 2026-10-22.

Parent: `2520ae6611bc48ddf9bbcd8ce775e29bf7ddc7fb`.

## R98 verified engineering

- 22 passing regression tests.
- Three synthetic nonlinear solver configurations.
- Twelve accepted nonlinear estimator windows.
- Nine reported Schur marginalizations.
- Independent local Schur information, gradient
  and reduced quadratic energy checks.
- Distinct camera/LiDAR factor identities.
- Factor provenance and ownership checks.

## R99 verified engineering

- 33 passing regression tests.
- Nine actual S6 marginalization invocations
  independently audited across three runs.
- Correct prior inheritance across all three
  successive eliminations per run.
- Numerical agreement between local Gaussian
  Schur normal equations and retained priors.
- No duplicate consumed IMU or pose factors.
- Instrumentation restored after each run.
- Instrumented/uninstrumented numerical equivalence.
- Negative tests reject corrupted event chains.

## Scope and limitations

These tests use manufactured camera, LiDAR and
IMU measurements with assumed uncertainty.

The checked Schur equations concern frozen local
linearized Gaussian approximations, not full
nonlinear posterior consistency.

R99 did not merge R95's Gaussian backend into S6.

The digest chain is not independent physical
provenance or authentication.

All 11 scientific gates remain CLOSED.
No real sensor factor execution, physical clock
or extrinsic qualification, health training,
independent GT scoring, ATE/RPE or confirmation
test access has occurred.

The frozen 22/7/7 M2DGR split is unchanged.
Raw ROSbags, original ground truth and private
evidence remain off Git.

The user previously reported emailing M2DGR
authors. No verified response has been ingested.

## Next development

Plan an explicit nonlinear estimator-backend
integration with independent factor lifecycle
tests and fail-closed real-sensor admission.
