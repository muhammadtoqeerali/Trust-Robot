# TRUST-ROBOT | R135-A46-4 | Synthetic joint-fault identifiability and abstention

**Status:** offline manufactured-data estimator integration. This is not real sensor-health supervision, a physical localization result, authorized Phase-7 consistency processing or robot control.

## Reused code and experimental scope

Three previously tested private A46 modules are published as an optional synthetic-only diagnostic bridge. They reuse the published separated-modality 15D estimator, factory-ledger guards, manufactured camera relative poses, manufactured LiDAR post-registration factors and synthetic IMU propagation. The original 15D solver is not modified. The code uses a local Python test mock to inject only manufactured LiDAR factor perturbations; no raw scans are reprocessed. A46-2's source is adapted solely to installed-package import paths; A46-1 and A46-3 source bytes remain unchanged.

## Findings and non-identifiability

In A46-1 (203 selected tests), six prescribed manufactured conditions were compared, with baseline/common-mode repeated for camera seeds 13 and 31 (eight solver runs). A common +0.125 m camera/LiDAR relative-translation shift leaves their pairwise discrepancy unchanged even though both factors have changed. This is not proof that *all* diagnostic systems will miss such faults.

A46-2RR (221 selected tests) built a third comparison from two manufactured IMU samples. Holding that derived IMU pose fixed makes the camera/IMU and LiDAR/IMU differences change under a common camera/LiDAR shift. Two additional thought-experiment counterexamples apply an identical additive shift to a **derived IMU pose proxy**, not to the IMU samples or the nonlinear estimator. This demonstrates algebraic non-identifiability of the three pairwise translation differences under a shared shift; it does **not** demonstrate a real simultaneous three-sensor attack.

A46-3 (237 selected tests) maps the eight already tested synthetic cases into descriptive changed/unchanged comparisons and known manufactured LiDAR scan-availability shadow holds. Its `ABSTAIN_UNCALIBRATED_REAL_HEALTH` is mandatory for all cases, including the clean manufactured control. No physical fault source, health probability or physical factor weighting is inferred or selected. A46-4 repeats the selected test suite with published package imports before any Git publication.

## Unchanged scientific gates

No Nova or UNIVER access, M2DGR partition use, raw images, point clouds, bags, recording, hardware clock or extrinsic qualification, independent real 6-DoF reference, training or real health labels, physical factor admission, emergency-stop or robot command. Eleven M2DGR scientific gates remain closed, 13 independent physical evidence requirements remain open, and 22 TRAIN / 7 validation_calibration / 7 SEALED confirmation_test partition remains frozen. A numerical solver solution or residual disagreement is not a validated localization or fault-diagnosis result.

**Next:** design and falsify uncertainty-aware factor-selection interfaces with strict source provenance and explicit abstention, and separately qualify physical timing/extrinsics/reference/health data before considering any real factor execution.
