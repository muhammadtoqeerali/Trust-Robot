# TRUST-ROBOT KIOS V16 L4-L9 geometry and stability checkpoint

Date: 2026-10-15
Predecessor: 612c71ccc6b70abbe3e35af19bf9e7b8dc052b98

Status: synthetic engineering qualification only.

## L4: Analytic beam geometry

Original analytic rotational-information ratio:
0.000018217205284410183

Hypothetical permuted 16-beam layout:
0.13613967568317129

This was an analytic comparison, not a simulator measurement.

## L5: Candidate acquisition configuration

A separate versioned KIOS experiment changed the emitter elevation
permutation in the USD scene, acquisition constructor and runtime
attribute assertions. The baseline V16.28 scene was preserved.

Exact candidate source, USD scene and preparation receipt are SHA-bound.

## L6: Actual synthetic capture

Six camera frames, six LiDAR scans, 130 IMU samples and 130 USD pose
records passed local offline validation.

LiDAR point counts: [16,16,16,16,16,2].
Total valid points: 82.

Median structural rotational-information ratio of first five scans:
Original: 0.0005009572258707657
Candidate: 0.1364939507216398

Diagnostic improvement: approximately 272.47 times.
The final two-point scan remains sparse and unsuitable for 3D geometry.

## L7: Registration sensitivity

At 2 mm maximum deterministic coordinate perturbation:

Original median rotation change: 25.794354614625377 degrees.
Candidate median rotation change: 0.3080523086662964 degrees.

No calibrated sensor noise was used.

## L8: Multipattern registration

192 perturbation registrations per derivation, using 12 predetermined
patterns, two amplitudes, four pairs and two scan layouts.

The run completed with no registration failures and deterministic
re-derivation.

Candidate baseline ICP translation magnitudes across the four pairs:
[0.0451539,0.0392290,0.0413223,0.0404536] metres.

Scripted USD displacement was approximately 0.04 metres per interval.
This is internal synthetic consistency, not independent reference accuracy.

## L9: Forward/reverse and skip-frame closure

Eight bidirectional pair attempts and six skip-frame attempts passed.

Original median forward/reverse rotation closure: 2.7327916846 degrees.
Candidate median: approximately floating-point zero.

Original median skip-frame rotation closure: 33.88168226 degrees.
Candidate median: 0.0091809428 degrees.

Original median skip-frame translation closure: 0.23941396 metres.
Candidate median: 0.0000785919 metres.

Closure is internal consistency, not independent localization accuracy.

## Scientific restrictions

No trusted physical capture timestamp, independent reference ground truth,
calibrated cross-sensor synchronization, physical sensor validation,
ATE/RPE, supervised health labels or authorized estimator pose factors
have been established.

M2DGR split rules and existing SE2/SE4/SE5/SE9 scientific gates remain
unchanged.

## Reproducibility and next implementation

Exact code, experimental candidate scene, metadata and compact reports:
experiments/isaacsim_v16_l4_l9_geometry_stability_v1/

Raw sensor recordings remain locally on KIOS.

Next: L10 should investigate the loss of valid returns at the end of the
scripted trajectory, using a separate experiment and predeclared safeguards.
Never overwrite the successful V16.28 or L5/L6 historical recordings.
