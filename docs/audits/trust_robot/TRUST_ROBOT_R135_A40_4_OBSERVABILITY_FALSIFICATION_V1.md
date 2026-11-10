# TRUST-ROBOT | R135-A40-4 | Synthetic observability falsification checkpoint

**Scientific role:** reproducible offline manufactured-fixture engineering study of representation blind spots, not independently measured physical detection performance, sensor-health supervision, attack attribution, calibrated uncertainty, or controller behavior.

## Reviewed implementation and reproducibility

- `src/trust_robot/synthetic_observability_falsification_v1.py` is byte-identical to the private A40-3 candidate (SHA-256 `cca19baa8195e38edd4e0b833ac400404accfd37cfdc03d01abe1eba51747bb5`).
- `tests/trust_robot/test_synthetic_observability_falsification_v1.py` contains the 24 private tests with one adaptation: import from `trust_robot.synthetic_observability_falsification_v1` instead of the private top-level module.
- Reproduction: `PYTHONPATH=src python3 -m unittest discover -s tests/trust_robot -p 'test_synthetic_observability_falsification_v1.py' -v`.
- Private A40-3 execution receipt SHA-256: `e167f438d68950f96c9f1f594878e0621d95c5946762a5f20747f92d5bffe5c7`; candidate manifest SHA-256: `8e90d6901ee2afedd6c478f674c1c1b7782003489cbc5dcfab149e3a1bf2039a`. Private receipts, source-bag traces, credentials and payloads are not committed.

## Falsification results (manufactured data only)

Nineteen paired control/treatment cases were executed with published A39-7 and A40-2 descriptive software. Eight transformations produced no change in the represented diagnostic aggregates; six changed detailed aggregates but not the restricted public projection; five changed the public projection. This is a deliberately designed coverage/observational-equivalence experiment, **not** an empirical sensitivity, false-negative, ROC/AUC, or physical health accuracy measurement. Canonical aggregate SHA-256: `93e24b41941c64f5c6d3a9d82ff52c2a229da35abffe154d9978845b31972ef7`.

No-change examples include synthetic common timestamp shifts, equal-norm IMU vector direction changes and redistribution of LiDAR point slots while total slots remain fixed. Detail-only examples include IMU norm changes, limited recorder timestamp perturbations, and reported LiDAR field-layout changes; the public projection omits these distinctions. Public changes include manufactured zero-payload flagging, numeric-header overlap changes, record-list removal, delivery bursts and reported LiDAR slot removal. The source explicitly lists *unrepresented, not simulated* dimensions (camera blur/stale pixel content, LiDAR return geometry, manufacturer health register and physical-clock binding); they are not counted as missed detections.

## Frozen boundaries

Zero independently accepted real `healthy/degraded/unusable` measurement-role labels. No trained, independently calibrated physical health model. All 11 M2DGR real-fusion evidence gates remain CLOSED and frozen 22 TRAIN / 7 validation_calibration / 7 SEALED confirmation_test partitions were not accessed. Numerical ROS headers and recorder arrivals do not prove exposure-time synchronization. No real data, Nova, UNIVER, robot action, estimator factor, physical intervention, or attack-causation conclusion is authorized. Any subsequent A41 shadow reliability decision policy must be explicitly synthetic, non-operational, and independently gated.

**Next proposed research stage:** A41-1 offline shadow-only reliability-policy ablation informed by these observability limits, without creating empirical health probabilities, qualifying real factors, or enabling physical control.
