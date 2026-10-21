# TRUST-ROBOT R80–R82 recorded multimodal engineering checkpoint

Parent Git revision: `aa4c06bdc2eac5cff7352157beef9ec534f2f455`.

- **R80 (KIOS):** Eight separated recorded `room_02` LiDAR scan pairs, typed 6-DoF inverse/geometry checks, and 13 regression tests. The eight pairs are not represented as one continuous odometry chain.
- **R81 (Verona):** Reusable read-only frozen-TRAIN LiDAR increment adapter. Authenticated Phase-2 artifacts; independently replayed 90,992 consecutive increments from 91,014 scans in 22 TRAIN trajectories. Thirteen synthetic tests. Original trajectory JSONL files remain dataset-local and off Git.
- **R82 (Verona):** Stream-local, unaligned 256-record camera/IMU diagnostic windows built on frozen SE3 low-level feature files. The original 2,816,957 TRAIN feature records and 62 source feature files were verified. Thirteen synthetic tests. The 62 derived window JSONL files remain off Git; compact summaries and code are archived.
- **R83A/B:** SHA-256-pinned sanitized Verona–Windows–KIOS transfer; eight R81/R82 source/report files plus a handoff manifest. Original GT, ROSbags, private reports, original feature rows, and derived window files were excluded.

The 22/7/7 TRAIN/validation/confirmation split remains frozen.

R80–R82 do not establish physical timestamp mapping, independent calibration, synchronized fusion, visual/IMU pose factors, health labels, health probabilities, ATE/RPE, or physical accuracy.

All eleven scientific gates remain closed. An author request was not sent. Development continues using public and locally verified TRAIN evidence without waiting for outside responses.

Standalone archived verification:

`python3 -B experiments/trust_robot_r80_r82_recorded_multimodal_checkpoint_v1/verify_checkpoint.py verify experiments/trust_robot_r80_r82_recorded_multimodal_checkpoint_v1`

R80 regression tests require the repository-root argument. R81/R82 synthetic tests require only Python's standard library.

The full recorded-data replays cannot be reproduced from Git alone because their large frozen source artifacts remain on Verona. Their SHA-pinned compact results and validation receipts are archived.
