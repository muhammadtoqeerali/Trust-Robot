# TRUST-ROBOT Decision Log

## D-001 — Preserve inherited RC-RGD-IMU code

Decision: keep `src/imu_reliability/`, inherited experiments, historical configs, and embedded runtime as historical/reference implementation.

Reason: useful engineering provenance must not be confused with new TRUST-ROBOT science.

## D-002 — Introduce a separate TRUST-ROBOT namespace

Decision: new scientific code begins under `src/trust_robot/` and is added incrementally.

Reason: a wholesale rename would incorrectly relabel HAR/IMU-specific science as multimodal robotics science.

## D-003 — Protocol before dataset acquisition

Decision: Phase 1 defines dataset/reference/synchronization/frame/split contracts before downloading or preprocessing datasets.

Reason: reference leakage, frame ambiguity, synchronization assumptions, and split contamination must be prevented structurally.

## D-004 — Separate proposal status from local readiness

Decision: the dataset registry records proposal-level availability/role separately from locally verified readiness.

Reason: proposal statements must not be silently converted into claims that a local release, stream, calibration, or reference has been verified.

## D-005 — Reference streams are not estimator inputs

Decision: a concrete stream identifier used to construct reference truth cannot simultaneously be an evaluated estimator input.

Reason: reference-input leakage is scientifically invalid. Independent sensor instances must have distinct stream identifiers and provenance.

## D-006 — Base-trajectory lineage controls splitting

Decision: every clean/corrupted derivative carries a `base_trajectory_id`, and all records sharing that base ID must remain in one split.

Reason: derivatives of one trajectory are statistically dependent.

## D-007 — No robotics-stack installation in Phase 1

Decision: do not install ROS, GTSAM, Open3D, OpenCV, or other large robotics dependencies during Phase 1.

Reason: Phase 1 contracts are dependency-light; estimator/front-end dependencies belong to Phase 2 after an explicit architecture decision.

## D-008 — Phase-1 protocol is initially a candidate

Decision: Phase-1 protocol/config files use the `_candidate` suffix until local dataset/access evidence and validators are reviewed.

Reason: protocol freezing must follow evidence, not precede it.
