# TRUST-ROBOT R135-A37-2: Prospective Independent Health-Supervision Evidence Intake

Status: **software-only, prospective intake; no accepted supervision or physical action**.

## Scope

This module catalogs what *independent evidence* must be supplied before any new sensor-health supervision source can be reviewed. It records gaps and checks artifact-digest shapes. A digest alone proves neither artifact existence nor measurement content, event-time binding, physical independence, sensor health, or supervision acceptability. No source-acceptance function exists in this module.

## LiDAR controlled-availability candidate

The existing Phase-5 protocol specifically concerns the Velodyne **VLP-32C**. It requires distinct prospective evidence for the source measurement, raw operational-status observation, explicit interval binding, no-intervention baseline, baseline-nominality review, independently verified intervention execution, and independently verified measurement relationship. Even a complete set of well-formed digests does **not** qualify a health label. The frozen SE2 evidence-acceptance requirements still control.

**Do not apply this VLP-32C protocol to a different robot LiDAR simply because it also publishes PointCloud2.** A different instrument requires sensor-specific source/protocol review.

## Camera and IMU

The frozen SE3 camera and IMU feature contracts are diagnostic **inputs**, not supervised health labels. The module records generic independent-evidence gaps for those modalities but explicitly reports their health-supervision acceptance protocols as unresolved. No LiDAR operational-status rule is substituted for camera/IMU health semantics.

## Scientific boundary

- Frozen M2DGR TRAIN partition only for future candidate source review; no validation or confirmation access.
- Absence of messages, a clean bag identity, an injected-fault identifier, diagnostic features, ATE/RPE, and a classifier's own output cannot alone supply real health labels.
- No sensor-health model training, calibration, threshold selection, real factor admission, real sensor suppression, fallback navigation, or robot control.
- The software emits no supervision acceptance and no numerical health probabilities.
- Independent physical evidence and source-acceptance review are required before SE4 health-model training opens.

## Intended next physical-evidence track

Design separate prospective, instrumented TRAIN acquisition sessions with independently observed sensor status, physical-event/interval provenance, operator-controlled intervention logs where safe, and independent measurement-relation checks. Obtain appropriate safety and research approvals before any deliberate physical intervention. The stationary recorder-envelope bag alone cannot supply the missing independent labels.
