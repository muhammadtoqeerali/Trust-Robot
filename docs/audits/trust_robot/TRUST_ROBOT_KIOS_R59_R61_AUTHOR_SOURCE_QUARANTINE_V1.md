# TRUST-ROBOT KIOS R59–R61 author-source and GT quarantine archive

Git parent at preparation: `a800ca91326a51fa0cc86972bed08e99b6b459e5`
Branch: `kios-isaacsim-v15-integration`
Archive: `experiments/trust_robot_r59_r61_author_source_quarantine_checkpoint_v1/`

R59 cryptographically authenticated the author's exact README bytes against
immutable M2DGR Git blob `c394994a8431426c0bd4b3dcf618faf7b97d119f`
and verified its single `room_02` listing. It did not obtain GT bytes.
R60 generated the author-access GitHub issue as **PREPARED_NOT_POSTED**;
author contact and response remain absent. R61 independently verified a
bounded read-only quarantine, with one synthetic positive remaining
UNVERIFIED_ONLY, ten rejected negative cases, and approved staging status
ABSENT. No SharePoint retry is authorized by this checkpoint.

The 22 TRAIN / 7 validation_calibration / 7 confirmation_test split, raw
rosbag, and historical evidence are unchanged. The 11 R43 physical reference,
calibration and science gates remain CLOSED. No qualified reference, physical
clock or frame semantics, real pose factors, health labels/training, ATE/RPE,
or robot safety actions have been authorized.

This is an evidence-preparation audit, not proof of Git publication.

## R62A exact source-pin repair (2026-10-21)

The first R62 run stopped before checkpoint-manifest generation because its
hardcoded SHA256 for `r59_primary.py` had one incorrect hexadecimal digit.
An independent 17-file comparison confirmed exactly this one typo; R59's
original source matched its recorded R59 execution digest. The builder and
verifier were corrected without touching any R59–R61 source bytes, and the
single existing R62 partial source copy was byte-checked and retained.
Original builder, verifier, README and audit copies plus a targeted repair
receipt are preserved off-Git. No new GT bytes or qualification emerged.
