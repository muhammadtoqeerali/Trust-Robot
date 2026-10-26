# R130 scientific and publication-boundary audit

## Evidence tiers

1. Publisher-provided Hilti calibration files were acquired from an
   immutable repository revision and SHA256-frozen off Git on UNIVER.
2. Original calibration statements are source-authenticated, but that
   alone does not prove correspondence to every physical capture.
3. Safe YAML inspection and deterministic geometric checks established
   internal consistency for the five camera declarations and six
   rigid transformations.
4. R130-B3's executable verifier and deterministic detailed report
   are replayable only with their separate UNIVER source inputs.
5. The R130-B4 independent NumPy audit is supported by operator-posted
   output. Its independent source was not archived or authenticated.
6. The reduced R130-B5 handoff and KIOS B6C-R1 receipt are hash-bound,
   with a replayable portable integrity/scope verifier.

## Remaining scientific limitations

- Recorded IMU `imu_sensor_frame` and publisher YAML `imu`
  have no independently demonstrated frame-identity bridge.
- Time-shift declarations are not measured hardware-clock proof.
- Neither publisher extrinsics nor sensor-model consistency
  establishes independently verified physical calibration accuracy.
- The dense Hilti reference is not automatically an independent
  full-6DoF ground truth source for an estimator sharing its inputs.
- No original ground truth was accessed in R130; reference independence,
  coordinate frames, timestamp semantics and allowed scoring
  remain unqualified.
- No physical real-pose factors, health labels, thresholds, trained
  health model, ATE/RPE or safety-control decisions are authorized.
- Frozen M2DGR 22/7/7 partitions, sealed confirmation_test and
  eleven CLOSED scientific gates remain unchanged.

## Redistribution boundary

This document is an original technical narrative. It does not contain
publisher YAML bytes, their numerical parameter arrays, complete
derived calibration reports, raw ROSbags or ground-truth payloads.

Hilti-Oxford upstream attribution: Hilti-Research.
Dataset license: CC BY-NC-SA 3.0:
https://creativecommons.org/licenses/by-nc-sa/3.0/
Dataset: https://huggingface.co/datasets/Hilti-Research/hilti-slam-challenge-2022
Citation DOI: https://doi.org/10.1109/LRA.2022.3226077

The repository presently has no tracked conventional LICENSE/NOTICE
file under the R130-B7 inventory. This is not a legal conclusion
about ownership or redistribution rights for other repository files.

The B5 source package is marked not authorized for public Git
publication. This document does not overturn that status.
This review is not permission to publish the B5 handoff, original
publisher calibration files or detailed derived parameter reports.
