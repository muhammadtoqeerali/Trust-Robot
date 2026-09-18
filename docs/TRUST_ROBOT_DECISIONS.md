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

## D-009 — Phase-3E does not create a successor trajectory manifest

Decision: retain the Phase-3D trajectory manifest byte-for-byte as the
authoritative trajectory manifest after the Phase-3E reference temporal
association checkpoint.

Reason: the current trajectory-manifest schema has no explicit
reference-to-estimator temporal-association field. Updating per-sensor
synchronization methods would conflate sensor-to-sensor synchronization with
reference timing, while adding an ad-hoc reference field would violate the
schema.

## D-010 — Phase-3E characterization does not authorize timing tuning

Decision: Phase-3E numeric overlap, rotation-content correlation, translation
diagnostics, and RTK/GNSS receiver-UTC coordinate evidence are
characterization only.

No reference interpolation, nearest-neighbor pose-admission tolerance, fixed
reference offset, lag scan, automatic timing-validity threshold, or evaluation
interval may be derived from these observations.

Reason: the evidence is family- and observable-dependent. Mocap rotational
agreement is weak/heterogeneous; Leica cannot support the native LiDAR-interval
translation diagnostic without interpolation; translation results change
substantially with temporal-support definition; and RTK/INS receiver-UTC
coordinate compatibility does not establish pose measurement-time semantics.

## D-011 — Calibration artifact integrity is not sensor calibration

Decision: explicitly separate calibration-related artifact roles into
`artifact_integrity`, `calibration_provenance`, and
`sensor_calibration_verification`.

Legacy trajectory-manifest calibration artifacts default to
`artifact_integrity`.

Reason: the 36 existing M2DGR `calibration_artifacts` entries are raw-bag SHA
integrity artifacts. Their verified status establishes file integrity, not
camera intrinsics, sensor extrinsics, lever arms, or any other physical
calibration quantity.

A `sensor_calibration_verification` artifact must be independently verified and
must explicitly identify the streams or frames to which the claim applies.

Historical manifests remain byte-identical.

## D-012 — Rotation content support does not upgrade full calibration

Decision: record the frozen 28/28 D435i-IMU fixed-hypothesis result as
independent released sensor-content support for the published relative-rotation
convention, while keeping full calibration unverified.

Do not infer translation, camera intrinsics, camera/LiDAR calibration,
HandsFree/LiDAR full extrinsics, reference lever arms, synchronization, or
evaluation readiness from this rotational-content result.

No calibration successor trajectory manifest is created.

Reason: the diagnostic compares a pre-existing published rotation against fixed
identity and transpose alternatives without fitting a rotation or lag. It
strongly challenges orientation convention but does not observe the complete
set of physical calibration quantities required by the estimator/reference
contract.

## D-013 — Freeze the M2DGR partition prospectively before estimator scoring

Decision: freeze the deterministic metadata-only M2DGR V2 partition as:

- 22 `train`;
- 7 `validation_calibration`;
- 7 `confirmation_test`.

Create
`manifests/m2dgr_trajectory_manifest_v1_split_freeze_v1.json`
as the current authoritative trajectory manifest.

The successor differs from the Phase-3D manifest only in the 14 trajectory
`split` fields that move records out of `train`, plus the manifest digest.

The earlier metadata-split V1 candidate is rejected before estimator outcomes
because it accidentally removes complete scenario and collection-date
categories from training.

Reason: future data-selected protocol parameters require a partition that is
fixed before estimator outcomes are inspected. The accepted V2 split preserves
all observed scenario and collection-date categories in training and does not
use estimator errors, ATE, RPE, timing-correlation scores, calibration scores,
reference pose values, or author-reporting membership to choose membership.

This decision supersedes D-009 only for the identity of the *current*
authoritative manifest. D-009 remains the historical record that no successor
manifest was created at the Phase-3E checkpoint.


## D-014 — A validation split does not create missing physical evidence

Decision: the frozen `validation_calibration` partition may be used only for
future choices that are scientifically selectable after their physical
prerequisites are established.

Its existence does not authorize:

- nearest-neighbor pose association;
- reference interpolation;
- a reference-to-estimator fixed offset;
- an association tolerance;
- an evaluation interval;
- SE(3) or Sim(3) alignment;
- trajectory scoring.

It also cannot establish timestamp physical-event semantics, a common physical
clock, reference sensor origin, missing extrinsics, continuous reference
validity, or any other physical fact.

The `confirmation_test` partition is closed to future model, threshold,
association, alignment, and protocol selection.

Reason: a validation partition prevents outcome leakage when selecting a
legitimate tunable convention. It cannot transform an unresolved physical
quantity into a tunable parameter.
