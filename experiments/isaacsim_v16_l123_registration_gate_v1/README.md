# TRUST-ROBOT KIOS V16 L1–L3 registration and fail-closed factor gate

**Scope:** SHA-verified offline engineering diagnostics using the KIOS V16.28
synthetic sensor-frame LiDAR recordings. This is **not** a localization
accuracy, independently referenced 6-DoF pose, sensor synchronization,
health-label, or authorization checkpoint.

Read `AGENTS.md`, the V16.28–V16.29 recovery README in
`experiments/isaacsim_v16_recovery_v1/README.md`, and
`docs/audits/trust_robot/TRUST_ROBOT_KIOS_V16_L1_L2_L3_REGISTRATION_GATE_V1.md`.

- L1 (`code/phase_l1_registration.py`): reuses the unmodified frozen Phase-2
  registration and Phase-4 feature extractor. Six genuine GMO-derived XYZ
  scans, 84 points. Ten clean/sparsified pair attempts: eight diagnostic
  registrations; two rejected because final scan has four points. An
  **eight-point engineering gate** was used in this experiment; it is not a
  calibrated health or scientific factor-admission threshold.
- L2 (`code/phase_l2_ambiguity.py`): four clean registration candidates,
  weak rotational information, point geometry anisotropy, and deterministic
  coordinate-perturbation sensitivity tests. The perturbations (0.5 mm and
  2 mm maximum per-coordinate magnitude) are synthetic diagnostics, **not
  calibrated sensor-noise statistics**. Fit residuals are not pose accuracy.
- L3 (`code/phase_l3_factor_gate.py`): ten admission requests all **DENIED**;
  eight intentionally tampered evidence examples rejected. None of the
  uncertain registration poses, factor matrices or timestamps is emitted to
  an estimator as an authorized factor. This is a conservative engineering
  gate, not a frozen scientific health threshold.

SHA-bound copies of the three local, validated reports are in `evidence/`.
The exact byte-preserved source files are in `code/`. The V16 source/report
and historical recordings are **not copied or modified** by this package.
The package's `checkpoint_manifest_v1.json` and `SHA256SUMS.txt` bind inputs
and outputs. The `verify_checkpoint.py` script checks the local package and
exercises the eight negative L3 tampering tests without modifying inputs.

## Reproduce offline on KIOS (new output directories only)

```bash
W=/home/kios/TRUST_ROBOT_ALI
R=$W/github_checkout_v15
PY=$W/venvs/isaac_v15_odometry_v1/bin/python
PKG=$R/experiments/isaacsim_v16_l123_registration_gate_v1
REC=$W/experiments/isaacsim_v16_readiness_capture_v1
V16=$R/experiments/isaacsim_v16_recovery_v1/evidence/readiness_capture_report_v1.json
PYTHONPATH=$R/src "$PY" -B "$PKG/verify_checkpoint.py" "$V16"
# Create three NEW local experiment output directories before running:
# PYTHONPATH=$R/src "$PY" -B "$PKG/code/phase_l1_registration.py" "$REC" "$V16" NEW_L1_OUT
# PYTHONPATH=$R/src "$PY" -B "$PKG/code/phase_l2_ambiguity.py" "$REC" "$PKG/evidence/registration_transfer_report_v1.json" "$V16" NEW_L2_OUT
# PYTHONPATH=$R/src "$PY" -B "$PKG/code/phase_l3_factor_gate.py" "$PKG/evidence/registration_transfer_report_v1.json" "$PKG/evidence/l2_registration_ambiguity_report_v1.json" "$V16" NEW_L3_OUT
```

Reproduction commands above should be run offline in a private read-only
sandbox, with only new output directories writable. No simulator or GPU is
needed. Do not overwrite the frozen original local recording, L1–L3 reports,
any V15/V16 experiments, frozen Phase-2/Phase-4 code, or Git history.

**Next gate:** independently qualified timing, calibration, geometry and
reference evidence are required before actual estimator factor admission.
SE4 real health-model training and validation/test access remain blocked by
their existing scientific prerequisites. No change to TRAIN/validation/test
partitions, ATE/RPE claims or physical robot authorization is made here.
