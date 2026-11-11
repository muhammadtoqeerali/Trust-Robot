# TRUST-ROBOT | R135-A44-4 | Observation-aware numerical-support shadow

**Status:** reproducible offline synthetic engineering, not physical sensor health, validated real measurement factors or a safety controller.

## Motivation and reused core

R135-A44-1 reconciled previous unlabelled Nova diagnostic work with installed camera/IMU/LiDAR ROS package candidates; it did **not** record new data. A44-2R recovered and ran the earlier A41/A42 synthetic experiments and frozen marginalized 15D LiDAR–IMU solver. Its strict numerical-support rule accepted the manufactured LiDAR-dropout fixture because each solver window retained some current LiDAR factors. Numerical graph support is not the same as complete scan availability or verified physical observability.

The published `observation_aware_support_shadow_v1.py` reuses `trust_robot.analytic_marginalized_fusion` without modifying its factors, covariances, weight rules, optimization or Schur prior. No earlier experimental weighted derivative or source-blind attribution model is promoted.

## Bounded scientific result

The *synthetic* node-frame sequence is `(0, 2, 4, 6, 8)`, with four graph intervals. Both endpoints must have an available scan for a shadow interval to be eligible; this rule reads the known manufactured fixture mask independently of the fitted Jacobian. In the `lidar_dropout` fixture, node frame `4` is missing, so synthetic shadow windows `2` and `3` are held. The frozen solver's numerical status remains `NUMERICALLY_SUPPORTED` for all four windows. The `clean` and `accel_bias` fixtures remain eligible for **synthetic shadow only**, not physically healthy. The accelerometer-bias condition is not inferred or classified by this rule.

The module requires exact fixture provenance, chronology, presence/count consistency and frozen auxiliary/factor-conditioning gates. It rejects recorded/physical inputs, unexpected source metadata and altered estimator trajectories. This shadow never suppresses an actual sensor or commands a robot.

## Reproduction and evidence provenance

- Reviewed A44-3 KIOS result: 17 newly written shadow tests plus 165 recovered A41/A42 private tests plus 101 core regression tests = **283 passing tests**; private A44-3 receipt SHA-256 `0107753ade6e762366fb38c70e9413b563664c560879e50c42578427e9ef29bb`.
- This A44-4 package preserves the A44-3 candidate implementation byte-for-byte; its 17 tests change only the module import path and add three full frozen-solver integration tests. Run `PYTHONPATH=src python3 -B -m unittest discover -s tests/trust_robot -p 'test_observation_aware_support_shadow_v1.py' -v` and the selected A41/A42 and published-core regression suites.
- Reusable A39 Nova recording diagnostics, A41/A42 source reports and all A44 private receipts remain off Git; no raw images, point clouds, ROS bags, workstation-private paths or individual sensor payloads are committed.

## Hard limitations

No independently accepted real `healthy/degraded/unusable` labels (zero), calibrated three-class health model, verified hardware capture clock, physical extrinsics, independently measured 6DoF GT, operational reliability-aware factor admission, robot control, stop/return-home or physical performance claim. Header timestamp agreement is not physical exposure sync. Synthetic dropout flags are provided by a manufactured fixture and are **not available as independently trusted real measurements**. This conservative shadow is an offline diagnostic policy that may hold with partial but usable geometry; its costs and false-positive operating point are not calibrated. The sealed M2DGR confirmation partition was not accessed; the frozen 22/7/7 split, eleven scientific gates and prospective external evidence requirements remain intact.

**Next:** keep studying identifiable synthetic failure cases and qualified data acquisition prerequisites, then separately design validated factor-conditioning integration without importing arbitrary A41/A42 development policy into live operation.
