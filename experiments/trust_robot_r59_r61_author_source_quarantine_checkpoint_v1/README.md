# TRUST-ROBOT R59–R61: official author-source provenance and GT quarantine

This checkpoint archives 17 original, byte-identified off-Git development and
result files from R59, R60, R61. R59 independently authenticated the author's
immutable M2DGR README Git blob and official room_02 GT **link**. This does
not authenticate, download, or license a new GT payload. R60 prepared an
independently verified **unsent** author support issue draft. R61 built a
read-only, fail-closed candidate intake/quarantine with one synthetic positive
and ten rejected negative controls; the authorized GT staging path was absent.

R59–R61 are engineering/provenance readiness results; no reference clock,
reference frame, raw GT validity, physical calibration or synchronized sensor
capture time has been independently qualified. Historical raw reference digest
is not an author-confirmed checksum for a newly acquired file. All eleven R43
science gates remain CLOSED; no pose factors, supervised health training,
ATE/RPE or confirmation-test access is authorized. Raw rosbag, GT payloads,
authentication tokens and test observations are excluded.

Run `python3 -B verify_checkpoint.py` to recheck exact frozen bytes and
science restrictions. The upstream author README is included solely as the
SHA-authenticated published source document, not as a reference trajectory.
This archive is prepared on KIOS but not yet committed or pushed by R62.

Next: R63 independent tamper challenges and commit-scoped documentation
preparation; publish only after checks, without treating the absent GT as
acquired. Human review/posting of R60 is a separate external action.

## R62A exact source-pin repair (2026-10-21)

The first R62 run stopped before checkpoint-manifest generation because its
hardcoded SHA256 for `r59_primary.py` had one incorrect hexadecimal digit.
An independent 17-file comparison confirmed exactly this one typo; R59's
original source matched its recorded R59 execution digest. The builder and
verifier were corrected without touching any R59–R61 source bytes, and the
single existing R62 partial source copy was byte-checked and retained.
Original builder, verifier, README and audit copies plus a targeted repair
receipt are preserved off-Git. No new GT bytes or qualification emerged.
