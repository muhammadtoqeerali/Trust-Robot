# KIOS S1–S5 core 6DoF scientific readiness checkpoint

Date: 2026-10-16. Parent commit: `79a2abf6de6ff68df23de8bd04b538ce0c95b46b`.

S1 inventoried sixteen existing estimator source/test pairs and confirmed the frozen M2DGR 22/7/7 trajectory partition with 140 unqualified stream synchronization entries. No recordings were read.

S2 repaired the CPU test environment by disabling incompatible user-site NumPy (system NumPy 1.21.5 / SciPy 1.8.0). Nine selected estimator suites yielded 104 passing synthetic regression tests; eight unauthorized recorded-factor attempts were denied.

S3 introduced a TRAIN-only, metadata-only input contract for four distinct streams, including separate camera-IMU and handsfree-IMU sources. 41 unit tests passed. Header timestamps were illustrative caller assertions only.

S4 preserved lineage, timing, and calibration uncertainty with 32 still-closed requirements. 55 unit tests passed. The independent verifier was corrected to compare JSON gate-key sets rather than key order; the original matrix/report were unchanged. Bag SHA256 verification is not calibration; partial camera–IMU rotation evidence is not full extrinsic verification.

S5 verified the evidence chain and recorded 32 rejected false-promotions. Its docstring matcher was corrected to normalize whitespace without modifying repository estimator code.

The checkpoint archives 28 SHA-pinned Python, JSON and JUnit XML artifacts, along with this README, checkpoint manifest and standalone verifier. It does not archive the superseded S4/S5 verifier backups, raw sensor recordings, private SQLite, derived scientific pose factors, or trained health labels.

Scientific decision: **development-only**. Real sensor factor execution, M2DGR ATE/RPE scoring, physical cross-modal synchronization, full extrinsic calibration and empirical three-state health training remain unqualified.

Next: **S6 CPU-only manufactured-fixture support for independent camera and LiDAR constraints on the same estimator edge**, preserving separate ownership/covariances and the existing 104-test regression and fail-closed recorded-factor boundaries. S6 is not physical sensor qualification.

Verification: `python3 -B experiments/trust_robot_s1_s5_core_6dof_readiness_v1/verify_checkpoint.py`
