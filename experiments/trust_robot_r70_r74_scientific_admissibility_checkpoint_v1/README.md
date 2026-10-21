# R70–R74 M2DGR author-source admissibility checkpoint

Parent: `6873da42fda57f23a46c0ecb2c788489802faa8c`.

Six SHA-pinned R74 code and derived evidence artifacts are archived here.
R70, R71A and R72 original private Verona reports plus the R73 private handoff
receipt are **not** archived; only their SHA-256 identifiers are retained.
Run `python3 verify_checkpoint.py verify .` from this directory.

Author documentation names Vicon Vero 2.2 at nominal 50 Hz; recorded GT
median interval corresponds to approximately 50.057 Hz. This is a numeric
consistency observation, **not** physical clock synchronization. Source
calibration has 15 LiDAR-extrinsic headings but no explicit mocap entry.
The original room_02 GT and historical 90 invalid rotation samples in
61 index runs remain SHA-reproducible from the prior checkpoint.

Mocap tracked-body origin, mocap-to-LiDAR SE(3), reference timestamp capture
event/timebase, cross-sensor clock mapping and invalid-rotation treatment
remain unqualified. All eleven scientific gates are CLOSED. No real pose
factors, health training, ATE/RPE, confirmation_test, GT, or ROS bags are
permitted by this checkpoint.
