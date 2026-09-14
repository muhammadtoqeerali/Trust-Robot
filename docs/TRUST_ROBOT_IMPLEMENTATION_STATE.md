# TRUST-ROBOT Implementation State

Status: Phase 1 in progress
Protocol state: candidate, not frozen

## Physical deployment target

The primary eventual physical deployment and validation platform is a local dog/quadruped robot.

The current registry label `KIOS_QUADRUPED` is provisional until the actual robot identity, onboard compute hardware, sensor suite, calibration, synchronization, and reference instrumentation are frozen from collected evidence.

The core TRUST-ROBOT implementation must remain platform-independent around camera, LiDAR, and IMU localization/diagnostics rather than embedding quadruped-specific assumptions into the main estimator.

Future local quadruped data may be used in two scientifically separate roles:

- explicitly assigned development/training/validation-calibration trajectories;
- strictly disjoint held-out physical confirmation trajectories.

The final held-out quadruped trajectories must not be used for training, model selection, calibration, fault/attack severity selection, health thresholds, suppression/recovery thresholds, fallback thresholds, or other validation-selected decisions.

Quadruped proprioception is optional and will be added only if the actual platform exposes verified scientifically usable streams. Such signals must remain a separable branch rather than a requirement of the core camera/LiDAR/IMU pipeline.

A drone is an optional future cross-platform possibility, not a current project requirement. Drone-specific design constraints must not drive current implementation unless that platform is later explicitly adopted.


## Phase 0 closure

Phase 0 passed with documented limitations.

Verified inherited baseline:

- `src/imu_reliability/` imports successfully under the historical `protechto311` Python 3.11 environment.
- `tests/test_integrity_core.py`: 11/11 passed.
- `tests/test_p0_injection.py`: 17/17 passed.
- One inherited historical script, `experiments/08_cross_dataset_analysis/plot_reliability_analysis.py`, contains a syntax error caused by embedded shell heredoc text.
- Full inherited pytest collection was not executed because pytest is not installed in the historical environment.
- Historical absolute workstation paths remain intentionally preserved as research provenance.
- At Phase 0 closure, no TRUST-ROBOT dataset had yet been configured or downloaded in the new workspace.

## Current Phase 1 objective

Define and validate the data-interface contract while primary-dataset acquisition and readiness auditing proceed. Localization implementation remains gated on Phase-1 evidence.

Phase 1 covers:

- dataset registry;
- local-readiness status;
- M2DGR acquisition and readiness audit;
- dimension- and interval-aware reference validity;
- synchronization conventions;
- coordinate/frame rules;
- reference-source independence;
- trajectory lineage;
- trajectory-disjoint splitting;
- anti-leakage invariants;
- machine-testable validation rules.

## Current non-goals

Phase 1 does not:

- freeze the protocol before acquisition/reference audits complete;
- choose the estimator backend;
- install ROS/GTSAM/Open3D/OpenCV;
- implement visual/LiDAR/inertial front ends;
- implement modality-health models;
- define fault magnitudes or attack budgets;
- modify inherited RC-RGD-IMU scientific code.

## Current M2DGR acquisition state

- Full M2DGR acquisition is running on the workstation independently of the user's laptop.
- Official sequence links are derived from the upstream M2DGR repository and the upstream commit is recorded by the acquisition workflow.
- SharePoint session establishment and HTTP byte-range resume support have been verified.
- Representative RTK/INS, Leica, and motion-capture references have been audited.
- Leica zero orientation placeholders are not treated as rotational ground truth.
- Motion-capture reference quality is not assumed uniformly valid; raw reference files remain immutable and derived validity artifacts will identify admissible dimensions/samples or intervals.
- M2DGR timing-policy evidence from `gate_01` and `gate_02` supports verified sensor `header.stamp` as the measurement-time basis for audited candidate estimator streams; rosbag record timestamps remain transport/provenance diagnostics rather than measurement time.
- No global fixed sensor time offset is applied by default; any future fixed offset requires explicit evidence and versioned provenance.
- Multimodal association and scoring must use required-stream sensor-header time overlap intersected with independently valid reference coverage for the required scoring dimensions.
- Numerical association tolerance remains unresolved, and M2DGR synchronization is not yet marked fully verified.
- Full dataset acquisition remains in progress, so the Phase-1 protocol is not frozen.

## Current artifacts

Candidate artifacts introduced by Phase 1:

- `docs/trust_robot/data_protocol_v1_candidate.md`
- `configs/trust_robot/dataset_registry_v1_candidate.yaml`
- `configs/trust_robot/local_paths.example.yaml`
- `src/trust_robot/data_contracts.py`
- `tests/trust_robot/test_data_contracts.py`

The candidate protocol must not be called frozen until the workstation dataset/access audit and tests have been reviewed.
