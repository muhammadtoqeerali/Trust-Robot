# TRUST-ROBOT R135-A27-7 / A30-3 — Offline Engineering Audit

## Nominal frame graph verification (A27-7)

The already checksum-pinned Nova nominal URDF is tested for proper SO(3)
rotations and SE(3) pairwise inverses and triple compositions. The test
uses `T_target_source` semantics and explicitly checks a nominal transform
claim's direction. Numerical algebra tolerance is not an uncertainty bound
for physical extrinsics. The physical `bmi088_frame` alias remains absent
from the nominal URDF and is never inferred or qualified.

## Recorder timestamp provenance (A30-3)

The existing private metadata-only 843-envelope report is inspected for
per-stream recorder inter-arrival gaps, repeated timestamps, and deterministic
nearest-rank percentiles. These intervals reflect SQLite recorder timestamps,
not independently witnessed camera exposure, IMU sample or LiDAR firing times.
No event-clock mapping, offset, tolerance, cross-sensor exposure synchronization,
or physical sampling frequency is inferred.

## Independent event work orders

The five physical event-time requests B04, B05, B06, C01 and C02 are extracted
from the frozen A23 evidence packet and local A30-2 work-order contract. Their
timestamps, domain identities, offsets, uncertainties, and reviews remain empty.
No independent receipt is accepted by this phase.

## Scientific and operational boundaries

The existing M2DGR 22/7/7 split and all eleven original closed gates remain
unchanged. Historical confirmation-test inspection precludes a claim of complete
prior pristine status. No previous M2DGR dataset is opened or retroactively
qualified by Nova evidence. No robot communication, motion, sensor capture, raw
payload export, estimator invocation, physical factor creation, or pose scoring
is performed. Real factor admission remains DENIED.

## Next work

Produce concrete independent witness worksheets for event timing, frame
identity and calibration uncertainty; then plan a prospective controlled
capture only after reviewing hardware safety and evidence authority.
