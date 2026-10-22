# R104 — single-fixture synthetic factor graph contract

R104 reuses the existing S6 manufactured generator and unchanged
nonlinear estimator. Each case has exactly five nodes at times
0, 200, 400, 600, and 800 ms in a synthetic epoch; eight IMU
readings cover nonoverlapping 100 ms sample intervals. Four
preintegrated IMU factors each own exactly two samples.

LiDAR registration factors are derived from synthetic scans and
camera relative poses are separately manufactured using generator
truth. Both are attached to the same synthetic node schedule with
distinct measurement identities and assumed covariance scales.
Generator truth is not forwarded to the S6 estimator or stored in
the released evidence. S6 internally rebuilds and optimizes factors;
R104 is a validated input witness, not a replacement optimizer.

R104 does NOT merge R95 information-form priors with S6. No 15D to
30D live prior transfer is attempted. A shared synthetic generator
is not a verified physical camera/LiDAR/IMU timestamp calibration,
independent sensor-noise verification, or an independent GT score.
The original S6 synthetic frame and assumed gauge apply.

All 11 scientific gates remain CLOSED. No physical sensor factors,
recorded GT/ROSbags, health training, ATE/RPE, or confirmation test.
