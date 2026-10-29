# R135-A12: Distinct synthetic depth-camera integration with 15D estimator

Status: **UNTRUSTED_SYNTHETIC_SOLVER_DIAGNOSTIC_ONLY**.

## Objective

Reproduce the successful R135-A11 read-only experiment
as an explicit, tested software module.

The existing Schur-marginalized 15D estimator and
its numerical weighting are unchanged.

## Synthetic observation sources

The LiDAR factors originate from the existing analytic
LiDAR registration fixture.

Camera factors originate from the separately manufactured
metric-depth camera model published in R135-A10.

The camera generator uses projected 3D scene points,
pixel/depth observations and rigid 3D alignment.

It does not copy LiDAR registration factors.

Both sources share a manufactured trajectory. Therefore
they are not independent physical sensor evidence.

## Frozen scenarios

1. LiDAR-only baseline: 7 pose slots.
2. Remove one LiDAR factor: 6 pose slots.
3. Restore the missing slot using ideal depth camera.
4. Restore the missing slot using noisy depth camera.
5. Restore the missing slot using biased depth camera.
6. Replace an existing LiDAR factor using noisy depth camera.

The last four cases use one camera-labeled slot.

No scenario simultaneously includes independent camera
and LiDAR factors on the same edge.

The legacy estimator continues to use a single
relative-pose slot and its existing residual model.
Distinct modality-specific factor information is
not selected or authorized.

## Numerical diagnostics

The module reports:

- accepted nonlinear estimator windows;
- Schur elimination count;
- factor consumption and reuse checks;
- selected synthetic factor-slot provenance;
- summed numerical optimization objective;
- final synthetic estimator position;
- SHA256 of synthetic solver output;
- final-position difference relative to the
  synthetic LiDAR baseline.

The summed costs are optimizer diagnostics; they are
not independent localization error measurements.

The baseline-relative position difference is not
ATE, RPE or independent ground-truth validation.

The biased observation mode is a fixed pair-local
manufactured intervention, not a validated real fault.

## Strict scientific limitations

This module does not establish:

- physical localization performance;
- real sensor redundancy;
- health-aware measurement weighting;
- calibrated pose-factor covariance;
- physical observability;
- calibrated sensor extrinsics or synchronization;
- sensor-health probabilities or labels;
- robustness improvement or recovery in real faults;
- RQ1/RQ2 scientific experimental conclusions.

No external fixture, source record, probability,
health state, information weight or ground-truth
reference can be supplied through its public scenario API.

## M2DGR and data safeguards

The frozen 22/7/7 split remains unchanged.
No M2DGR or Hilti recorded source is read.
No held-out or confirmation-test data is accessed.

All 11 M2DGR scientific admission gates remain CLOSED.

## Next step

Validate the 20 new tests and all existing regressions,
verify exact three-file Git scope and SHA256 hashes,
then publish through a separate guarded KIOS phase.

Future synthetic sensitivity experiments must keep
their results explicitly separate from physical claims
and from the currently denied health-model authority.
