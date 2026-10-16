# TRUST-ROBOT KIOS L24-L30 Multimodal Evidence Audit

Checkpoint date: 2026-10-16
Branch: kios-isaacsim-v15-integration
Parent commit: 45b54a9625ea4c834f4009f441973cf93ce0d6b3

## Research results

L24 performed 11 freshness/provenance adversarial tests.
The frozen reference reviewed all 11. Sequence-only detection
reviewed 8 of 11, missing coherent and camera-payload replay cases.

L25 challenged common-mode corruptions. The frozen reference
reviewed 11/11; sequence-only review detected 1/11 in this
scenario set. Scripted-USD translation-magnitude comparisons
reviewed 5/11 at 1 cm, 3/11 at 2 cm and 1/11 at 4 cm.
These exploratory tests do not constitute independent truth.

L26 defined 11 scientific readiness requirements. Zero were
independently qualified. Four admission/readiness gates were
denied; all 11 unsupported-claim challenges were denied.

L27 inventoried six camera frames, six 16-return LiDAR scans,
130 IMU rows and 130 scripted USD pose rows from existing data.
An acquisition contract was developed; no new capture occurred.

L28 produced a shadow envelope of 272 existing-data events
and passed six negative controls. It was not new acquisition.

L29 prepared a distinct instrumented runtime candidate.
Its adapter dry-run yielded 272 events. No simulator was run
in L29.

L30 ran this candidate in guarded KIOS Isaac Sim with a
successful exit and independently checked metadata evidence.
Selected steps: 51, 61, 71, 81, 91, 101.
LiDAR returns: 16 each; total 96.
Camera frames: 6. LiDAR frames: 6.
IMU rows: 130. Scripted USD pose rows: 130.
Fresh metadata events: 272.
Six negative controls passed.

Reported GMO-minus-read-clock offset spread:
7.95053356483777e-10 seconds.
This narrow software-clock difference does not establish
physical exposure synchronization.

## Provenance and data boundaries

The archive includes original implementation snapshots and
compact JSON/JSONL metadata evidence with exact SHA256s.

The instrumented candidate and adapter retain KIOS-specific
paths; they are not portable execution packages.

The L30 launch block itself was not evidenced as a separately
stored, byte-for-byte KIOS script.

The original sensor recordings, large runtime logs and scene
remain KIOS-local. Earlier recordings were checked unchanged
during L30 validation.

## Unresolved scientific gates

- Independent source authenticity and replay adjudication
- Sensor measurement-event timestamp meaning and uncertainty
- Verified camera/LiDAR/IMU intrinsic and extrinsic calibration
- Independent, continuously associated 6DoF reference
- Validated factor uncertainty
- Prospective held-out localization and fault evaluation
- Calibrated sensor-health probabilities and error rates

Scientifically authorized pose factors: 0.
Generated supervised health labels: 0.

No physical-sensor equivalence, independent ground truth,
ATE/RPE performance or validated fault-detection claim.

## Next step

L31: perform a new offline provenance/timestamp contract
assessment on L30 evidence. Do not rerun L30 or modify the
frozen LiDAR frontend. Preserve all qualification gates.
