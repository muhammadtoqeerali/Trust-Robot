# TRUST-ROBOT | R135-A40-2 | Controlled synthetic intervention diagnostic benchmark

**Status:** versioned, deterministic *synthetic engineering benchmark*, derived from private R135-A40-1. Not independently measured physical fault/attack evidence, health labels, estimator evaluation, or robot control.

## Reproducible scope

- `src/trust_robot/synthetic_diagnostic_stress_v1.py`: byte-identical to private A40-1 candidate (SHA-256 `dc7cbf0740d2a85c0207e84f97cc89988ac4716f5e489a39662739e866d0e3b0`); requires `unlabelled_multimodal_diagnostics_v1.py` published in R135-A39-7.
- `tests/trust_robot/test_synthetic_diagnostic_stress_v1.py`: the 16 private synthetic tests, with only the import rewritten from the private top-level module to `trust_robot.synthetic_diagnostic_stress_v1`.
- Reproduce: `PYTHONPATH=src python3 -m unittest discover -s tests/trust_robot -p 'test_synthetic_diagnostic_stress_v1.py' -v`.
- R135-A40-1 KIOS report: 14 paired manufactured-fixture scenarios, three expected input-schema rejections, 16/16 new tests and 89/89 existing focused regressions passed. Private receipt SHA-256: `af57f23efc676493198352704d5b7ef5b0aa1475749037d505f8aeadb24d8859`; private receipts/logs remain outside Git.

## Intervention semantics

The deterministic control has 12 left and 12 right synthetic camera records, 16 manufactured IMU vectors, and four synthetic LiDAR layout records. Each of 14 interventions starts from a fresh deep-copy control. Scenarios cover camera zero payload/startup, recorder interarrival burst, synthetic message removal and numeric-header mutation/duplication; IMU bias, arithmetic noise, stuck values, nonfinite input; and LiDAR point-slot and layout changes. Three malformed cases are rejected rather than diagnosed.

Exported results include only bounded aggregate deltas and case identifiers. Scenario-design intent (`BENIGN_FAULT_SCENARIO` versus `ADVERSARIAL_SCENARIO`) is **not inferred from diagnostic measurements**. Two indistinguishable zero-payload transformations with opposite intent tags produce identical diagnostic deltas. Some interventions are not observable by these features. No camera blur or stale-content feature, geometric LiDAR validity, physical timing binding, causal attack attribution, probability calibration, fault severity operating point, physical factor admission or actuator capability is established.

## Scientific and safety freeze

- Real independently accepted `healthy/degraded/unusable` measurement-role labels: **zero**; real trained calibrated health model: **not qualified**.
- M2DGR eleven physical evidence gates: **ALL CLOSED**; 22 TRAIN / 7 validation_calibration / 7 SEALED confirmation_test base-trajectory partitions unchanged and not accessed.
- Numeric ROS header equality and recorder arrival remain physically **unqualified clock axes**, not exposure synchronization, dropped-frame verification, or actual sensor failure.
- Synthetic condition tags are neither real sensor-health ground truth nor attack attribution. No physical robot sensor, real data, Nova/UNIVER workstation, ROS recording, estimator factor, safety action, stop or return-home command is used or authorized.
- Source and synthetic tests are suitable for future offline robustness/ablation engineering only. Any real physical intervention, independent witness acquisition, operational health model or factor admission requires separate evidence and approval gates.

**Next scoped research step (proposed R135-A40-3):** extend the fully offline manufactured-fixture study with falsification/observability coverage and explicit non-detection cases; preserve all scientific boundaries before choosing subsequent ablation experiments.
