# R132 — diagnostic-only sensor evidence adapter (candidate)

This package carries the **unchanged** R132-A2 SHA-256-pinned bridge source plus
an independently written, portable regression script. The source consumes the
existing hash-pinned R129 aggregate report for seven Hilti-Oxford Exp14 sensor
streams. It exposes only sensor topic names, modality identifiers and 33
feature-family names; it never returns the feature measurements themselves.

It is a descriptive software integration boundary, **not** a connection to the
S6 synthetic solver and **not** a physically qualified real-sensor factor path.
The callable endpoints for real factors and health labels always raise denial
exceptions. Existing S3/S4 recorded-factor gates remain unchanged and closed.

Evidence: R132-A2's candidate passed 8 structural and 6 API denials. A separate
R132-A3 verifier subsequently passed six raw-integrity and sixteen structural
mutations, ten API denials and two static old-gate checks. A4's portable test
rechecks the source/report pins and core denials. It does not replay original
raw sensor measurements or independently validate physical sensor calibration.

To run from a repository checkout, without any raw ROS bags:

    python3 -I -B experiments/trust_robot_r132_diagnostic_bridge_v1/test_r132_diagnostic_bridge.py "$PWD"

Original source inputs and source-system private checkpoints remain off Git.
No ground truth, train/test access, health probabilities, pose factors,
deskew, clock synchronization, ATE/RPE or safety-control authorization.
The frozen M2DGR 22/7/7 partition remains unchanged, all eleven science
gates remain CLOSED, and publication requires separate explicit permission.
