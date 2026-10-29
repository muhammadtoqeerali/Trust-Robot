# R135-A9: Distinct synthetic metric depth-camera source

Status: **UNTRUSTED_SYNTHETIC_OBSERVATION_ONLY**.

## Purpose

Convert the read-only R135-A8 feasibility calculation into
a reproducible source module and a tested software contract.

This is an analytic development fixture, not a physical
sensor-data processing or scientific evaluation result.

## Observation generation

A fixed virtual scene contains 72 manufactured 3D points.

A shared manufactured trajectory provides camera poses
for projection into five synthetic frames.

Each simulated frame supplies:
- manufactured pixel coordinates;
- manufactured metric depth;
- fixed camera-specific numerical noise;
- optional pair-local bias on the current observation.

Rigid 3D correspondence alignment supplies a relative
SE(3) motion packet through the existing typed synthetic
factor interface.

The virtual depth is essential to metric translation.
Monocular-only metric scale is not established.

## Source distinction

The generator does not import or copy LiDAR registration
factors, LiDAR point clouds, or LiDAR solver outputs.

Its camera noise generator is separate from the LiDAR
fixture noise generator.

However, both development streams share the same
manufactured motion model.

This constitutes different synthetic observation
construction, not independent physical sensor evidence.

## Frozen scope

Seven local graph edges and three observation modes:
ideal, noisy, biased.

21 manufactured camera-relative-motion packets.

The numerical camera model, scene, seeds and selected
perturbations are fixed for reproducibility.

The bias is pair-local and not a validated time-persistent
hardware bias or measured sensor fault.

## Evidence restrictions

The generator does not:
- read real camera, IMU or LiDAR observations;
- admit recorded sensor factors;
- execute the 15D estimator;
- compute recorded-reference ATE or RPE;
- train or execute a sensor-health classifier;
- generate physical health labels;
- select factor information weights;
- calibrate physical camera extrinsics;
- certify camera/IMU clock synchronization;
- establish physical observability;
- establish independent real-world camera redundancy.

Manufactured analytic motion can be used inside unit
tests to check generator geometry. Such comparisons
do not constitute real ground-truth validation.

## M2DGR protection

The frozen 22/7/7 partition is unchanged.
No validation-calibration or confirmation-test records
are accessed.

All 11 scientific admission gates remain CLOSED.

## Next stage

After 18 new unit tests and existing regressions pass,
publish the exact three-file implementation checkpoint.

Then separately investigate controlled injection of
manufactured camera packets into the already-published
15D factor-factory interface.

Actual synthetic optimizer behavior must be evaluated
without claiming independent physical sensing, sensor
health inference or physical localization recovery.
