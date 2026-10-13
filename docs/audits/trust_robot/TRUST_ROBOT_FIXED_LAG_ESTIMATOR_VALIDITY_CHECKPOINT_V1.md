# TRUST-ROBOT fixed-lag estimator validity checkpoint V1

Date: 2026-10-13

**Status: development-only software implementation and
manufactured-fixture regression validation.**

This checkpoint closes a substantial analytical estimator
implementation batch. It does not establish the complete
TRUST-ROBOT scientific system.

## Implemented in this batch

- Fifteen-dimensional Schur-complement information priors.
- First-estimate linearization and factor-ownership accounting.
- Covariance-aware inertial and LiDAR factor fusion with
  marginalization of departing states.
- Longer 12-node synthetic estimator horizon.
- Sensor-input fail-closed robustness checks.
- Numerical rank, conditioning and factor-support diagnostics.
- Opt-in numerical-support reporting and strict admission.
- Preservation of the original estimator public API.
- Nonlinear profile-cost sensitivity characterization.
- Manufactured linear-Gaussian NEES/coverage sanity checks.
- Seeded perturbation stress through the actual nonlinear
  five-node and 12-node estimator.

## Validation results

- Full local regression: 156 tests in 16 suites.
- Seeded nonlinear estimator study: 48 of 48 solves completed.
- Four scenarios: five-node clean/dropout and
  12-node clean/outage.
- Original legacy estimator entry point retained.
- Historical five-node regression compatibility retained.

### Nonlinear Schur study

| Measure | Result |
|---|---:|
| Affine far-perturbation mean objective difference | 8.82975174e-12 |
| Nonlinear near-perturbation mean difference | 3.98336458e-05 |
| Nonlinear far-perturbation mean difference | 0.0133301065 |
| Known-noise Gaussian trials | 512 |
| Matched Gaussian mean NEES | 14.909730 |
| Mismatched Gaussian mean NEES | 59.638918 |

The objective differences quantify fixed-linearization
approximation against a reoptimized nonlinear profile.
They are not physical position errors.

The Gaussian consistency test has manufactured truth and
known assumed noise, independent of physical sensor data.
Its residual chi-square statistic is not a sequential
filter innovation NIS.

### Actual nonlinear estimator stress

| Condition | Nodes | Accepted solves | Total trials |
|---|---:|---:|---:|
| five/clean | 5 | 12 | 12 |
| five/lidar_dropout | 5 | 12 | 12 |
| twelve/clean | 12 | 12 | 12 |
| twelve/lidar_outage | 12 | 12 | 12 |

All stress conditions used synthetic IMU perturbations and
existing analytic scan factors. The unperturbed **estimator
output** was a sensitivity baseline, not independent truth.

Completion of a solver run does not prove estimator accuracy.

## Reproducibility and evidence

The exact sources, tests and the two companion development
reports are committed in this software batch.

The KIOS dedicated experiment evidence includes:

- analytic_estimator_robustness_dev_v1/
- analytic_factor_support_dev_v1/
- analytic_marginalized_support_dev_v1/
- analytic_marginalization_consistency_dev_v1/

Their status manifests bind source and output SHA256 hashes.
Generated experimental payloads, logs and private machine
state are intentionally not committed.

Run the relevant development test scripts with the
dedicated compatible Python environment and PYTHONPATH=src.

## What is not yet qualified

- Physical camera/LiDAR/IMU capture-time synchronization.
- Independently verified extrinsics and reference association.
- Full real-sensor three-modality estimator input.
- Empirically calibrated estimator posterior uncertainty.
- Real three-class health-model training and calibration.
- Runtime health-aware factor weighting.
- Auxiliary consistency runtime execution.
- Hysteretic modality suppression and safety integration.
- Held-out external dataset localization claims.
- Closed-loop physical robot safety performance.

The frozen authorization gates remain closed.
Numerical Jacobian support is not physical observability.
Manufactured perturbation performance is not proof of
fault tolerance or attack resistance.

## Next substantial implementation phase

Move from analytic development to evidence-qualified
sensor-backed factor construction and three-modality
localization integration.

Before scoring real localization:

1. Check stream capture-time and coordinate contracts
   against existing dataset and calibration evidence.
2. Admit only reference-independent measurements under
   explicitly qualified temporal association.
3. Connect valid LiDAR, camera and IMU constraints to the
   fixed nonlinear estimator.
4. Establish independently referenced accuracy evaluation
   only where the reference and synchronization gates allow it.
5. Then obtain admissible supervision for three-class health
   modeling, validation-only calibration, factor conditioning,
   estimator status and supervisory safety.

Do not reinterpret inherited RC-RGD-IMU experiments as
TRUST-ROBOT final results or reopen frozen selection gates
without new scientific authorization.
