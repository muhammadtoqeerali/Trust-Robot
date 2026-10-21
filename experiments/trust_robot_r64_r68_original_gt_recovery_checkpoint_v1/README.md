# TRUST-ROBOT R64–R68 historical M2DGR GT recovery checkpoint

The original TRAIN `room_02.txt` was already stored in the original Verona M2DGR dataset. A checksum-identical 504403-byte copy was transferred Verona → Windows → KIOS, kept OUTSIDE Git at `/home/kios/TRUST_ROBOT_ALI/manual_official_gt_staging_v1/room_02_official_gt_candidate.txt`.
Historical GT SHA256: `79d2c6d9132ce3cf87bb87445729302cd73709a59344a3dfacc5d7788937589d`. This is a match to our original dataset evidence, **not** an independent original-author checksum attestation.

R65: 3831 numeric eight-column records, 77.82016110420227 first-column span, no duplicate/decreasing values; 90 candidate quaternion deviations >0.01.
R66: original 0.001 quaternion norm rule and independent replay agree on 90 invalid rotations in 61 sample-index runs, 3741 structurally valid rotations, zero invalid translations.
R67: original Phase-2 reference-quality artifact rebuilt BYTE-FOR-BYTE, SHA256 `8b27f25c02d04e838a88eb62980b1f2e94d0e1ed13defd0c6fa0f0b07c6bed49`.
R68: reconciled original frozen R43/R53 physical evidence requirements; corrected author request is a DRAFT, NOT SENT.

All 11 physical/scientific gates remain CLOSED. No independent physical GT timestamp/event/epoch mapping, mocap tracked body origin, mocap-to-LiDAR rigid transform, or required sensor calibration. No real pose factors, health training, ATE/RPE or test-data selection. `confirmation_test` remains sealed. No raw `.bag` or original `.txt` GT is in this archive. R61's historical `GT=ABSENT` describes its earlier staging state only; it is not current.

Verona original dataset path: `/mnt/hdd16T/ToqeerHomeBackup/toqeer/datasets/TRUST_ROBOT/M2DGR/`; Verona project: `~/toqeer/TRUST_ROBOT`; KIOS active Git checkout: `/home/kios/TRUST_ROBOT_ALI/github_checkout_v15`.

To verify all 22 frozen original off-Git source/report SHA pins and scientific semantics from a Git clone:
`python3 experiments/trust_robot_r64_r68_original_gt_recovery_checkpoint_v1/verify_checkpoint.py verify experiments/trust_robot_r64_r68_original_gt_recovery_checkpoint_v1`

The verifier does not require raw ground-truth or ROS bag bytes.
