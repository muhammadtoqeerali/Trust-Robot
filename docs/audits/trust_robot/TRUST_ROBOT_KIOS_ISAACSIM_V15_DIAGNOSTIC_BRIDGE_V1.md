# TRUST-ROBOT KIOS Isaac Sim V15 diagnostic bridge

Status: **offline synthetic diagnostic bridge passed**.

## Implementation

This milestone adds a read-only adapter for the preserved Isaac Sim
V15 recording, and a controlled synthetic intervention comparison.

It reuses the existing frozen SE3 camera feature extractor after
Pillow RGB-to-grayscale conversion, and the exact existing SE3 IMU
vector-norm feature extractor. Frozen source modules were not modified.

Camera: 6 recorded frames. IMU: 90 recorded samples. LiDAR: 6
recorded clouds.

The LiDAR output contains point count, centroid and axis spans only.
These are **new synthetic structural diagnostics**, not the frozen
Phase-4 paired-registration/ICP five-feature contract.

## Controlled synthetic interventions

The paired variant deterministically applies:
- camera blackout to recorded frame 3;
- every-other-point LiDAR sparsification to recorded frame 3;
- an added 3.0 m/s2 x-axis acceleration bias at recorded IMU step
  45.

The clean source files are not modified. Interventions are performed
in memory and the derived feature files remain outside Git.

## Provenance

Source commit: `99816844a4344f14ac201d2d26e05a645932d8ca`

Module SHA-256: `07e150502446cbb3ea65592964ae35addfe974caeb0232f10d4b918bd3ebcdf9`

Test SHA-256: `21af4cbbe63766084b8f91839e94d3530d5bd3d5d7348ec0316bf550ff98f03f`

Derived output manifest SHA-256:
`55381f48bd21fb2c1d5ddc422ec77fe69958c605a7d0e003bd88ae82d95d239d`

The adjacent JSON evidence file records the six derived-output hashes
and the original V15 compact-evidence binding.

Two complete derivations were byte-compared before output publication.

## Reproduction

Use a project-local Python environment with NumPy and Pillow:

    PYTHONPATH=src python -B src/trust_robot/isaacsim_v15_diagnostic_bridge.py RECORDING_DIR experiments/isaacsim_v15/compact_evidence_v15.json NEW_OUTPUT_DIR

Run tests with:

    PYTHONPATH=src python -B tests/trust_robot/test_isaacsim_v15_diagnostic_bridge.py -v

## Scientific boundaries

These are synthetic, controlled intervention facts only, **not**
admissible empirical healthy/degraded/unusable training labels.

Simulation read-step times and sensor-reported times do not establish
physical capture timing or cross-modal synchronization.

No independent ground truth was used. No localization estimator,
health classifier, calibrated probability, safety controller or real
robot was evaluated in this milestone.

No physical LiDAR motion fidelity, deskewing or realistic attack
resilience has been established. No ATE or RPE has been calculated.

This work does not change or reopen existing SE3/Phase-4 freezes,
TRAIN/validation/confirmation partitions or the blocked SE4 empirical
health-supervision frontier.
